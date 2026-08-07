#!/usr/bin/env python3

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:
    print(
        "ERROR: falta el paquete Python 'jsonschema'.",
        file=sys.stderr,
    )
    print(
        "Instálalo antes de ejecutar estas pruebas.",
        file=sys.stderr,
    )
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parent.parent

PAIRS = (
    (
        ROOT / "schemas/manifest-v1.schema.json",
        ROOT / "tests/fixtures/manifest.valid.json",
    ),
    (
        ROOT / "schemas/nodes-v1.schema.json",
        ROOT / "tests/fixtures/nodes.valid.json",
    ),
    (
        ROOT / "schemas/edges-v1.schema.json",
        ROOT / "tests/fixtures/edges.valid.json",
    ),
    (
        ROOT / "schemas/neighbor-info-v1.schema.json",
        ROOT / "tests/fixtures/neighbor-info.valid.json",
    ),
    (
        ROOT / "schemas/observer-receptions-v1.schema.json",
        ROOT / "tests/fixtures/observer-receptions.valid.json",
    ),
    (
        ROOT / "schemas/stats-v1.schema.json",
        ROOT / "tests/fixtures/stats.valid.json",
    ),
    (
        ROOT / "schemas/meta-v1.schema.json",
        ROOT / "tests/fixtures/meta.valid.json",
    ),
    (
        ROOT / "schemas/configuration-warnings-v1.schema.json",
        ROOT / "tests/fixtures/configuration-warnings.valid.json",
    ),
)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise AssertionError(f"Falta el archivo: {path}") from None
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"JSON inválido en {path}: "
            f"línea {exc.lineno}, columna {exc.colno}: {exc.msg}"
        ) from None


def parse_timestamp(value: str) -> datetime:
    if not value.endswith("Z"):
        raise AssertionError(
            f"Timestamp sin sufijo Z: {value}"
        )

    return datetime.fromisoformat(
        value[:-1] + "+00:00"
    )


def validate_schema(
    schema_path: Path,
    fixture_path: Path,
) -> None:
    schema = load_json(schema_path)
    fixture = load_json(fixture_path)

    Draft202012Validator.check_schema(schema)

    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )

    errors = sorted(
        validator.iter_errors(fixture),
        key=lambda error: list(error.absolute_path),
    )

    if errors:
        messages = []

        for error in errors:
            location = "/".join(
                str(part)
                for part in error.absolute_path
            )

            messages.append(
                f"{location or '<raíz>'}: {error.message}"
            )

        raise AssertionError(
            f"{fixture_path} no cumple {schema_path}:\n  "
            + "\n  ".join(messages)
        )

    print(
        f"OK schema: {fixture_path.relative_to(ROOT)}"
    )


def validate_manifest(
    document: dict[str, Any],
) -> None:
    generation = document["generation"]
    documents = document["documents"]

    expected_names = {
        "nodes.json",
        "edges.json",
        "neighbor-info.json",
        "observer-receptions.json",
        "stats.json",
        "meta.json",
        "configuration-warnings.json",
    }

    if set(documents) != expected_names:
        raise AssertionError(
            "O manifesto non contén "
            "o conxunto esperado de documentos"
        )

    for filename in expected_names:
        expected_path = (
            f"generations/{generation}/{filename}"
        )

        if documents[filename] != expected_path:
            raise AssertionError(
                "Ruta incoherente no manifesto "
                f"para {filename}"
            )

    parse_timestamp(document["generated_at"])

    print("OK semántica: manifest.valid.json")


