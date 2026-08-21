"""Análisis independiente de configuración Meshtastic."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import statistics
import tempfile
import time
from typing import Any
from urllib.parse import urlencode, urlsplit

from mesh_noroeste.exclusions import load_exclusions
from mesh_noroeste.http_client import FetchError, fetch_json
from mesh_noroeste.normalization import canonical_node_id


DEFAULT_BASE_URL = "https://meshview.mesh.comunidadeozulo.org"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_PACKETS = 10_000
DEFAULT_WORKERS = 20
BROADCAST_ID = 0xFFFFFFFF

PORTS = {
    "position": 3,
    "nodeinfo": 4,
    "routing": 5,
    "range_test": 66,
    "telemetry": 67,
    "traceroute": 70,
}

THRESHOLDS = {
    "position_fixed": (3, 7, 25),
    "position_mobile": (31, 49, 97),
    "nodeinfo": (3, 7, 25),
    "telemetry_device": (5, 9, 25),
    "telemetry_environment": (9, 16, 26),
    "telemetry_power": (7, 16, 26),
    "routing": (16, 31, 151),
    "traceroute_auto": (11, 13, 25),
}

POSITION_FIELDS = (
    "ground_speed",
    "ground_track",
    "sats_in_view",
    "seq_number",
    "timestamp",
    "altitude_hae",
)

MOBILE_HARDWARE_MARKERS = (
    "T1000",
    "TRACKER",
    "WISMESH_TAP",
    "WATCH",
)

MOBILE_ROLES = {
    "CLIENT_MUTE",
    "CLIENT_HIDDEN",
    "TRACKER",
    "TAK_TRACKER",
    "ROUTER",
    "ROUTER_CLIENT",
    "REPEATER",
    "ROUTER_LATE",
}

LATITUDE_PATTERN = re.compile(
    r"\blatitude_i\s*:\s*(-?\d+)"
)
LONGITUDE_PATTERN = re.compile(
    r"\blongitude_i\s*:\s*(-?\d+)"
)


class ConfigurationAnalysisError(RuntimeError):
    """Error controlado del analizador."""


@dataclass(frozen=True, slots=True)
class NodeMetadata:
    """Metadatos mínimos publicados por unha API Meshtastic."""

    node_id: int
    public_id: str
    hardware: str
    role: str
    firmware: str


def validated_base_url(value: str) -> str:
    """Valida la URL raíz de la API."""

    if not isinstance(value, str):
        raise TypeError("La URL base debe ser texto")

    normalized = value.strip().rstrip("/")
    parsed = urlsplit(normalized)

    if parsed.scheme.lower() != "https":
        raise ValueError("La URL base debe usar HTTPS")

    if parsed.hostname is None:
        raise ValueError(
            "La URL base debe incluir un servidor"
        )

    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "La URL base no admite credenciales, "
            "consulta ni fragmento"
        )

    return normalized


def _fetch_document(
    url: str,
    *,
    timeout: float,
) -> Any:
    try:
        return fetch_json(
            url,
            timeout=timeout,
            max_bytes=DEFAULT_MAX_BYTES,
            user_agent=(
                "Mesh-Noroeste-Configuration-Analysis/0.1.0"
            ),
        ).document
    except FetchError as exc:
        raise ConfigurationAnalysisError(
            str(exc)
        ) from exc


def parse_nodes(
    document: Any,
) -> tuple[NodeMetadata, ...]:
    """Valida la respuesta de ``/api/nodes``."""

    if not isinstance(document, dict):
        raise ConfigurationAnalysisError(
            "La raíz de /api/nodes debe ser un objeto"
        )

    records = document.get("nodes")

    if not isinstance(records, list):
        raise ConfigurationAnalysisError(
            "/api/nodes no contiene una lista nodes"
        )

    nodes: list[NodeMetadata] = []
    seen: set[int] = set()

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ConfigurationAnalysisError(
                f"Nodo {index}: debe ser un objeto"
            )

        node_id = record.get("node_id")
        public_id = record.get("id")

        if (
            isinstance(node_id, bool)
            or not isinstance(node_id, int)
            or not 0 <= node_id <= BROADCAST_ID
        ):
            raise ConfigurationAnalysisError(
                f"Nodo {index}: node_id inválido"
            )

        expected = f"!{node_id:08x}"

        if (
            not isinstance(public_id, str)
            or public_id.strip().lower() != expected
        ):
            raise ConfigurationAnalysisError(
                f"Nodo {index}: id no corresponde "
                "con node_id"
            )

        if node_id in seen:
            raise ConfigurationAnalysisError(
                f"Nodo duplicado: {expected}"
            )

        seen.add(node_id)
        nodes.append(
            NodeMetadata(
                node_id=node_id,
                public_id=expected,
                hardware=str(
                    record.get("hw_model") or ""
                ),
                role=str(
                    record.get("role") or "CLIENT"
                ),
                firmware=str(
                    record.get("firmware") or ""
                ),
            )
        )

    return tuple(nodes)


def parse_packets(
    document: Any,
) -> list[dict[str, Any]]:
    """Valida la envoltura de ``/api/packets``."""

    if not isinstance(document, dict):
        raise ConfigurationAnalysisError(
            "La raíz de /api/packets debe ser "
            "un objeto"
        )

    records = document.get("packets")

    if not isinstance(records, list):
        raise ConfigurationAnalysisError(
            "/api/packets no contiene una lista packets"
        )

    return [
        record
        for record in records
        if isinstance(record, dict)
    ]


def severity_for(
    count: int,
    thresholds: tuple[int, int, int],
) -> str | None:
    """Clasifica una frecuencia diaria."""

    medium, high, critical = thresholds

    if count >= critical:
        return "critical"

    if count >= high:
        return "high"

    if count >= medium:
        return "medium"

    return None


def _issue(
    key: str,
    severity: str,
) -> dict[str, str]:
    return {
        "key": key,
        "severity": severity,
    }


def firmware_at_least(
    value: str,
    expected: tuple[int, int, int],
) -> bool:
    """Compara la parte numérica inicial de una versión."""

    parts: list[int] = []

    for raw_part in value.split(".")[:3]:
        match = re.match(r"\d+", raw_part)

        parts.append(
            int(match.group())
            if match is not None
            else 0
        )

    while len(parts) < 3:
        parts.append(0)

    return tuple(parts) >= expected


def parse_coordinates(
    payload: str,
) -> tuple[float, float] | None:
    """Extrae coordenadas del texto protobuf."""

    latitude = LATITUDE_PATTERN.search(payload)
    longitude = LONGITUDE_PATTERN.search(payload)

    if latitude is None or longitude is None:
        return None

    return (
        int(latitude.group(1)) / 10_000_000,
        int(longitude.group(1)) / 10_000_000,
    )


def haversine_metres(
    first: tuple[float, float],
    second: tuple[float, float],
) -> float:
    """Calcula distancia aproximada entre coordenadas."""

    latitude_1, longitude_1 = map(
        math.radians,
        first,
    )
    latitude_2, longitude_2 = map(
        math.radians,
        second,
    )

    latitude_delta = latitude_2 - latitude_1
    longitude_delta = longitude_2 - longitude_1

    value = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_1)
        * math.cos(latitude_2)
        * math.sin(longitude_delta / 2) ** 2
    )

    return 6_371_000 * 2 * math.atan2(
        math.sqrt(value),
        math.sqrt(1 - value),
    )


def classify_position(
    values: list[tuple[float, float]],
) -> bool | None:
    """Devuelve True para fija y False para móvil."""

    if len(values) < 2:
        return None

    reference = (
        statistics.median(
            value[0]
            for value in values
        ),
        statistics.median(
            value[1]
            for value in values
        ),
    )

    maximum_distance = max(
        haversine_metres(reference, value)
        for value in values
    )

    return maximum_distance < 1_000


def regular_automatic_pattern(
    packets: list[dict[str, Any]],
    *,
    minimum_count: int,
    short_cycle_minutes: float | None = None,
) -> bool:
    """Detecta emisiones periódicas suficientemente regulares."""

    timestamps = sorted(
        packet["import_time_us"]
        for packet in packets
        if (
            isinstance(
                packet.get("import_time_us"),
                int,
            )
            and not isinstance(
                packet.get("import_time_us"),
                bool,
            )
        )
    )

    if len(timestamps) < minimum_count:
        return False

    intervals = [
        (later - earlier) / 60_000_000
        for earlier, later in zip(
            timestamps,
            timestamps[1:],
        )
        if later > earlier
    ]

    if len(intervals) < minimum_count - 1:
        return False

    average = statistics.fmean(intervals)

    if average <= 0:
        return False

    deviation = (
        statistics.pstdev(intervals)
        if len(intervals) > 1
        else 0.0
    )

    if deviation / average < 0.20:
        return True

    return (
        short_cycle_minutes is not None
        and average < short_cycle_minutes
        and len(timestamps) > 50
    )


def mobile_hardware(value: str) -> bool:
    """Detecta modelos concebidos como portátiles."""

    normalized = value.upper()

    return any(
        marker in normalized
        for marker in MOBILE_HARDWARE_MARKERS
    )


def latest_hop_start(
    base_url: str,
    packet: dict[str, Any] | None,
    *,
    timeout: float,
) -> int | None:
    """Obtiene el hop_start máximo de un paquete."""

    if packet is None:
        return None

    packet_id = packet.get("id")

    if (
        isinstance(packet_id, bool)
        or not isinstance(packet_id, int)
    ):
        return None

    document = _fetch_document(
        f"{base_url}/api/packets_seen/{packet_id}",
        timeout=timeout,
    )

    if not isinstance(document, dict):
        return None

    records = document.get("seen")

    if not isinstance(records, list):
        return None

    values = [
        record.get("hop_start")
        for record in records
        if isinstance(record, dict)
    ]

    valid = [
        value
        for value in values
        if (
            isinstance(value, int)
            and not isinstance(value, bool)
            and 0 <= value <= 7
        )
    ]

    return max(valid) if valid else None


def analyse_packets(
    metadata: NodeMetadata,
    packets: list[dict[str, Any]],
    *,
    traceroute_hop_start: int | None = None,
) -> dict[str, Any]:
    """Genera los avisos normalizables de un nodo."""

    by_port = {
        name: [
            packet
            for packet in packets
            if packet.get("portnum") == port
        ]
        for name, port in PORTS.items()
    }

    warnings: list[dict[str, str]] = []

    if by_port["range_test"]:
        warnings.append(
            _issue("range_test", "critical")
        )

    positions = [
        packet
        for packet in by_port["position"]
        if packet.get("to_node_id") == BROADCAST_ID
    ]
    coordinates = [
        parsed
        for packet in positions
        if (
            parsed := parse_coordinates(
                str(packet.get("payload") or "")
            )
        ) is not None
    ]
    fixed = classify_position(coordinates)

    if fixed is not None:
        key = (
            "position_fixed"
            if fixed
            else "position_mobile"
        )
        severity = severity_for(
            len(positions),
            THRESHOLDS[key],
        )

        if severity is not None:
            warnings.append(
                _issue(key, severity)
            )

    nodeinfo_packets = [
        packet
        for packet in by_port["nodeinfo"]
        if packet.get("to_node_id") == BROADCAST_ID
    ]
    nodeinfo_count = len(nodeinfo_packets)

    if (
        regular_automatic_pattern(
            nodeinfo_packets,
            minimum_count=4,
        )
        or nodeinfo_count
        >= THRESHOLDS["nodeinfo"][2]
    ):
        severity = severity_for(
            nodeinfo_count,
            THRESHOLDS["nodeinfo"],
        )

        if severity is not None:
            warnings.append(
                _issue("nodeinfo", severity)
            )

    telemetry_counts = {
        "telemetry_device": 0,
        "telemetry_environment": 0,
        "telemetry_power": 0,
    }

    for packet in by_port["telemetry"]:
        payload = str(packet.get("payload") or "")

        if "device_metrics" in payload:
            telemetry_counts[
                "telemetry_device"
            ] += 1

        if "environment_metrics" in payload:
            telemetry_counts[
                "telemetry_environment"
            ] += 1

        if "power_metrics" in payload:
            telemetry_counts[
                "telemetry_power"
            ] += 1

    for key, count in telemetry_counts.items():
        severity = severity_for(
            count,
            THRESHOLDS[key],
        )

        if severity is not None:
            warnings.append(
                _issue(key, severity)
            )

    routing_packets = by_port["routing"]
    routing_count = len(routing_packets)

    if (
        regular_automatic_pattern(
            routing_packets,
            minimum_count=5,
            short_cycle_minutes=10,
        )
        or routing_count
        >= THRESHOLDS["routing"][2]
    ):
        severity = severity_for(
            routing_count,
            THRESHOLDS["routing"],
        )

        if severity is not None:
            warnings.append(
                _issue("routing", severity)
            )

    traceroutes = by_port["traceroute"]
    traceroute_requests = [
        packet
        for packet in traceroutes
        if "route_back" not in str(
            packet.get("payload") or ""
        )
    ]
    traceroute_count = len(traceroutes)

    if (
        regular_automatic_pattern(
            traceroute_requests,
            minimum_count=4,
            short_cycle_minutes=20,
        )
        or traceroute_hop_start == 7
    ):
        severity = severity_for(
            traceroute_count,
            THRESHOLDS["traceroute_auto"],
        )

        if severity is not None:
            warnings.append(
                _issue("traceroute_auto", severity)
            )

    if fixed is True:
        has_unnecessary_fields = any(
            re.search(
                rf"\b{re.escape(field)}\s*:",
                str(packet.get("payload") or ""),
            )
            for field in POSITION_FIELDS
            for packet in positions
        )

        if has_unnecessary_fields:
            warnings.append(
                _issue("position_flags", "medium")
            )

    if (
        metadata.role.upper() == "CLIENT_BASE"
        and firmware_at_least(
            metadata.firmware,
            (2, 7, 17),
        )
    ):
        warnings.append(
            _issue("client_base_fw", "medium")
        )

    if (
        (
            fixed is False
            or mobile_hardware(metadata.hardware)
        )
        and metadata.role.upper() not in MOBILE_ROLES
    ):
        warnings.append(
            _issue("client_mute_mobile", "medium")
        )

    severity_order = {
        "critical": 0,
        "high": 1,
        "medium": 2,
    }
    warnings.sort(
        key=lambda warning: (
            severity_order[warning["severity"]],
            warning["key"],
        )
    )

    return {
        "id": metadata.public_id,
        "issues": warnings,
    }


def analyse_node(
    metadata: NodeMetadata,
    *,
    base_url: str,
    since_us: int,
    timeout: float,
    max_packets: int,
) -> dict[str, Any]:
    """Consulta y analiza un nodo."""

    query = urlencode({
        "from_node_id": metadata.node_id,
        "since": since_us,
        "limit": max_packets,
    })
    packets = parse_packets(
        _fetch_document(
            f"{base_url}/api/packets?{query}",
            timeout=timeout,
        )
    )

    traceroutes = [
        packet
        for packet in packets
        if packet.get("portnum") == PORTS["traceroute"]
    ]
    latest_traceroute = max(
        traceroutes,
        key=lambda packet: packet.get(
            "import_time_us",
            0,
        ),
        default=None,
    )

    hop_start = latest_hop_start(
        base_url,
        latest_traceroute,
        timeout=timeout,
    )

    return analyse_packets(
        metadata,
        packets,
        traceroute_hop_start=hop_start,
    )


def build_document(
    nodes: tuple[NodeMetadata, ...],
    *,
    base_url: str,
    timeout: float,
    workers: int,
    max_packets: int,
    now: int | None = None,
) -> dict[str, Any]:
    """Analiza todos los nodos y construye el documento."""

    updated = int(time.time()) if now is None else now
    since_us = (updated - 86_400) * 1_000_000
    records: list[dict[str, Any]] = []
    failures: list[str] = []

    with ThreadPoolExecutor(
        max_workers=workers
    ) as executor:
        pending = {
            executor.submit(
                analyse_node,
                metadata,
                base_url=base_url,
                since_us=since_us,
                timeout=timeout,
                max_packets=max_packets,
            ): metadata
            for metadata in nodes
        }

        for completed, future in enumerate(
            as_completed(pending),
            start=1,
        ):
            metadata = pending[future]

            try:
                records.append(future.result())
            except (
                ConfigurationAnalysisError,
                OSError,
                TypeError,
                ValueError,
            ) as exc:
                failures.append(
                    f"{metadata.public_id}: {exc}"
                )

            if completed % 250 == 0:
                print(
                    f"Analizados {completed}/{len(nodes)}",
                    flush=True,
                )

    if not records and nodes:
        raise ConfigurationAnalysisError(
            "No se pudo analizar ningún nodo"
        )

    for failure in failures[:20]:
        print(
            f"AVISO: {failure}",
            flush=True,
        )

    if len(failures) > 20:
        print(
            "AVISO: "
            f"{len(failures) - 20} errores adicionales",
            flush=True,
        )

    return {
        "updated": updated,
        "nodes": sorted(
            records,
            key=lambda record: record["id"],
        ),
    }


def atomic_write(
    path: Path,
    document: dict[str, Any],
) -> None:
    """Escribe JSON de forma atómica."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        json.dump(
            document,
            temporary,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)

    try:
        os.replace(
            temporary_path,
            path,
        )
    finally:
        temporary_path.unlink(
            missing_ok=True
        )


