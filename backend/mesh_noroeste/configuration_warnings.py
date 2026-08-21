"""Adaptación independiente de avisos de configuración."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from mesh_noroeste.normalization import (
    canonical_node_id,
    normalize_timestamp,
)


SCHEMA_ID = "mesh-noroeste.configuration-warnings/v1"

SEVERITIES = {
    "medium",
    "high",
    "critical",
}

SOURCE_WARNING_KEYS = {
    "range_test": "range_test_active",
    "position_fixed": "fixed_position_frequent",
    "position_mobile": "mobile_position_frequent",
    "nodeinfo": "node_info_frequent",
    "telemetry_device": "device_telemetry_frequent",
    "telemetry_environment": "environment_telemetry_frequent",
    "telemetry_power": "power_telemetry_frequent",
    "routing": "routing_frequent",
    "position_flags": "position_fields_unnecessary",
    "traceroute_auto": "automatic_traceroute_frequent",
    "hop_limit_high": "hop_limit_high",
    "client_base_fw": "client_base_firmware_old",
    "client_mute_mobile": "client_mute_mobile",
}

_SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
}


class ConfigurationWarningsError(ValueError):
    """Indica que el documento de análisis no es válido."""


def _required(
    record: Mapping[Any, Any],
    key: str,
    context: str,
) -> Any:
    if key not in record:
        raise ConfigurationWarningsError(
            f"{context}: falta el campo {key!r}"
        )

    return record[key]


def _eligible_node_ids(
    published_nodes: Iterable[Mapping[str, Any]],
) -> set[str]:
    eligible: set[str] = set()
    seen: set[str] = set()

    for index, node in enumerate(published_nodes):
        if not isinstance(node, Mapping):
            raise ConfigurationWarningsError(
                f"Nodo publicado {index}: debe ser un objeto"
            )

        node_id = _required(
            node,
            "id",
            f"Nodo publicado {index}",
        )
        network = _required(
            node,
            "network",
            f"Nodo publicado {index}",
        )
        sources = _required(
            node,
            "sources",
            f"Nodo publicado {index}",
        )

        if not isinstance(node_id, str):
            raise ConfigurationWarningsError(
                f"Nodo publicado {index}: id debe ser texto"
            )

        if node_id in seen:
            raise ConfigurationWarningsError(
                f"Nodo publicado duplicado: {node_id}"
            )

        seen.add(node_id)

        if not isinstance(sources, list):
            raise ConfigurationWarningsError(
                f"Nodo publicado {index}: sources debe ser una lista"
            )

        if (
            network == "meshtastic"
            and "ozulo_map" in sources
        ):
            eligible.add(node_id)

    return eligible


def _warnings(
    record: Mapping[Any, Any],
    index: int,
) -> list[dict[str, str]]:
    raw_issues = _required(
        record,
        "issues",
        f"Registro {index}",
    )

    if not isinstance(raw_issues, list):
        raise ConfigurationWarningsError(
            f"Registro {index}: issues debe ser una lista"
        )

    normalized: list[dict[str, str]] = []
    seen_keys: set[str] = set()

    for issue_index, issue in enumerate(raw_issues):
        context = f"Registro {index}, aviso {issue_index}"

        if not isinstance(issue, Mapping):
            raise ConfigurationWarningsError(
                f"{context}: debe ser un objeto"
            )

        source_key = _required(issue, "key", context)
        severity = _required(issue, "severity", context)

        if not isinstance(source_key, str):
            raise ConfigurationWarningsError(
                f"{context}: key debe ser texto"
            )

        if severity not in SEVERITIES:
            raise ConfigurationWarningsError(
                f"{context}: severidad no admitida"
            )

        key = SOURCE_WARNING_KEYS.get(source_key)

        if key is None:
            continue

        if key in seen_keys:
            raise ConfigurationWarningsError(
                f"Registro {index}: aviso duplicado {key}"
            )

        seen_keys.add(key)
        normalized.append({
            "key": key,
            "severity": severity,
        })

    normalized.sort(
        key=lambda warning: (
            _SEVERITY_ORDER[warning["severity"]],
            warning["key"],
        )
    )

    return normalized


def build_unavailable_configuration_warnings_document(
    published_nodes: Iterable[Mapping[str, Any]],
    *,
    generated_at: Any,
) -> dict[str, Any]:
    """Representa un análisis temporalmente no disponible."""

    eligible = _eligible_node_ids(published_nodes)

    return {
        "schema": SCHEMA_ID,
        "generated_at": normalize_timestamp(generated_at),
        "analysis": {
            "source": "ozulo_map",
            "available": False,
            "updated_at": None,
            "eligible_nodes": len(eligible),
            "analyzed_nodes": 0,
            "nodes_with_warnings": 0,
        },
        "nodes": [],
    }


def build_configuration_warnings_document(
    source_document: Any,
    published_nodes: Iterable[Mapping[str, Any]],
    *,
    generated_at: Any,
) -> dict[str, Any]:
    """Cruza el análisis con los nodos Meshtastic publicados."""

    if not isinstance(source_document, Mapping):
        raise ConfigurationWarningsError(
            "La raíz del análisis debe ser un objeto"
        )

    try:
        updated_at = normalize_timestamp(
            _required(
                source_document,
                "updated",
                "Análisis",
            )
        )
    except (TypeError, ValueError) as exc:
        raise ConfigurationWarningsError(
            "Análisis: updated no es un timestamp válido"
        ) from exc

    records = _required(
        source_document,
        "nodes",
        "Análisis",
    )

    if not isinstance(records, list):
        raise ConfigurationWarningsError(
            "Análisis: nodes debe ser una lista"
        )

    eligible = _eligible_node_ids(published_nodes)
    analyzed: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()

    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise ConfigurationWarningsError(
                f"Registro {index}: debe ser un objeto"
            )

        source_id = _required(
            record,
            "id",
            f"Registro {index}",
        )

        try:
            node_id = canonical_node_id(
                "meshtastic",
                source_id,
            )
        except (TypeError, ValueError) as exc:
            raise ConfigurationWarningsError(
                f"Registro {index}: id Meshtastic inválido"
            ) from exc

        if node_id in seen_source_ids:
            raise ConfigurationWarningsError(
                f"Análisis: id duplicado {node_id}"
            )

        seen_source_ids.add(node_id)
        warnings = _warnings(record, index)

        if node_id not in eligible:
            continue

        analyzed.append({
            "id": node_id,
            "warnings": warnings,
        })

    analyzed.sort(key=lambda node: node["id"])

    return {
        "schema": SCHEMA_ID,
        "generated_at": normalize_timestamp(generated_at),
        "analysis": {
            "source": "ozulo_map",
            "available": True,
            "updated_at": updated_at,
            "eligible_nodes": len(eligible),
            "analyzed_nodes": len(analyzed),
            "nodes_with_warnings": sum(
                bool(node["warnings"])
                for node in analyzed
            ),
        },
        "nodes": analyzed,
    }
