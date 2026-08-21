"""Análise agregada dos experimentos Meshtastic LongFast/NarrowFast."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import sqlite3
from statistics import mean, median
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class ExperimentPresetSummary:
    """Resumo estatístico dun preset nunha xanela temporal."""

    channel: str

    packets: int
    nodes: int

    packets_with_rf: int
    rf_samples: int

    packets_multi_gateway: int
    packets_multi_stage: int
    route_discovery_packets: int

    telemetry_samples: int

    oldest_us: int | None
    newest_us: int | None

    snr_mean: float | None
    snr_median: float | None
    snr_p10: float | None
    snr_p90: float | None

    rssi_mean: float | None
    rssi_median: float | None
    rssi_p10: float | None
    rssi_p90: float | None

    gateway_mean: float | None
    gateway_median: float | None

    stage_mean: float | None
    stage_median: float | None

    channel_utilization_mean: float | None
    channel_utilization_median: float | None

    air_util_tx_mean: float | None
    air_util_tx_median: float | None


@dataclass(frozen=True, slots=True)
class ExperimentAnalysis:
    """Resultado completo da análise por preset."""

    summaries: tuple[ExperimentPresetSummary, ...]

    @property
    def by_channel(
        self,
    ) -> dict[str, ExperimentPresetSummary]:
        return {
            summary.channel: summary
            for summary in self.summaries
        }


def _finite_number(
    value: Any,
) -> float | None:
    if isinstance(value, bool):
        return None

    if not isinstance(value, (int, float)):
        return None

    normalized = float(value)

    if not math.isfinite(normalized):
        return None

    return normalized


def _json_numbers(
    value: Any,
) -> tuple[float, ...]:
    if not isinstance(value, str):
        return ()

    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return ()

    if not isinstance(decoded, list):
        return ()

    result = []

    for item in decoded:
        normalized = _finite_number(item)

        if normalized is not None:
            result.append(normalized)

    return tuple(result)


def _percentile(
    values: Iterable[float],
    fraction: float,
) -> float | None:
    normalized = sorted(
        float(value)
        for value in values
    )

    if not normalized:
        return None

    if len(normalized) == 1:
        return normalized[0]

    position = (
        (len(normalized) - 1)
        * fraction
    )

    lower = int(
        math.floor(position)
    )

    upper = int(
        math.ceil(position)
    )

    if lower == upper:
        return normalized[lower]

    weight = position - lower

    return (
        normalized[lower]
        * (1.0 - weight)
        + normalized[upper]
        * weight
    )


def _mean(
    values: Iterable[float],
) -> float | None:
    normalized = tuple(values)

    if not normalized:
        return None

    return float(
        mean(normalized)
    )


def _median(
    values: Iterable[float],
) -> float | None:
    normalized = tuple(values)

    if not normalized:
        return None

    return float(
        median(normalized)
    )


def _validated_range(
    start_us: int | None,
    end_us: int | None,
) -> tuple[int | None, int | None]:
    for name, value in (
        ("start_us", start_us),
        ("end_us", end_us),
    ):
        if value is None:
            continue

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
        ):
            raise TypeError(
                f"{name} debe ser un enteiro ou None"
            )

        if value < 0:
            raise ValueError(
                f"{name} non pode ser negativo"
            )

    if (
        start_us is not None
        and end_us is not None
        and end_us <= start_us
    ):
        raise ValueError(
            "end_us debe ser maior ca start_us"
        )

    return start_us, end_us


def _rows_for_channel(
    connection: sqlite3.Connection,
    channel: str,
    *,
    start_us: int | None,
    end_us: int | None,
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

    sql = """
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
        WHERE
    """

    sql += " AND ".join(
        clauses
    )

    sql += """
        ORDER BY
            imported_at_us ASC,
            event_id ASC
    """

    return list(
        connection.execute(
            sql,
            parameters,
        ).fetchall()
    )


def summarize_channel(
    connection: sqlite3.Connection,
    channel: str,
    *,
    start_us: int | None = None,
    end_us: int | None = None,
) -> ExperimentPresetSummary:
    """Resume un preset para unha xanela temporal."""

    if not isinstance(
        connection,
        sqlite3.Connection,
    ):
        raise TypeError(
            "connection debe ser sqlite3.Connection"
        )

    if channel not in {
        "LongFast",
        "NarrowFast",
    }:
        raise ValueError(
            "channel debe ser LongFast ou NarrowFast"
        )

    start_us, end_us = (
        _validated_range(
            start_us,
            end_us,
        )
    )

    rows = _rows_for_channel(
        connection,
        channel,
        start_us=start_us,
        end_us=end_us,
    )

    snrs: list[float] = []
    rssis: list[float] = []

    gateways: list[float] = []
    stages: list[float] = []

    channel_utilization: list[float] = []
    air_util_tx: list[float] = []

    packets_with_rf = 0
    rf_samples = 0
    packets_multi_gateway = 0
    packets_multi_stage = 0
    route_discovery_packets = 0
    telemetry_samples = 0

    nodes: set[str] = set()

    imported_times: list[int] = []

    for row in rows:
        nodes.add(
            row["from_id"]
        )

        imported_times.append(
            int(
                row["imported_at_us"]
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

        utilization = _finite_number(
            row["channel_utilization"]
        )

        air_tx = _finite_number(
            row["air_util_tx"]
        )

        if (
            utilization is not None
            or air_tx is not None
        ):
            telemetry_samples += 1

        if utilization is not None:
            channel_utilization.append(
                utilization
            )

        if air_tx is not None:
            air_util_tx.append(
                air_tx
            )

    return ExperimentPresetSummary(
        channel=channel,
        packets=len(rows),
        nodes=len(nodes),
        packets_with_rf=packets_with_rf,
        rf_samples=rf_samples,
        packets_multi_gateway=(
            packets_multi_gateway
        ),
        packets_multi_stage=(
            packets_multi_stage
        ),
        route_discovery_packets=(
            route_discovery_packets
        ),
        telemetry_samples=(
            telemetry_samples
        ),
        oldest_us=(
            min(imported_times)
            if imported_times
            else None
        ),
        newest_us=(
            max(imported_times)
            if imported_times
            else None
        ),
        snr_mean=_mean(snrs),
        snr_median=_median(snrs),
        snr_p10=_percentile(
            snrs,
            0.10,
        ),
        snr_p90=_percentile(
            snrs,
            0.90,
        ),
        rssi_mean=_mean(rssis),
        rssi_median=_median(rssis),
        rssi_p10=_percentile(
            rssis,
            0.10,
        ),
        rssi_p90=_percentile(
            rssis,
            0.90,
        ),
        gateway_mean=_mean(
            gateways
        ),
        gateway_median=_median(
            gateways
        ),
        stage_mean=_mean(
            stages
        ),
        stage_median=_median(
            stages
        ),
        channel_utilization_mean=(
            _mean(
                channel_utilization
            )
        ),
        channel_utilization_median=(
            _median(
                channel_utilization
            )
        ),
        air_util_tx_mean=_mean(
            air_util_tx
        ),
        air_util_tx_median=_median(
            air_util_tx
        ),
    )


def analyze_experiment(
    connection: sqlite3.Connection,
    *,
    start_us: int | None = None,
    end_us: int | None = None,
) -> ExperimentAnalysis:
    """Constrúe o resumo comparable LongFast/NarrowFast."""

    start_us, end_us = (
        _validated_range(
            start_us,
            end_us,
        )
    )

    summaries = tuple(
        summarize_channel(
            connection,
            channel,
            start_us=start_us,
            end_us=end_us,
        )
        for channel in (
            "LongFast",
            "NarrowFast",
        )
    )

    return ExperimentAnalysis(
        summaries=summaries
    )


EXPERIMENT_BUCKET_SECONDS = 15 * 60
EXPERIMENT_BUCKET_US = (
    EXPERIMENT_BUCKET_SECONDS
    * 1_000_000
)


@dataclass(frozen=True, slots=True)
class ExperimentTimeBucket:
    """Resumo experimental dun intervalo temporal fixo."""

    channel: str

    start_us: int
    end_us: int

    packets: int
    nodes: int

    packets_with_rf: int
    rf_samples: int

    packets_multi_gateway: int
    packets_multi_stage: int

    route_discovery_packets: int
    telemetry_samples: int

    snr_mean: float | None
    snr_median: float | None

    rssi_mean: float | None
    rssi_median: float | None

    gateway_mean: float | None

    channel_utilization_mean: float | None
    air_util_tx_mean: float | None


def _bucket_size_us(
    bucket_seconds: int,
) -> int:
    if (
        isinstance(bucket_seconds, bool)
        or not isinstance(
            bucket_seconds,
            int,
        )
    ):
        raise TypeError(
            "bucket_seconds debe ser un enteiro"
        )

    if bucket_seconds <= 0:
        raise ValueError(
            "bucket_seconds debe ser positivo"
        )

    return (
        bucket_seconds
        * 1_000_000
    )


def _bucket_start(
    timestamp_us: int,
    bucket_us: int,
) -> int:
    return (
        timestamp_us
        // bucket_us
        * bucket_us
    )


def experiment_time_buckets(
    connection: sqlite3.Connection,
    channel: str,
    *,
    start_us: int | None = None,
    end_us: int | None = None,
    bucket_seconds: int = (
        EXPERIMENT_BUCKET_SECONDS
    ),
) -> tuple[ExperimentTimeBucket, ...]:
    """Agrupa observacións experimentais en intervalos temporais.

    Só se devolven intervalos que conteñen datos. A ausencia dun
    bucket non debe interpretarse automaticamente como perda radio:
    simplemente significa que non hai observacións almacenadas nese
    intervalo.
    """

    if channel not in {
        "LongFast",
        "NarrowFast",
    }:
        raise ValueError(
            "channel debe ser LongFast ou NarrowFast"
        )

    start_us, end_us = (
        _validated_range(
            start_us,
            end_us,
        )
    )

    bucket_us = _bucket_size_us(
        bucket_seconds
    )

    rows = _rows_for_channel(
        connection,
        channel,
        start_us=start_us,
        end_us=end_us,
    )

    grouped: dict[
        int,
        list[sqlite3.Row],
    ] = {}

    for row in rows:
        timestamp = int(
            row["imported_at_us"]
        )

        bucket_start_us = (
            _bucket_start(
                timestamp,
                bucket_us,
            )
        )

        grouped.setdefault(
            bucket_start_us,
            [],
        ).append(
            row
        )

    result: list[
        ExperimentTimeBucket
    ] = []

    for bucket_start_us in sorted(
        grouped
    ):
        bucket_rows = grouped[
            bucket_start_us
        ]

        nodes: set[str] = set()

        snrs: list[float] = []
        rssis: list[float] = []

        gateways: list[float] = []

        utilization: list[float] = []
        air_tx: list[float] = []

        packets_with_rf = 0
        rf_samples = 0

        multi_gateway = 0
        multi_stage = 0

        route_discovery = 0
        telemetry_samples = 0

        for row in bucket_rows:
            nodes.add(
                row["from_id"]
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

            if gateway_count > 1:
                multi_gateway += 1

            if stage_count > 1:
                multi_stage += 1

            if int(
                row["route_discovery"]
            ):
                route_discovery += 1

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

            channel_value = (
                _finite_number(
                    row[
                        "channel_utilization"
                    ]
                )
            )

            air_value = (
                _finite_number(
                    row["air_util_tx"]
                )
            )

            if (
                channel_value is not None
                or air_value is not None
            ):
                telemetry_samples += 1

            if channel_value is not None:
                utilization.append(
                    channel_value
                )

            if air_value is not None:
                air_tx.append(
                    air_value
                )

        result.append(
            ExperimentTimeBucket(
                channel=channel,
                start_us=bucket_start_us,
                end_us=(
                    bucket_start_us
                    + bucket_us
                ),
                packets=len(
                    bucket_rows
                ),
                nodes=len(nodes),
                packets_with_rf=(
                    packets_with_rf
                ),
                rf_samples=rf_samples,
                packets_multi_gateway=(
                    multi_gateway
                ),
                packets_multi_stage=(
                    multi_stage
                ),
                route_discovery_packets=(
                    route_discovery
                ),
                telemetry_samples=(
                    telemetry_samples
                ),
                snr_mean=_mean(snrs),
                snr_median=_median(snrs),
                rssi_mean=_mean(rssis),
                rssi_median=_median(
                    rssis
                ),
                gateway_mean=_mean(
                    gateways
                ),
                channel_utilization_mean=(
                    _mean(utilization)
                ),
                air_util_tx_mean=(
                    _mean(air_tx)
                ),
            )
        )

    return tuple(result)