def run_analysis(
    *,
    base_url: str,
    output_path: Path,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    workers: int = DEFAULT_WORKERS,
    max_packets: int = DEFAULT_MAX_PACKETS,
    now: int | None = None,
) -> dict[str, Any]:
    """Ejecuta el análisis completo."""

    normalized_base_url = validated_base_url(
        base_url
    )
    excluded_node_ids = load_exclusions(
        os.environ.get("MESH_EXCLUSIONS_PATH")
    )
    nodes = tuple(
        metadata
        for metadata in parse_nodes(
            _fetch_document(
                f"{normalized_base_url}/api/nodes",
                timeout=timeout,
            )
        )
        if canonical_node_id(
            "meshtastic",
            metadata.public_id,
        ) not in excluded_node_ids
    )
    document = build_document(
        nodes,
        base_url=normalized_base_url,
        timeout=timeout,
        workers=workers,
        max_packets=max_packets,
        now=now,
    )
    atomic_write(
        output_path,
        document,
    )

    return document


def _positive_integer(value: str) -> int:
    parsed = int(value)

    if parsed < 1:
        raise argparse.ArgumentTypeError(
            "debe ser mayor que cero"
        )

    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)

    if (
        not math.isfinite(parsed)
        or parsed <= 0
    ):
        raise argparse.ArgumentTypeError(
            "debe ser mayor que cero"
        )

    return parsed


