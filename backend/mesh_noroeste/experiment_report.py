"""Construción dun informe reutilizable dos experimentos Meshtastic."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sqlite3
from statistics import mean, median
from typing import Any, Iterable, Mapping

from mesh_noroeste.experiment_analysis import (
    EXPERIMENT_BUCKET_SECONDS,
    experiment_time_buckets,
)
from mesh_noroeste.experiment_store import (
    connect_experiment_store,
)
from mesh_noroeste.territory import (
    TerritoryIndex,
)


EXPERIMENT_REPORT_SCHEMA = (
    "mesh-noroeste.meshtastic-experiment/v1"
)

EXPERIMENT_CHANNELS = (
    "LongFast",
    "NarrowFast",
)


def _finite_number(
    value: Any,
) -> float | None:
    if isinstance(value, bool):
        return None

    if not isinstance(value, (int, float)):
        return None

    number = float(value)

    if not math.isfinite(number):
        return None

    return number


def _json_numbers(
    value: str,
) -> tuple[float, ...]:
    try:
        document = json.loads(value)
    except (
        TypeError,
        json.JSONDecodeError,
    ):
        return ()

    if not isinstance(document, list):
        return ()

    result: list[float] = []

    for item in document:
        number = _finite_number(item)

        if number is not None:
            result.append(number)

    return tuple(result)


def _mean(
    values: Iterable[float],
) -> float | None:
    items = tuple(values)

    if not items:
        return None

    return float(mean(items))


def _median(
    values: Iterable[float],
) -> float | None:
    items = tuple(values)

    if not items:
        return None

    return float(median(items))


def _percentile(
    values: Iterable[float],
    fraction: float,
) -> float | None:
    items = sorted(values)

    if not items:
        return None

    if not 0 <= fraction <= 1:
        raise ValueError(
            "fraction debe estar entre 0 e 1"
        )

    if len(items) == 1:
        return float(items[0])

    position = (
        (len(items) - 1)
        * fraction
    )

    lower = int(position)
    upper = min(
        lower + 1,
        len(items) - 1,
    )

    weight = position - lower

    return float(
        items[lower] * (1 - weight)
        + items[upper] * weight
    )


def _iso_from_us(
    value: int | None,
) -> str | None:
    if value is None:
        return None

    return (
        datetime.fromtimestamp(
            value / 1_000_000,
            tz=timezone.utc,
        )
        .isoformat()
        .replace("+00:00", "Z")
    )


def _generated_at(
    value: str | None,
) -> str:
    if value is not None:
        if not isinstance(value, str):
            raise TypeError(
                "generated_at debe ser texto ou None"
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "generated_at non pode estar baleiro"
            )

        return normalized

    return (
        datetime.now(
            timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def _channel_rows(
    connection: sqlite3.Connection,
    channel: str,
    *,
    start_us: int | None,
    end_us: int | None,
    from_ids: Iterable[str] | None = None,
) -> list[sqlite3.Row]:
    clauses = [
        "channel = ?",
    ]

    parameters: list[Any] = [
        channel,
    ]

    if start_us is not None:
        clauses.append(
            "imported_at_us >= ?"
        )
        parameters.append(
            start_us
        )

    if end_us is not None:
        clauses.append(
            "imported_at_us < ?"
        )
        parameters.append(
            end_us
        )

    if from_ids is not None:
        normalized_ids = tuple(
            sorted(
                {
                    value.strip()
                    for value in from_ids
                    if (
                        isinstance(value, str)
                        and value.strip()
                    )
                }
            )
        )

        if not normalized_ids:
            return []

        placeholders = ", ".join(
            "?"
            for _ in normalized_ids
        )

        clauses.append(
            f"from_id IN ({placeholders})"
        )

        parameters.extend(
            normalized_ids
        )

    return connection.execute(
        f"""
        SELECT
            event_id,
            packet_id,
            from_id,
            channel,
            portnum,
            imported_at_us,
            gateway_count,
            stage_count,
            snr_values_json,
            rssi_values_json,
            route_discovery,
            telemetry_time,
            channel_utilization,
            air_util_tx,
            battery_level,
            voltage,
            uptime_seconds
        FROM experiment_observations
        WHERE {" AND ".join(clauses)}
        ORDER BY
            imported_at_us ASC,
            event_id ASC
        """,
        tuple(parameters),
    ).fetchall()


def channel_summary(
    connection: sqlite3.Connection,
    channel: str,
    *,
    start_us: int | None = None,
    end_us: int | None = None,
    from_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Resume un preset sen inventar métricas ausentes."""

    if channel not in EXPERIMENT_CHANNELS:
        raise ValueError(
            "channel debe ser LongFast ou NarrowFast"
        )

    rows = _channel_rows(
        connection,
        channel,
        start_us=start_us,
        end_us=end_us,
        from_ids=from_ids,
    )

    nodes: set[str] = set()

    snrs: list[float] = []
    rssis: list[float] = []

    gateways: list[float] = []
    stages: list[float] = []

    utilization: list[float] = []
    air_tx: list[float] = []

    packets_with_rf = 0
    rf_samples = 0
    packets_multi_gateway = 0
    packets_multi_stage = 0
    route_discovery_packets = 0
    telemetry_samples = 0

    oldest_us: int | None = None
    newest_us: int | None = None

    for row in rows:
        nodes.add(
            row["from_id"]
        )

        imported_at_us = int(
            row["imported_at_us"]
        )

        oldest_us = (
            imported_at_us
            if oldest_us is None
            else min(
                oldest_us,
                imported_at_us,
            )
        )

        newest_us = (
            imported_at_us
            if newest_us is None
            else max(
                newest_us,
                imported_at_us,
            )
        )

        gateway_count = int(
            row["gateway_count"]
        )

        stage_count = int(
            row["stage_count"]
        )

        gateways.append(
            float(gateway_count)
        )

        stages.append(
            float(stage_count)
        )

        if gateway_count > 1:
            packets_multi_gateway += 1

        if stage_count > 1:
            packets_multi_stage += 1

        if int(
            row["route_discovery"]
        ):
            route_discovery_packets += 1

        row_snrs = _json_numbers(
            row["snr_values_json"]
        )

        row_rssis = _json_numbers(
            row["rssi_values_json"]
        )

        if row_snrs or row_rssis:
            packets_with_rf += 1

        snrs.extend(
            row_snrs
        )

        rssis.extend(
            row_rssis
        )

        rf_samples += max(
            len(row_snrs),
            len(row_rssis),
        )

        channel_utilization = (
            _finite_number(
                row[
                    "channel_utilization"
                ]
            )
        )

        air_util_tx = (
            _finite_number(
                row["air_util_tx"]
            )
        )

        if (
            channel_utilization
            is not None
            or air_util_tx is not None
        ):
            telemetry_samples += 1

        if (
            channel_utilization
            is not None
        ):
            utilization.append(
                channel_utilization
            )

        if air_util_tx is not None:
            air_tx.append(
                air_util_tx
            )

    return {
        "channel": channel,
        "packets": len(rows),
        "nodes": len(nodes),
        "oldest_us": oldest_us,
        "newest_us": newest_us,
        "oldest_at": (
            _iso_from_us(
                oldest_us
            )
        ),
        "newest_at": (
            _iso_from_us(
                newest_us
            )
        ),
        "packets_with_rf": (
            packets_with_rf
        ),
        "rf_samples": rf_samples,
        "packets_multi_gateway": (
            packets_multi_gateway
        ),
        "packets_multi_stage": (
            packets_multi_stage
        ),
        "route_discovery_packets": (
            route_discovery_packets
        ),
        "telemetry_samples": (
            telemetry_samples
        ),
        "snr": {
            "mean": _mean(snrs),
            "median": _median(snrs),
            "p10": _percentile(
                snrs,
                0.10,
            ),
            "p90": _percentile(
                snrs,
                0.90,
            ),
        },
        "rssi": {
            "mean": _mean(rssis),
            "median": _median(rssis),
            "p10": _percentile(
                rssis,
                0.10,
            ),
            "p90": _percentile(
                rssis,
                0.90,
            ),
        },
        "gateways": {
            "mean": _mean(
                gateways
            ),
            "median": _median(
                gateways
            ),
        },
        "stages": {
            "mean": _mean(
                stages
            ),
            "median": _median(
                stages
            ),
        },
        "channel_utilization": {
            "samples": len(
                utilization
            ),
            "mean": _mean(
                utilization
            ),
            "median": _median(
                utilization
            ),
            "p10": _percentile(
                utilization,
                0.10,
            ),
            "p90": _percentile(
                utilization,
                0.90,
            ),
        },
        "air_util_tx": {
            "samples": len(
                air_tx
            ),
            "mean": _mean(
                air_tx
            ),
            "median": _median(
                air_tx
            ),
            "p10": _percentile(
                air_tx,
                0.10,
            ),
            "p90": _percentile(
                air_tx,
                0.90,
            ),
        },
    }