def validate_nodes(document: dict[str, Any]) -> None:
    ids: set[str] = set()

    for node in document["nodes"]:
        node_id = node["id"]

        if node_id in ids:
            raise AssertionError(
                f"Identificador de nodo repetido: {node_id}"
            )

        ids.add(node_id)

        sources = node["sources"]
        source_ids = node["source_ids"]
        source_last_seen = node.get("source_last_seen")

        if set(sources) != set(source_ids):
            raise AssertionError(
                f"Fuentes incoherentes en {node_id}: "
                f"sources={sources}, "
                f"source_ids={list(source_ids)}"
            )

        if source_last_seen is not None:
            if set(sources) != set(source_last_seen):
                raise AssertionError(
                    f"Datas por fonte incoherentes en {node_id}: "
                    f"sources={sources}, "
                    f"source_last_seen={list(source_last_seen)}"
                )

            for observed_at in source_last_seen.values():
                parse_timestamp(observed_at)

        status = node["status"]

        temporal_states = (
            status["active"],
            status["recent"],
            status["historical"],
        )

        if sum(temporal_states) != 1:
            raise AssertionError(
                f"Estado temporal incoherente en {node_id}"
            )

        latitude = node["latitude"]
        longitude = node["longitude"]
        position_time = node["position_updated_at"]
        has_position = status["has_position"]

        position_complete = (
            latitude is not None
            and longitude is not None
            and position_time is not None
        )

        position_empty = (
            latitude is None
            and longitude is None
            and position_time is None
        )

        if has_position and not position_complete:
            raise AssertionError(
                f"Posición incompleta en {node_id}"
            )

        if not has_position and not position_empty:
            raise AssertionError(
                f"Posición residual en {node_id}"
            )

        first_seen = node["first_seen"]
        last_seen = node["last_seen"]

        last_dt = parse_timestamp(last_seen)

        if first_seen is not None:
            first_dt = parse_timestamp(first_seen)

            if first_dt > last_dt:
                raise AssertionError(
                    f"first_seen posterior a last_seen "
                    f"en {node_id}"
                )

        if position_time is not None:
            parse_timestamp(position_time)

    print("OK semántica: nodes.valid.json")


def validate_edges(document: dict[str, Any]) -> None:
    ids: set[str] = set()

    for edge in document["edges"]:
        edge_id = edge["id"]
        from_id = edge["from_id"]
        to_id = edge["to_id"]

        if edge_id in ids:
            raise AssertionError(
                f"Identificador de conexión repetido: {edge_id}"
            )

        ids.add(edge_id)

        if from_id == to_id:
            raise AssertionError(
                f"Conexión consigo misma: {edge_id}"
            )

        network_prefix = edge["network"] + ":"

        if not from_id.startswith(network_prefix):
            raise AssertionError(
                f"from_id incompatible en {edge_id}"
            )

        if not to_id.startswith(network_prefix):
            raise AssertionError(
                f"to_id incompatible en {edge_id}"
            )

        if not edge["directed"] and from_id > to_id:
            raise AssertionError(
                f"Extremos no ordenados en {edge_id}"
            )

        parse_timestamp(edge["last_seen"])

    print("OK semántica: edges.valid.json")


def validate_neighbor_info(
    document: dict[str, Any],
) -> None:
    identities: set[tuple[str, str, str, str]] = set()

    for observation in document["observations"]:
        source = observation["source"]
        from_id = observation["from_id"]
        to_id = observation["to_id"]
        observed_at = observation["observed_at"]

        if from_id == to_id:
            raise AssertionError(
                "NeighborInfo non pode observar o propio emisor"
            )

        identity = (
            source,
            from_id,
            to_id,
            observed_at,
        )

        if identity in identities:
            raise AssertionError(
                "Observación NeighborInfo duplicada: "
                f"{identity}"
            )

        identities.add(identity)
        parse_timestamp(observed_at)

    parse_timestamp(document["generated_at"])

    print(
        "OK semántica: neighbor-info.valid.json"
    )


def validate_observer_receptions(
    document: dict[str, Any],
) -> None:
    identities: set[
        tuple[str, str, str]
    ] = set()

    for reception in document["receptions"]:
        identity = (
            reception["node_id"],
            reception["observer_id"],
            reception["packet_hash"],
        )

        if identity in identities:
            raise AssertionError(
                "Recepción de observer duplicada: "
                f"{identity}"
            )

        identities.add(identity)
        parse_timestamp(reception["observed_at"])

    parse_timestamp(document["generated_at"])

    print(
        "OK semántica: "
        "observer-receptions.valid.json"
    )


def validate_stats(document: dict[str, Any]) -> None:
    totals = document["totals"]
    networks = document["networks"]

    temporal_total = (
        totals["active_nodes"]
        + totals["recent_nodes"]
        + totals["historical_nodes"]
    )

    if temporal_total != totals["nodes"]:
        raise AssertionError(
            "Los estados temporales generales "
            "no suman el total de nodos"
        )

    for network, values in networks.items():
        temporal_network = (
            values["active_nodes"]
            + values["recent_nodes"]
            + values["historical_nodes"]
        )

        if temporal_network != values["nodes"]:
            raise AssertionError(
                f"Estados temporales incoherentes "
                f"en {network}"
            )

        if values["positioned_nodes"] > values["nodes"]:
            raise AssertionError(
                f"Demasiados nodos posicionados "
                f"en {network}"
            )

    fields = (
        "nodes",
        "active_nodes",
        "recent_nodes",
        "historical_nodes",
        "positioned_nodes",
        "edges",
    )

    for field in fields:
        subtotal = sum(
            values[field]
            for values in networks.values()
        )

        if subtotal != totals[field]:
            raise AssertionError(
                f"El total de {field} no coincide "
                "con la suma por redes"
            )

    for source, values in document["sources"].items():
        has_error_time = values["last_error_at"] is not None
        has_error_text = values["last_error"] is not None

        if has_error_time != has_error_text:
            raise AssertionError(
                f"Estado de error incoherente en {source}"
            )

        if values["last_success"] is not None:
            parse_timestamp(values["last_success"])

        if values["last_error_at"] is not None:
            parse_timestamp(values["last_error_at"])

    print("OK semántica: stats.valid.json")