def main() -> int:
    """Punto de entrada del analizador."""

    default_output = Path(
        os.environ.get(
            "MESH_CONFIGURATION_WARNINGS_PATH",
            (
                Path(__file__).resolve().parents[2]
                / "cache"
                / "configuration-analysis.json"
            ),
        )
    )

    parser = argparse.ArgumentParser(
        description=(
            "Analiza a actividade Meshtastic publicada "
            "pola API de Comunidade O Zulo."
        )
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get(
            "MESH_CONFIGURATION_SOURCE_URL",
            DEFAULT_BASE_URL,
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
    )
    parser.add_argument(
        "--timeout",
        type=_positive_float,
        default=DEFAULT_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--workers",
        type=_positive_integer,
        default=DEFAULT_WORKERS,
    )
    parser.add_argument(
        "--max-packets",
        type=_positive_integer,
        default=DEFAULT_MAX_PACKETS,
    )
    arguments = parser.parse_args()

    try:
        document = run_analysis(
            base_url=arguments.base_url,
            output_path=(
                arguments.output
                .expanduser()
                .resolve()
            ),
            timeout=arguments.timeout,
            workers=arguments.workers,
            max_packets=arguments.max_packets,
        )
    except (
        ConfigurationAnalysisError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        parser.exit(
            2,
            f"ERROR: {exc}\n",
        )

    print(
        json.dumps(
            {
                "status": "ok",
                "output": str(
                    arguments.output
                    .expanduser()
                    .resolve()
                ),
                "nodes_analyzed": len(
                    document["nodes"]
                ),
                "nodes_with_warnings": sum(
                    bool(record["issues"])
                    for record in document["nodes"]
                ),
                "updated": document["updated"],
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