def _experiment_emitter_ids(
    connection: sqlite3.Connection,
    channel: str,
    *,
    start_us: int | None,
    end_us: int | None,
) -> tuple[str, ...]:
    """Obtén os emisores únicos dun preset e xanela."""

    rows = _channel_rows(
        connection,
        channel,
        start_us=start_us,
        end_us=end_us,
    )

    return tuple(
        sorted(
            {
                str(
                    row["from_id"]
                )
                for row in rows
            }
        )
    )


def _territory_node_index(
    nodes_document: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    """Indexa os nodos públicos por identificador canónico."""

    records = nodes_document.get(
        "nodes"
    )

    if not isinstance(records, list):
        raise ValueError(
            "nodes_document debe conter unha lista nodes"
        )

    result: dict[
        str,
        Mapping[str, Any],
    ] = {}

    for record in records:
        if not isinstance(
            record,
            Mapping,
        ):
            continue

        node_id = record.get(
            "id"
        )

        if (
            not isinstance(node_id, str)
            or not node_id.strip()
        ):
            continue

        result[
            node_id.strip()
        ] = record

    return result


def _territory_match_document(
    match,
) -> dict[str, Any]:
    return {
        "id": match.id,
        "name": match.name,
        "province": match.parent,
        "country": match.country,
    }


def _territorial_channel_report(
    connection: sqlite3.Connection,
    channel: str,
    *,
    nodes_by_id: Mapping[
        str,
        Mapping[str, Any],
    ],
    territory_index: TerritoryIndex,
    start_us: int | None,
    end_us: int | None,
) -> dict[str, Any]:
    """Agrupa un preset por concello galego sen ocultar incerteza."""

    emitter_ids = (
        _experiment_emitter_ids(
            connection,
            channel,
            start_us=start_us,
            end_us=end_us,
        )
    )

    municipality_emitters: dict[
        str,
        set[str],
    ] = {}

    municipality_metadata: dict[
        str,
        dict[str, Any],
    ] = {}

    municipality_exact: dict[
        str,
        set[str],
    ] = {}

    municipality_compatible: dict[
        str,
        set[str],
    ] = {}

    province_emitters: dict[
        str,
        set[str],
    ] = {}

    exact_emitters: set[str] = set()
    compatible_emitters: set[str] = set()
    ambiguous_emitters: set[str] = set()
    outside_emitters: set[str] = set()
    unlocated_emitters: set[str] = set()

    ambiguous: list[
        dict[str, Any]
    ] = []

    outside: list[
        dict[str, Any]
    ] = []

    for emitter_id in emitter_ids:
        node = nodes_by_id.get(
            emitter_id
        )

        if node is None:
            unlocated_emitters.add(
                emitter_id
            )

            outside.append(
                {
                    "from_id": emitter_id,
                    "reason": (
                        "node_not_published"
                    ),
                    "name": None,
                    "latitude": None,
                    "longitude": None,
                    "position_precision_bits": None,
                }
            )

            continue

        latitude = node.get(
            "latitude"
        )
        longitude = node.get(
            "longitude"
        )
        precision_bits = node.get(
            "position_precision_bits"
        )

        name = (
            node.get("long_name")
            or node.get("short_name")
        )

        if (
            latitude is None
            or longitude is None
        ):
            unlocated_emitters.add(
                emitter_id
            )

            outside.append(
                {
                    "from_id": emitter_id,
                    "reason": (
                        "missing_position"
                    ),
                    "name": name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "position_precision_bits": (
                        precision_bits
                    ),
                }
            )

            continue

        classification = (
            territory_index.classify(
                latitude,
                longitude,
                level="municipality",
                precision_bits=(
                    precision_bits
                    if isinstance(
                        precision_bits,
                        int,
                    )
                    and not isinstance(
                        precision_bits,
                        bool,
                    )
                    else None
                ),
            )
        )

        if (
            classification.status
            == "exact"
        ):
            match = (
                classification.exact
            )

            if match is None:
                raise ValueError(
                    "Clasificación exact sen territorio"
                )

            exact_emitters.add(
                emitter_id
            )

            selected_match = match
            assignment = "exact"

        elif (
            classification.status
            == "compatible"
        ):
            if (
                len(
                    classification.compatible
                )
                != 1
            ):
                raise ValueError(
                    "Clasificación compatible "
                    "sen territorio único"
                )

            compatible_emitters.add(
                emitter_id
            )

            selected_match = (
                classification.compatible[0]
            )
            assignment = "compatible"

        elif (
            classification.status
            == "ambiguous"
        ):
            ambiguous_emitters.add(
                emitter_id
            )

            ambiguous.append(
                {
                    "from_id": emitter_id,
                    "name": name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "position_precision_bits": (
                        precision_bits
                    ),
                    "candidates": [
                        _territory_match_document(
                            match
                        )
                        for match
                        in classification.compatible
                    ],
                }
            )

            continue

        elif (
            classification.status
            == "outside"
        ):
            outside_emitters.add(
                emitter_id
            )

            outside.append(
                {
                    "from_id": emitter_id,
                    "reason": (
                        "outside_galicia"
                    ),
                    "name": name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "position_precision_bits": (
                        precision_bits
                    ),
                }
            )

            continue

        else:
            raise ValueError(
                "Estado territorial non recoñecido: "
                f"{classification.status!r}"
            )

        municipality_id = (
            selected_match.id
        )

        municipality_metadata[
            municipality_id
        ] = _territory_match_document(
            selected_match
        )

        municipality_emitters.setdefault(
            municipality_id,
            set(),
        ).add(
            emitter_id
        )

        if assignment == "exact":
            municipality_exact.setdefault(
                municipality_id,
                set(),
            ).add(
                emitter_id
            )
        else:
            municipality_compatible.setdefault(
                municipality_id,
                set(),
            ).add(
                emitter_id
            )

        province = (
            selected_match.parent
            or "Sen provincia"
        )

        province_emitters.setdefault(
            province,
            set(),
        ).add(
            emitter_id
        )

    municipalities: list[
        dict[str, Any]
    ] = []

    for municipality_id, ids in (
        municipality_emitters.items()
    ):
        metadata = (
            municipality_metadata[
                municipality_id
            ]
        )

        municipalities.append(
            {
                **metadata,
                "classification": {
                    "exact_nodes": len(
                        municipality_exact.get(
                            municipality_id,
                            set(),
                        )
                    ),
                    "compatible_nodes": len(
                        municipality_compatible.get(
                            municipality_id,
                            set(),
                        )
                    ),
                },
                "metrics": channel_summary(
                    connection,
                    channel,
                    start_us=start_us,
                    end_us=end_us,
                    from_ids=ids,
                ),
            }
        )

    municipalities.sort(
        key=lambda item: (
            -int(
                item["metrics"][
                    "packets"
                ]
            ),
            str(
                item["province"]
                or ""
            ),
            str(
                item["name"]
            ),
        )
    )

    provinces: list[
        dict[str, Any]
    ] = []

    for province, ids in (
        province_emitters.items()
    ):
        provinces.append(
            {
                "name": province,
                "metrics": channel_summary(
                    connection,
                    channel,
                    start_us=start_us,
                    end_us=end_us,
                    from_ids=ids,
                ),
            }
        )

    provinces.sort(
        key=lambda item: (
            -int(
                item["metrics"][
                    "packets"
                ]
            ),
            str(
                item["name"]
            ),
        )
    )

    assigned_emitters = (
        exact_emitters
        | compatible_emitters
    )

    total_summary = (
        channel_summary(
            connection,
            channel,
            start_us=start_us,
            end_us=end_us,
        )
    )

    assigned_summary = (
        channel_summary(
            connection,
            channel,
            start_us=start_us,
            end_us=end_us,
            from_ids=assigned_emitters,
        )
    )

    ambiguous_summary = (
        channel_summary(
            connection,
            channel,
            start_us=start_us,
            end_us=end_us,
            from_ids=ambiguous_emitters,
        )
    )

    outside_group = (
        outside_emitters
        | unlocated_emitters
    )

    outside_summary = (
        channel_summary(
            connection,
            channel,
            start_us=start_us,
            end_us=end_us,
            from_ids=outside_group,
        )
    )

    total_packets = int(
        total_summary["packets"]
    )

    assigned_packets = int(
        assigned_summary["packets"]
    )

    return {
        "summary": {
            "emitters": len(
                emitter_ids
            ),
            "assigned_emitters": len(
                assigned_emitters
            ),
            "exact_emitters": len(
                exact_emitters
            ),
            "compatible_emitters": len(
                compatible_emitters
            ),
            "ambiguous_emitters": len(
                ambiguous_emitters
            ),
            "outside_emitters": len(
                outside_emitters
            ),
            "unlocated_emitters": len(
                unlocated_emitters
            ),
            "packets": total_packets,
            "assigned_packets": (
                assigned_packets
            ),
            "assigned_packet_percent": (
                (
                    assigned_packets
                    / total_packets
                    * 100.0
                )
                if total_packets
                else 0.0
            ),
        },
        "provinces": provinces,
        "municipalities": municipalities,
        "ambiguous": {
            "metrics": ambiguous_summary,
            "nodes": sorted(
                ambiguous,
                key=lambda item: (
                    -len(
                        item["candidates"]
                    ),
                    str(
                        item["name"]
                        or item["from_id"]
                    ),
                ),
            ),
        },
        "outside": {
            "metrics": outside_summary,
            "nodes": sorted(
                outside,
                key=lambda item: (
                    str(
                        item["reason"]
                    ),
                    str(
                        item["name"]
                        or item["from_id"]
                    ),
                ),
            ),
        },
    }


def build_experiment_territories(
    connection: sqlite3.Connection,
    *,
    nodes_document: Mapping[str, Any],
    territory_index: TerritoryIndex,
    start_us: int | None = None,
    end_us: int | None = None,
) -> dict[str, Any]:
    """Constrúe a desagregación territorial por preset."""

    if not isinstance(
        nodes_document,
        Mapping,
    ):
        raise TypeError(
            "nodes_document debe ser un mapping"
        )

    if not isinstance(
        territory_index,
        TerritoryIndex,
    ):
        raise TypeError(
            "territory_index debe ser TerritoryIndex"
        )

    nodes_by_id = (
        _territory_node_index(
            nodes_document
        )
    )

    return {
        channel: (
            _territorial_channel_report(
                connection,
                channel,
                nodes_by_id=nodes_by_id,
                territory_index=(
                    territory_index
                ),
                start_us=start_us,
                end_us=end_us,
            )
        )
        for channel in EXPERIMENT_CHANNELS
    }


def _bucket_document(
    bucket,
) -> dict[str, Any]:
    document = asdict(bucket)

    document["start_at"] = (
        _iso_from_us(
            bucket.start_us
        )
    )

    document["end_at"] = (
        _iso_from_us(
            bucket.end_us
        )
    )

    return document


def _comparison_window(
    connection: sqlite3.Connection,
    summaries: dict[
        str,
        dict[str, Any],
    ],
) -> dict[str, Any]:
    """Constrúe a intersección temporal observable dos dous presets.

    ``end_us`` mantén a mesma semántica ca o resto do informe:
    é un límite exclusivo. Engádese un microsegundo á última
    observación común para non excluír o evento situado exactamente
    no extremo temporal dereito.
    """

    missing = [
        channel
        for channel in EXPERIMENT_CHANNELS
        if (
            summaries[channel].get(
                "oldest_us"
            )
            is None
            or summaries[channel].get(
                "newest_us"
            )
            is None
        )
    ]

    if missing:
        return {
            "available": False,
            "reason": (
                "missing_channel_data"
            ),
            "missing_channels": missing,
            "start_us": None,
            "end_us": None,
            "start_at": None,
            "end_at": None,
            "duration_seconds": 0.0,
            "channels": {},
        }

    overlap_start_us = max(
        int(
            summaries[channel][
                "oldest_us"
            ]
        )
        for channel in EXPERIMENT_CHANNELS
    )

    overlap_last_us = min(
        int(
            summaries[channel][
                "newest_us"
            ]
        )
        for channel in EXPERIMENT_CHANNELS
    )

    if overlap_last_us < overlap_start_us:
        return {
            "available": False,
            "reason": (
                "no_temporal_overlap"
            ),
            "missing_channels": [],
            "start_us": None,
            "end_us": None,
            "start_at": None,
            "end_at": None,
            "duration_seconds": 0.0,
            "channels": {},
        }

    # channel_summary usa imported_at_us < end_us.
    # Convertimos polo tanto o último instante observable
    # nun límite superior exclusivo sen perder ese evento.
    overlap_end_us = (
        overlap_last_us + 1
    )

    channels = {
        channel: channel_summary(
            connection,
            channel,
            start_us=overlap_start_us,
            end_us=overlap_end_us,
        )
        for channel in EXPERIMENT_CHANNELS
    }

    return {
        "available": True,
        "reason": None,
        "missing_channels": [],
        "start_us": overlap_start_us,
        "end_us": overlap_end_us,
        "start_at": _iso_from_us(
            overlap_start_us
        ),
        "end_at": _iso_from_us(
            overlap_end_us
        ),
        "duration_seconds": (
            (
                overlap_end_us
                - overlap_start_us
            )
            / 1_000_000
        ),
        "channels": channels,
    }


def build_experiment_report(
    connection: sqlite3.Connection,
    *,
    generated_at: str | None = None,
    start_us: int | None = None,
    end_us: int | None = None,
    bucket_seconds: int = (
        EXPERIMENT_BUCKET_SECONDS
    ),
    nodes_document: Mapping[str, Any] | None = None,
    territory_index: TerritoryIndex | None = None,
) -> dict[str, Any]:
    """Constrúe o documento canónico para Excel e visualización."""

    if (
        start_us is not None
        and (
            isinstance(start_us, bool)
            or not isinstance(
                start_us,
                int,
            )
        )
    ):
        raise TypeError(
            "start_us debe ser enteiro ou None"
        )

    if (
        end_us is not None
        and (
            isinstance(end_us, bool)
            or not isinstance(
                end_us,
                int,
            )
        )
    ):
        raise TypeError(
            "end_us debe ser enteiro ou None"
        )

    if (
        start_us is not None
        and end_us is not None
        and end_us <= start_us
    ):
        raise ValueError(
            "end_us debe ser maior ca start_us"
        )

    summaries: dict[
        str,
        dict[str, Any],
    ] = {}

    series: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for channel in EXPERIMENT_CHANNELS:
        summaries[channel] = (
            channel_summary(
                connection,
                channel,
                start_us=start_us,
                end_us=end_us,
            )
        )

        buckets = experiment_time_buckets(
            connection,
            channel,
            start_us=start_us,
            end_us=end_us,
            bucket_seconds=bucket_seconds,
        )

        series[channel] = [
            _bucket_document(
                bucket
            )
            for bucket in buckets
        ]

    territories = None

    if (
        nodes_document is not None
        and territory_index is not None
    ):
        territories = (
            build_experiment_territories(
                connection,
                nodes_document=(
                    nodes_document
                ),
                territory_index=(
                    territory_index
                ),
                start_us=start_us,
                end_us=end_us,
            )
        )

    document = {
        "schema": (
            EXPERIMENT_REPORT_SCHEMA
        ),
        "generated_at": (
            _generated_at(
                generated_at
            )
        ),
        "window": {
            "start_us": start_us,
            "end_us": end_us,
            "start_at": (
                _iso_from_us(
                    start_us
                )
            ),
            "end_at": (
                _iso_from_us(
                    end_us
                )
            ),
        },
        "bucket_seconds": (
            bucket_seconds
        ),
        "channels": summaries,
        "series": series,
        "comparison_window": (
            _comparison_window(
                connection,
                summaries,
            )
        ),
        "evidence": {
            "observational": {
                "available": True,
                "source": (
                    "passive_observation"
                ),
            },
            "controlled": {
                "available": False,
                "tests": [],
                "methodology": None,
            },
        },
        "methodology": {
            "rf_zero_zero_missing": True,
            "delivery_rate_requires_controlled_test": True,
            "collisions_are_not_directly_observed": True,
            "ingestion_delay_is_not_radio_latency": True,
            (
                "observational_data_does_not_"
                "isolate_preset_effect"
            ): True,
        },
    }

    if territories is not None:
        document[
            "territories"
        ] = territories

    return document


def write_experiment_report(
    database: Path | str,
    output: Path | str,
    *,
    generated_at: str | None = None,
    start_us: int | None = None,
    end_us: int | None = None,
    bucket_seconds: int = (
        EXPERIMENT_BUCKET_SECONDS
    ),
) -> Path:
    """Constrúe e escribe o informe JSON de forma reproducible."""

    connection = (
        connect_experiment_store(
            database
        )
    )

    try:
        report = (
            build_experiment_report(
                connection,
                generated_at=generated_at,
                start_us=start_us,
                end_us=end_us,
                bucket_seconds=(
                    bucket_seconds
                ),
            )
        )

    finally:
        connection.close()

    output_path = Path(
        output
    ).expanduser().resolve()

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return output_path