def validate_meta(document: dict[str, Any]) -> None:
    retention = document["retention"]

    if retention["historical_days"] < retention["recent_days"]:
        raise AssertionError(
            "historical_days debe ser mayor o igual "
            "que recent_days"
        )

    bounds = document["region"]["bounds"]

    if bounds is not None:
        if bounds["south"] >= bounds["north"]:
            raise AssertionError(
                "south debe ser menor que north"
            )

        if bounds["west"] >= bounds["east"]:
            raise AssertionError(
                "west debe ser menor que east"
            )

    parse_timestamp(document["generated_at"])

    print("OK semántica: meta.valid.json")


def validate_configuration_warnings(
    document: dict[str, Any],
) -> None:
    analysis = document["analysis"]
    nodes = document["nodes"]

    ids = [node["id"] for node in nodes]

    if len(ids) != len(set(ids)):
        raise AssertionError(
            "Hay identificadores repetidos en los avisos"
        )

    analyzed_nodes = analysis["analyzed_nodes"]
    nodes_with_warnings = analysis["nodes_with_warnings"]
    eligible_nodes = analysis["eligible_nodes"]

    if analyzed_nodes != len(nodes):
        raise AssertionError(
            "analyzed_nodes no coincide con la lista de nodos"
        )

    warned = sum(
        bool(node["warnings"])
        for node in nodes
    )

    if nodes_with_warnings != warned:
        raise AssertionError(
            "nodes_with_warnings no coincide con los avisos"
        )

    if analyzed_nodes > eligible_nodes:
        raise AssertionError(
            "Hay más nodos analizados que elegibles"
        )

    available = analysis["available"]
    updated_at = analysis["updated_at"]

    if available:
        if updated_at is None:
            raise AssertionError(
                "Un análisis disponible necesita updated_at"
            )
        parse_timestamp(updated_at)
    else:
        if updated_at is not None:
            raise AssertionError(
                "Un análisis no disponible no debe tener updated_at"
            )
        if analyzed_nodes != 0 or nodes_with_warnings != 0:
            raise AssertionError(
                "Un análisis no disponible debe tener "
                "contadores de análisis a cero"
            )
        if nodes:
            raise AssertionError(
                "Un análisis no disponible no debe incluir nodos"
            )

    parse_timestamp(document["generated_at"])

    print(
        "OK semántica: "
        "configuration-warnings.valid.json"
    )


def main() -> int:
    print("=== VALIDACIÓN DE CONTRATOS ===")

    for schema_path, fixture_path in PAIRS:
        validate_schema(schema_path, fixture_path)

    manifest = load_json(
        ROOT / "tests/fixtures/manifest.valid.json"
    )
    nodes = load_json(
        ROOT / "tests/fixtures/nodes.valid.json"
    )
    edges = load_json(
        ROOT / "tests/fixtures/edges.valid.json"
    )
    neighbor_info = load_json(
        ROOT / "tests/fixtures/neighbor-info.valid.json"
    )
    observer_receptions = load_json(
        ROOT
        / "tests/fixtures/observer-receptions.valid.json"
    )
    stats = load_json(
        ROOT / "tests/fixtures/stats.valid.json"
    )
    meta = load_json(
        ROOT / "tests/fixtures/meta.valid.json"
    )
    warnings = load_json(
        ROOT
        / "tests/fixtures/configuration-warnings.valid.json"
    )

    validate_manifest(manifest)
    validate_nodes(nodes)
    validate_edges(edges)
    validate_neighbor_info(neighbor_info)
    validate_observer_receptions(
        observer_receptions
    )
    validate_stats(stats)
    validate_meta(meta)
    validate_configuration_warnings(warnings)

    print()
    print("RESULTADO: todos los contratos son válidos.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
