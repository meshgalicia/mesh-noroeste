"""Adaptador clean-room para os JSON consolidados de O Zulo."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import math
import re
from typing import Any

from mesh_noroeste.domain import (
    EdgeObservation,
    NeighborObservation,
    NodeObservation,
    make_edge_observation,
    make_neighbor_observation,
    make_observation,
)


_PUBLIC_ID = re.compile(r"^![0-9a-f]{8}$")
_NEIGHBOR_BLOCK = re.compile(
    r"neighbors\s*\{(?P<body>[^}]*)\}",
    re.IGNORECASE,
)
_PAYLOAD_NODE_ID = re.compile(
    r"^node_id:\s*(?P<node_id>\d+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_NEIGHBOR_NODE_ID = re.compile(
    r"\bnode_id:\s*(?P<node_id>\d+)\b",
    re.IGNORECASE,
)
_NEIGHBOR_SNR = re.compile(
    r"\bsnr:\s*(?P<snr>-?\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)


class OzuloMapError(ValueError):
    """Indica que un documento do mapa de O Zulo non é válido."""


def _required(
    record: Mapping[Any, Any],
    key: str,
    index: int,
    *,
    kind: str,
) -> Any:
    if key not in record:
        raise OzuloMapError(
            f"{kind} {index}: falta o campo {key!r}"
        )

    return record[key]


def _public_id(
    value: Any,
    field: str,
    index: int,
    *,
    kind: str,
) -> str:
    if not isinstance(value, str):
        raise OzuloMapError(
            f"{kind} {index}: {field} debe ser texto"
        )

    normalized = value.strip().lower()

    if _PUBLIC_ID.fullmatch(normalized) is None:
        raise OzuloMapError(
            f"{kind} {index}: {field} debe usar !xxxxxxxx"
        )

    return normalized


def _timestamp(
    value: Any,
    field: str,
    index: int,
    *,
    kind: str,
) -> datetime:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
    ):
        raise OzuloMapError(
            f"{kind} {index}: {field} debe ser "
            "un enteiro positivo en segundos"
        )

    try:
        return datetime.fromtimestamp(
            value,
            tz=timezone.utc,
        )
    except (OverflowError, OSError, ValueError) as exc:
        raise OzuloMapError(
            f"{kind} {index}: {field} está fóra de rango"
        ) from exc


def _optional_text(
    value: Any,
    field: str,
    index: int,
) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise OzuloMapError(
            f"Nodo {index}: {field} debe ser texto ou null"
        )

    return value


def _optional_number(
    value: Any,
    field: str,
    index: int,
    *,
    kind: str,
) -> float | int | None:
    if value is None:
        return None

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise OzuloMapError(
            f"{kind} {index}: {field} debe ser "
            "numérico ou null"
        )

    return value


def _optional_integer(
    value: Any,
    field: str,
    index: int,
) -> int | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, int):
        raise OzuloMapError(
            f"Nodo {index}: {field} debe ser "
            "un enteiro ou null"
        )

    return value


def _optional_boolean_flag(
    value: Any,
    field: str,
    index: int,
) -> bool | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, int) and value in {0, 1}:
        return bool(value)

    raise OzuloMapError(
        f"Nodo {index}: {field} debe ser "
        "booleano, 0, 1 ou null"
    )


def _coordinates(
    latitude: Any,
    longitude: Any,
    index: int,
) -> tuple[float | int | None, float | int | None]:
    if latitude is None and longitude is None:
        return None, None

    if latitude is None or longitude is None:
        raise OzuloMapError(
            f"Nodo {index}: latitude e longitude "
            "deben aparecer xuntas"
        )

    return (
        _optional_number(
            latitude,
            "latitude",
            index,
            kind="Nodo",
        ),
        _optional_number(
            longitude,
            "longitude",
            index,
            kind="Nodo",
        ),
    )


def parse_ozulo_map_nodes(
    document: Any,
    *,
    source: str,
) -> tuple[NodeObservation, ...]:
    """Normaliza os nodos consolidados publicados por O Zulo."""

    if not isinstance(source, str):
        raise TypeError("source debe ser texto")

    if not isinstance(document, Mapping):
        raise OzuloMapError(
            "A raíz de nodos de O Zulo debe ser un obxecto"
        )

    records = document.get("nodes")

    if not isinstance(records, list):
        raise OzuloMapError(
            "O campo 'nodes' de O Zulo debe ser unha lista"
        )

    observations: list[NodeObservation] = []
    seen_ids: set[str] = set()

    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise OzuloMapError(
                f"Nodo {index}: debe ser un obxecto"
            )

        source_id = _public_id(
            _required(
                record,
                "node_id",
                index,
                kind="Nodo",
            ),
            "node_id",
            index,
            kind="Nodo",
        )

        if source_id in seen_ids:
            raise OzuloMapError(
                f"Nodo {index}: node_id duplicado {source_id}"
            )

        seen_ids.add(source_id)

        first_seen = _timestamp(
            _required(
                record,
                "first_seen",
                index,
                kind="Nodo",
            ),
            "first_seen",
            index,
            kind="Nodo",
        )
        observed_at = _timestamp(
            _required(
                record,
                "last_seen",
                index,
                kind="Nodo",
            ),
            "last_seen",
            index,
            kind="Nodo",
        )

        if first_seen > observed_at:
            first_seen = None

        latitude, longitude = _coordinates(
            record.get("latitude"),
            record.get("longitude"),
            index,
        )

        position_updated_at = (
            observed_at
            if latitude is not None
            else None
        )
        position_precision_bits = (
            _optional_integer(
                record.get("precision_bits"),
                "precision_bits",
                index,
            )
            if latitude is not None
            else None
        )

        try:
            observation = make_observation(
                source=source,
                network="meshtastic",
                source_id=source_id,
                observed_at=observed_at,
                first_seen=first_seen,
                short_name=_optional_text(
                    record.get("short_name"),
                    "short_name",
                    index,
                ),
                long_name=_optional_text(
                    record.get("long_name"),
                    "long_name",
                    index,
                ),
                hardware=_optional_text(
                    record.get("hardware"),
                    "hardware",
                    index,
                ),
                role=_optional_text(
                    record.get("role"),
                    "role",
                    index,
                ),
                latitude=latitude,
                longitude=longitude,
                altitude_m=_optional_number(
                    record.get("altitude"),
                    "altitude",
                    index,
                    kind="Nodo",
                ),
                position_precision_bits=position_precision_bits,
                position_updated_at=position_updated_at,
                metrics={
                    "battery_percent": _optional_number(
                        record.get("battery_level"),
                        "battery_level",
                        index,
                        kind="Nodo",
                    ),
                    "voltage_v": _optional_number(
                        record.get("voltage"),
                        "voltage",
                        index,
                        kind="Nodo",
                    ),
                    "channel_utilization_percent": (
                        _optional_number(
                            record.get("channel_util"),
                            "channel_util",
                            index,
                            kind="Nodo",
                        )
                    ),
                    "air_util_tx_percent": _optional_number(
                        record.get("air_util_tx"),
                        "air_util_tx",
                        index,
                        kind="Nodo",
                    ),
                    "snr_db": _optional_number(
                        record.get("snr"),
                        "snr",
                        index,
                        kind="Nodo",
                    ),
                    "rssi_dbm": _optional_number(
                        record.get("rssi"),
                        "rssi",
                        index,
                        kind="Nodo",
                    ),
                },
                radio={
                    "channel": _optional_text(
                        record.get("channel"),
                        "channel",
                        index,
                    ),
                    "firmware": _optional_text(
                        record.get("firmware"),
                        "firmware",
                        index,
                    ),
                    "hops_away": _optional_integer(
                        record.get("hops_away"),
                        "hops_away",
                        index,
                    ),
                    "mqtt_gateway": (
                        _optional_boolean_flag(
                            record.get("is_mqtt_gateway"),
                            "is_mqtt_gateway",
                            index,
                        )
                    ),
                },
            )
        except (TypeError, ValueError) as exc:
            raise OzuloMapError(
                f"Nodo {index}: {exc}"
            ) from exc

        observations.append(observation)

    return tuple(observations)


def parse_ozulo_neighbor_packets(
    document: Any,
    *,
    source: str,
) -> tuple[NeighborObservation, ...]:
    """Normaliza os anuncios NeighborInfo publicados por O Zulo."""

    if not isinstance(source, str):
        raise TypeError("source debe ser texto")

    if not isinstance(document, Mapping):
        raise OzuloMapError(
            "A raíz de paquetes de O Zulo debe ser un obxecto"
        )

    records = document.get("packets")

    if not isinstance(records, list):
        raise OzuloMapError(
            "O campo 'packets' de O Zulo debe ser unha lista"
        )

    observations: list[NeighborObservation] = []
    seen: set[tuple[str, str, str, str]] = set()

    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise OzuloMapError(
                f"Paquete {index}: debe ser un obxecto"
            )

        portnum = _required(
            record,
            "portnum",
            index,
            kind="Paquete",
        )

        if (
            isinstance(portnum, bool)
            or not isinstance(portnum, int)
            or portnum != 71
        ):
            raise OzuloMapError(
                f"Paquete {index}: portnum debe ser 71"
            )

        from_node_id = _required(
            record,
            "from_node_id",
            index,
            kind="Paquete",
        )

        if (
            isinstance(from_node_id, bool)
            or not isinstance(from_node_id, int)
            or not 0 <= from_node_id <= 0xFFFFFFFF
        ):
            raise OzuloMapError(
                f"Paquete {index}: from_node_id debe ser "
                "un enteiro Meshtastic válido"
            )

        imported_at = _required(
            record,
            "import_time_us",
            index,
            kind="Paquete",
        )

        if (
            isinstance(imported_at, bool)
            or not isinstance(imported_at, int)
            or imported_at < 0
        ):
            raise OzuloMapError(
                f"Paquete {index}: import_time_us debe ser "
                "un enteiro positivo"
            )

        payload = _required(
            record,
            "payload",
            index,
            kind="Paquete",
        )

        if not isinstance(payload, str):
            raise OzuloMapError(
                f"Paquete {index}: payload debe ser texto"
            )

        emitter_match = _PAYLOAD_NODE_ID.search(payload)

        if emitter_match is None:
            raise OzuloMapError(
                f"Paquete {index}: payload non declara node_id"
            )

        payload_node_id = int(
            emitter_match.group("node_id")
        )

        if payload_node_id != from_node_id:
            raise OzuloMapError(
                f"Paquete {index}: node_id do payload non "
                "coincide con from_node_id"
            )

        for neighbor_index, block_match in enumerate(
            _NEIGHBOR_BLOCK.finditer(payload)
        ):
            body = block_match.group("body")
            node_match = _NEIGHBOR_NODE_ID.search(body)
            snr_match = _NEIGHBOR_SNR.search(body)

            if node_match is None:
                raise OzuloMapError(
                    f"Paquete {index}, veciño {neighbor_index}: "
                    "falta node_id"
                )

            if snr_match is None:
                continue

            try:
                observation = make_neighbor_observation(
                    source=source,
                    from_source_id=from_node_id,
                    to_source_id=int(
                        node_match.group("node_id")
                    ),
                    observed_at=imported_at,
                    snr_db=float(
                        snr_match.group("snr")
                    ),
                )
            except (TypeError, ValueError) as exc:
                raise OzuloMapError(
                    f"Paquete {index}, veciño "
                    f"{neighbor_index}: {exc}"
                ) from exc

            identity = (
                observation.source,
                observation.from_source_id,
                observation.to_source_id,
                observation.observed_at,
            )

            if identity in seen:
                continue

            seen.add(identity)
            observations.append(observation)

    return tuple(
        sorted(
            observations,
            key=lambda observation: (
                observation.observed_at,
                observation.from_source_id,
                observation.to_source_id,
            ),
        )
    )


def parse_ozulo_map_edges(
    document: Any,
    *,
    source: str,
) -> tuple[EdgeObservation, ...]:
    """Normaliza as conexións consolidadas publicadas por O Zulo."""

    if not isinstance(source, str):
        raise TypeError("source debe ser texto")

    if not isinstance(document, Mapping):
        raise OzuloMapError(
            "A raíz de conexións de O Zulo debe ser un obxecto"
        )

    records = document.get("edges")

    if not isinstance(records, list):
        raise OzuloMapError(
            "O campo 'edges' de O Zulo debe ser unha lista"
        )

    latest_by_id: dict[str, EdgeObservation] = {}

    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise OzuloMapError(
                f"Conexión {index}: debe ser un obxecto"
            )

        from_source_id = _public_id(
            _required(
                record,
                "from_node",
                index,
                kind="Conexión",
            ),
            "from_node",
            index,
            kind="Conexión",
        )
        to_source_id = _public_id(
            _required(
                record,
                "to_node",
                index,
                kind="Conexión",
            ),
            "to_node",
            index,
            kind="Conexión",
        )

        if from_source_id == to_source_id:
            continue

        edge_type = _required(
            record,
            "edge_type",
            index,
            kind="Conexión",
        )

        if not isinstance(edge_type, str):
            raise OzuloMapError(
                f"Conexión {index}: edge_type debe ser texto"
            )

        normalized_type = edge_type.strip().lower()

        if normalized_type not in {
            "neighbor",
            "traceroute",
        }:
            raise OzuloMapError(
                f"Conexión {index}: edge_type debe ser "
                "neighbor ou traceroute"
            )

        observed_at = _timestamp(
            _required(
                record,
                "last_seen",
                index,
                kind="Conexión",
            ),
            "last_seen",
            index,
            kind="Conexión",
        )

        try:
            observation = make_edge_observation(
                source=source,
                network="meshtastic",
                from_source_id=from_source_id,
                to_source_id=to_source_id,
                edge_type=normalized_type,
                directed=normalized_type == "traceroute",
                observed_at=observed_at,
                metrics={
                    "snr_db": _optional_number(
                        record.get("snr"),
                        "snr",
                        index,
                        kind="Conexión",
                    ),
                    "rssi_dbm": None,
                },
            )
        except (TypeError, ValueError) as exc:
            raise OzuloMapError(
                f"Conexión {index}: {exc}"
            ) from exc

        previous = latest_by_id.get(observation.id)

        if (
            previous is None
            or observation.observed_at
            > previous.observed_at
        ):
            latest_by_id[observation.id] = observation

    return tuple(
        latest_by_id[key]
        for key in sorted(latest_by_id)
    )
