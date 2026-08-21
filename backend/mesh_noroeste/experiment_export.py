"""Exportación tabular dos experimentos Meshtastic."""

from __future__ import annotations

import csv
from datetime import datetime
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

import xlsxwriter


EXPERIMENT_CSV_FILENAME = (
    "experiment.csv"
)

EXPERIMENT_XLSX_FILENAME = (
    "experiment.xlsx"
)


EXPERIMENT_TERRITORIES_CSV_FILENAME = (
    "experiment-territories.csv"
)


TERRITORY_COLUMNS = (
    "channel",
    "level",
    "id",
    "name",
    "province",
    "country",
    "packets",
    "nodes",
    "exact_nodes",
    "compatible_nodes",
    "packets_with_rf",
    "rf_samples",
    "packets_multi_gateway",
    "packets_multi_stage",
    "route_discovery_packets",
    "telemetry_samples",
    "snr_mean",
    "snr_median",
    "snr_p10",
    "snr_p90",
    "rssi_mean",
    "rssi_median",
    "rssi_p10",
    "rssi_p90",
    "gateway_mean",
    "gateway_median",
    "stage_mean",
    "stage_median",
    "channel_utilization_samples",
    "channel_utilization_mean",
    "channel_utilization_median",
    "channel_utilization_p10",
    "channel_utilization_p90",
    "air_util_tx_samples",
    "air_util_tx_mean",
    "air_util_tx_median",
    "air_util_tx_p10",
    "air_util_tx_p90",
    "oldest_at",
    "newest_at",
)


TERRITORY_HEADERS = {
    "channel": "Preset",
    "level": "Nivel",
    "id": "ID territorio",
    "name": "Territorio",
    "province": "Provincia",
    "country": "País",
    "packets": "Paquetes",
    "nodes": "Emisores",
    "exact_nodes": "Emisores exactos",
    "compatible_nodes": "Emisores compatibles",
    "packets_with_rf": "Paquetes con RF",
    "rf_samples": "Mostras RF",
    "packets_multi_gateway": "Paquetes >1 gateway",
    "packets_multi_stage": "Paquetes >1 etapa",
    "route_discovery_packets": "RouteDiscovery",
    "telemetry_samples": "Mostras telemetría",
    "snr_mean": "SNR media",
    "snr_median": "SNR mediana",
    "snr_p10": "SNR p10",
    "snr_p90": "SNR p90",
    "rssi_mean": "RSSI media",
    "rssi_median": "RSSI mediana",
    "rssi_p10": "RSSI p10",
    "rssi_p90": "RSSI p90",
    "gateway_mean": "Gateways media",
    "gateway_median": "Gateways mediana",
    "stage_mean": "Etapas media",
    "stage_median": "Etapas mediana",
    "channel_utilization_samples": "ChUtil mostras",
    "channel_utilization_mean": "ChUtil media",
    "channel_utilization_median": "ChUtil mediana",
    "channel_utilization_p10": "ChUtil p10",
    "channel_utilization_p90": "ChUtil p90",
    "air_util_tx_samples": "Air Util TX mostras",
    "air_util_tx_mean": "Air Util TX media",
    "air_util_tx_median": "Air Util TX mediana",
    "air_util_tx_p10": "Air Util TX p10",
    "air_util_tx_p90": "Air Util TX p90",
    "oldest_at": "Primeira observación",
    "newest_at": "Última observación",
}


SERIES_COLUMNS = (
    "channel",
    "start_at",
    "end_at",
    "start_us",
    "end_us",
    "packets",
    "nodes",
    "packets_with_rf",
    "rf_samples",
    "packets_multi_gateway",
    "packets_multi_stage",
    "route_discovery_packets",
    "telemetry_samples",
    "snr_mean",
    "snr_median",
    "rssi_mean",
    "rssi_median",
    "gateway_mean",
    "channel_utilization_mean",
    "air_util_tx_mean",
)


SERIES_HEADERS = {
    "channel": "Preset",
    "start_at": "Inicio UTC",
    "end_at": "Fin UTC",
    "start_us": "Inicio Unix µs",
    "end_us": "Fin Unix µs",
    "packets": "Paquetes",
    "nodes": "Nodos",
    "packets_with_rf": "Paquetes con RF",
    "rf_samples": "Mostras RF",
    "packets_multi_gateway": (
        "Paquetes >1 gateway"
    ),
    "packets_multi_stage": (
        "Paquetes >1 etapa"
    ),
    "route_discovery_packets": (
        "RouteDiscovery"
    ),
    "telemetry_samples": (
        "Mostras telemetría"
    ),
    "snr_mean": "SNR media",
    "snr_median": "SNR mediana",
    "rssi_mean": "RSSI media",
    "rssi_median": "RSSI mediana",
    "gateway_mean": "Gateways media",
    "channel_utilization_mean": (
        "Channel utilization media"
    ),
    "air_util_tx_mean": (
        "Air util TX media"
    ),
}


def _series_rows(
    document: Mapping[str, Any],
) -> list[dict[str, Any]]:
    series = document.get("series")

    if not isinstance(series, Mapping):
        raise ValueError(
            "document.series debe ser un mapping"
        )

    rows: list[dict[str, Any]] = []

    for channel in (
        "LongFast",
        "NarrowFast",
    ):
        channel_rows = series.get(
            channel,
            [],
        )

        if not isinstance(
            channel_rows,
            list,
        ):
            raise ValueError(
                f"series.{channel} debe ser unha lista"
            )

        for item in channel_rows:
            if not isinstance(
                item,
                Mapping,
            ):
                continue

            row = {
                key: item.get(key)
                for key in SERIES_COLUMNS
            }

            row["channel"] = channel

            rows.append(row)

    rows.sort(
        key=lambda row: (
            row.get("start_us")
            if isinstance(
                row.get("start_us"),
                int,
            )
            else -1,
            str(
                row.get("channel")
                or ""
            ),
        )
    )

    return rows


def _territory_metric(
    metrics: Mapping[str, Any],
    group: str,
    field: str,
) -> Any:
    value = metrics.get(group)

    if not isinstance(value, Mapping):
        return None

    return value.get(field)


def _territory_row(
    channel: str,
    level: str,
    territory: Mapping[str, Any],
) -> dict[str, Any]:
    metrics = territory.get("metrics")

    if not isinstance(metrics, Mapping):
        metrics = {}

    classification = territory.get(
        "classification"
    )

    if not isinstance(
        classification,
        Mapping,
    ):
        classification = {}

    return {
        "channel": channel,
        "level": level,
        "id": territory.get("id"),
        "name": (
            territory.get("name")
            or territory.get("province")
        ),
        "province": (
            territory.get("province")
            if level == "municipality"
            else territory.get("name")
        ),
        "country": territory.get("country"),
        "packets": metrics.get("packets"),
        "nodes": metrics.get("nodes"),
        "exact_nodes": classification.get(
            "exact_nodes"
        ),
        "compatible_nodes": classification.get(
            "compatible_nodes"
        ),
        "packets_with_rf": metrics.get(
            "packets_with_rf"
        ),
        "rf_samples": metrics.get(
            "rf_samples"
        ),
        "packets_multi_gateway": metrics.get(
            "packets_multi_gateway"
        ),
        "packets_multi_stage": metrics.get(
            "packets_multi_stage"
        ),
        "route_discovery_packets": metrics.get(
            "route_discovery_packets"
        ),
        "telemetry_samples": metrics.get(
            "telemetry_samples"
        ),
        "snr_mean": _territory_metric(
            metrics,
            "snr",
            "mean",
        ),
        "snr_median": _territory_metric(
            metrics,
            "snr",
            "median",
        ),
        "snr_p10": _territory_metric(
            metrics,
            "snr",
            "p10",
        ),
        "snr_p90": _territory_metric(
            metrics,
            "snr",
            "p90",
        ),
        "rssi_mean": _territory_metric(
            metrics,
            "rssi",
            "mean",
        ),
        "rssi_median": _territory_metric(
            metrics,
            "rssi",
            "median",
        ),
        "rssi_p10": _territory_metric(
            metrics,
            "rssi",
            "p10",
        ),
        "rssi_p90": _territory_metric(
            metrics,
            "rssi",
            "p90",
        ),
        "gateway_mean": _territory_metric(
            metrics,
            "gateways",
            "mean",
        ),
        "gateway_median": _territory_metric(
            metrics,
            "gateways",
            "median",
        ),
        "stage_mean": _territory_metric(
            metrics,
            "stages",
            "mean",
        ),
        "stage_median": _territory_metric(
            metrics,
            "stages",
            "median",
        ),
        "channel_utilization_samples": (
            _territory_metric(
                metrics,
                "channel_utilization",
                "samples",
            )
        ),
        "channel_utilization_mean": (
            _territory_metric(
                metrics,
                "channel_utilization",
                "mean",
            )
        ),
        "channel_utilization_median": (
            _territory_metric(
                metrics,
                "channel_utilization",
                "median",
            )
        ),
        "channel_utilization_p10": (
            _territory_metric(
                metrics,
                "channel_utilization",
                "p10",
            )
        ),
        "channel_utilization_p90": (
            _territory_metric(
                metrics,
                "channel_utilization",
                "p90",
            )
        ),
        "air_util_tx_samples": (
            _territory_metric(
                metrics,
                "air_util_tx",
                "samples",
            )
        ),
        "air_util_tx_mean": _territory_metric(
            metrics,
            "air_util_tx",
            "mean",
        ),
        "air_util_tx_median": _territory_metric(
            metrics,
            "air_util_tx",
            "median",
        ),
        "air_util_tx_p10": _territory_metric(
            metrics,
            "air_util_tx",
            "p10",
        ),
        "air_util_tx_p90": _territory_metric(
            metrics,
            "air_util_tx",
            "p90",
        ),
        "oldest_at": metrics.get(
            "oldest_at"
        ),
        "newest_at": metrics.get(
            "newest_at"
        ),
    }


def _territory_rows(
    document: Mapping[str, Any],
    *,
    level: str | None = None,
) -> list[dict[str, Any]]:
    territories = document.get(
        "territories"
    )

    if territories is None:
        return []

    if not isinstance(
        territories,
        Mapping,
    ):
        raise ValueError(
            "document.territories debe ser un mapping"
        )

    rows: list[dict[str, Any]] = []

    for channel in (
        "LongFast",
        "NarrowFast",
    ):
        channel_data = territories.get(
            channel
        )

        if not isinstance(
            channel_data,
            Mapping,
        ):
            continue

        if level in (
            None,
            "province",
        ):
            provinces = channel_data.get(
                "provinces",
                [],
            )

            if not isinstance(
                provinces,
                list,
            ):
                raise ValueError(
                    f"territories.{channel}.provinces "
                    "debe ser unha lista"
                )

            for province in provinces:
                if not isinstance(
                    province,
                    Mapping,
                ):
                    continue

                rows.append(
                    _territory_row(
                        channel,
                        "province",
                        province,
                    )
                )

        if level in (
            None,
            "municipality",
        ):
            municipalities = channel_data.get(
                "municipalities",
                [],
            )

            if not isinstance(
                municipalities,
                list,
            ):
                raise ValueError(
                    f"territories.{channel}.municipalities "
                    "debe ser unha lista"
                )

            for municipality in municipalities:
                if not isinstance(
                    municipality,
                    Mapping,
                ):
                    continue

                rows.append(
                    _territory_row(
                        channel,
                        "municipality",
                        municipality,
                    )
                )

    rows.sort(
        key=lambda row: (
            0
            if row["channel"] == "LongFast"
            else 1,
            str(row.get("province") or ""),
            str(row.get("name") or ""),
        )
    )

    return rows


def _temporary_path(
    target: Path,
) -> Path:
    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, name = (
        tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
        )
    )

    os.fchmod(
        descriptor,
        0o644,
    )

    os.close(descriptor)

    return Path(name)


def write_experiment_csv(
    document: Mapping[str, Any],
    path: Path | str,
) -> Path:
    """Escribe unha táboa temporal longa en CSV UTF-8."""

    if not isinstance(document, Mapping):
        raise TypeError(
            "document debe ser un mapping"
        )

    target = Path(
        path
    ).expanduser().resolve()

    temporary = _temporary_path(
        target
    )

    try:
        with temporary.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=SERIES_COLUMNS,
                extrasaction="ignore",
            )

            writer.writerow(
                SERIES_HEADERS
            )

            for row in _series_rows(
                document
            ):
                writer.writerow(row)

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary,
            target,
        )

    except BaseException:
        temporary.unlink(
            missing_ok=True
        )
        raise

    return target


def write_experiment_territories_csv(
    document: Mapping[str, Any],
    path: Path | str,
) -> Path:
    """Escribe as métricas territoriais nun CSV independente."""

    if not isinstance(document, Mapping):
        raise TypeError(
            "document debe ser un mapping"
        )

    target = Path(
        path
    ).expanduser().resolve()

    temporary = _temporary_path(
        target
    )

    try:
        with temporary.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=TERRITORY_COLUMNS,
                extrasaction="ignore",
            )

            writer.writerow(
                TERRITORY_HEADERS
            )

            for row in _territory_rows(
                document
            ):
                writer.writerow(row)

            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary,
            target,
        )

    except BaseException:
        temporary.unlink(
            missing_ok=True
        )
        raise

    return target


def _excel_datetime(
    value: Any,
) -> datetime | None:
    if not isinstance(value, str):
        return None

    normalized = value.strip()

    if not normalized:
        return None

    try:
        return datetime.fromisoformat(
            normalized.replace(
                "Z",
                "+00:00",
            )
        ).replace(
            tzinfo=None
        )
    except ValueError:
        return None


def _metric_value(
    summary: Mapping[str, Any],
    group: str,
    field: str,
) -> Any:
    value = summary.get(group)

    if not isinstance(value, Mapping):
        return None

    return value.get(field)


def _summary_row(
    channel: str,
    summary: Mapping[str, Any],
) -> list[Any]:
    """Converte un resumo dun preset nunha fila tabular."""

    return [
        channel,
        summary.get("packets"),
        summary.get("nodes"),
        summary.get(
            "packets_with_rf"
        ),
        summary.get(
            "rf_samples"
        ),
        summary.get(
            "packets_multi_gateway"
        ),
        summary.get(
            "packets_multi_stage"
        ),
        summary.get(
            "route_discovery_packets"
        ),
        summary.get(
            "telemetry_samples"
        ),
        _metric_value(
            summary,
            "snr",
            "mean",
        ),
        _metric_value(
            summary,
            "snr",
            "median",
        ),
        _metric_value(
            summary,
            "rssi",
            "mean",
        ),
        _metric_value(
            summary,
            "rssi",
            "median",
        ),
        _metric_value(
            summary,
            "gateways",
            "mean",
        ),
        _metric_value(
            summary,
            "channel_utilization",
            "mean",
        ),
        _metric_value(
            summary,
            "air_util_tx",
            "mean",
        ),
        summary.get(
            "oldest_at"
        ),
        summary.get(
            "newest_at"
        ),
    ]


def _comparison_window(
    document: Mapping[str, Any],
) -> Mapping[str, Any]:
    comparison = document.get(
        "comparison_window"
    )

    if not isinstance(
        comparison,
        Mapping,
    ):
        raise ValueError(
            "document.comparison_window "
            "debe ser un mapping"
        )

    return comparison


def _comparison_rows(
    document: Mapping[str, Any],
) -> list[list[Any]]:
    comparison = _comparison_window(
        document
    )

    channels = comparison.get(
        "channels"
    )

    if not isinstance(
        channels,
        Mapping,
    ):
        return []

    rows: list[list[Any]] = []

    for channel in (
        "LongFast",
        "NarrowFast",
    ):
        summary = channels.get(
            channel
        )

        if not isinstance(
            summary,
            Mapping,
        ):
            continue

        rows.append(
            _summary_row(
                channel,
                summary,
            )
        )

    return rows


def _summary_rows(
    document: Mapping[str, Any],
) -> list[list[Any]]:
    channels = document.get(
        "channels"
    )

    if not isinstance(
        channels,
        Mapping,
    ):
        raise ValueError(
            "document.channels debe ser un mapping"
        )

    rows: list[list[Any]] = []

    for channel in (
        "LongFast",
        "NarrowFast",
    ):
        summary = channels.get(
            channel
        )

        if not isinstance(
            summary,
            Mapping,
        ):
            raise ValueError(
                f"Falta channels.{channel}"
            )

        rows.append(
            _summary_row(
                channel,
                summary,
            )
        )

    return rows


def write_experiment_xlsx(
    document: Mapping[str, Any],
    path: Path | str,
) -> Path:
    """Xera un libro XLSX listo para análise humana."""

    if not isinstance(document, Mapping):
        raise TypeError(
            "document debe ser un mapping"
        )

    target = Path(
        path
    ).expanduser().resolve()

    temporary = _temporary_path(
        target
    )

    workbook = None

    try:
        workbook = (
            xlsxwriter.Workbook(
                temporary,
                {
                    "constant_memory": True,
                },
            )
        )

        title_format = (
            workbook.add_format({
                "bold": True,
                "font_size": 16,
            })
        )

        header_format = (
            workbook.add_format({
                "bold": True,
                "border": 1,
                "text_wrap": True,
                "valign": "vcenter",
            })
        )

        integer_format = (
            workbook.add_format({
                "num_format": "0",
            })
        )

        decimal_format = (
            workbook.add_format({
                "num_format": "0.00",
            })
        )

        timestamp_format = (
            workbook.add_format({
                "num_format": (
                    "yyyy-mm-dd hh:mm:ss"
                ),
            })
        )

        note_format = (
            workbook.add_format({
                "text_wrap": True,
                "valign": "top",
            })
        )

        # --------------------------------------------------
        # Resumo
        # --------------------------------------------------

        summary_sheet = (
            workbook.add_worksheet(
                "Resumo"
            )
        )

        summary_sheet.freeze_panes(
            3,
            1,
        )

        summary_sheet.write(
            0,
            0,
            (
                "Experimento Meshtastic "
                "LongFast / NarrowFast"
            ),
            title_format,
        )

        summary_sheet.write(
            1,
            0,
            "Xerado",
            header_format,
        )

        generated = _excel_datetime(
            document.get(
                "generated_at"
            )
        )

        if generated is not None:
            summary_sheet.write_datetime(
                1,
                1,
                generated,
                timestamp_format,
            )
        else:
            summary_sheet.write(
                1,
                1,
                document.get(
                    "generated_at"
                ),
            )

        summary_headers = [
            "Preset",
            "Paquetes",
            "Nodos",
            "Paquetes con RF",
            "Mostras RF",
            "Paquetes >1 gateway",
            "Paquetes >1 etapa",
            "RouteDiscovery",
            "Mostras telemetría",
            "SNR media",
            "SNR mediana",
            "RSSI media",
            "RSSI mediana",
            "Gateways media",
            "Channel utilization media",
            "Air util TX media",
            "Primeira observación",
            "Última observación",
        ]

        for column, header in enumerate(
            summary_headers
        ):
            summary_sheet.write(
                3,
                column,
                header,
                header_format,
            )

        for row_index, values in enumerate(
            _summary_rows(document),
            start=4,
        ):
            for column, value in enumerate(
                values
            ):
                if column in (
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    8,
                ):
                    summary_sheet.write(
                        row_index,
                        column,
                        value,
                        integer_format,
                    )

                elif column in (
                    9,
                    10,
                    11,
                    12,
                    13,
                    14,
                    15,
                ):
                    summary_sheet.write(
                        row_index,
                        column,
                        value,
                        decimal_format,
                    )

                elif column in (
                    16,
                    17,
                ):
                    parsed = (
                        _excel_datetime(
                            value
                        )
                    )

                    if parsed is None:
                        summary_sheet.write(
                            row_index,
                            column,
                            value,
                        )
                    else:
                        summary_sheet.write_datetime(
                            row_index,
                            column,
                            parsed,
                            timestamp_format,
                        )

                else:
                    summary_sheet.write(
                        row_index,
                        column,
                        value,
                    )

        summary_sheet.autofilter(
            3,
            0,
            5,
            len(
                summary_headers
            ) - 1,
        )

        summary_sheet.set_column(
            0,
            0,
            14,
        )

        summary_sheet.set_column(
            1,
            8,
            17,
        )

        summary_sheet.set_column(
            9,
            15,
            20,
        )

        summary_sheet.set_column(
            16,
            17,
            21,
        )

        # --------------------------------------------------
        # Comparación na xanela temporal común
        # --------------------------------------------------

        comparison = _comparison_window(
            document
        )

        comparison_sheet = (
            workbook.add_worksheet(
                "Comparación"
            )
        )

        comparison_sheet.write(
            0,
            0,
            (
                "Comparación LongFast / NarrowFast "
                "na xanela temporal común"
            ),
            title_format,
        )

        available = (
            comparison.get(
                "available"
            ) is True
        )

        comparison_sheet.write(
            2,
            0,
            "Dispoñible",
            header_format,
        )

        comparison_sheet.write(
            2,
            1,
            (
                "Si"
                if available
                else "Non"
            ),
        )

        comparison_sheet.write(
            3,
            0,
            "Inicio común",
            header_format,
        )

        comparison_start = (
            _excel_datetime(
                comparison.get(
                    "start_at"
                )
            )
        )

        if comparison_start is not None:
            comparison_sheet.write_datetime(
                3,
                1,
                comparison_start,
                timestamp_format,
            )
        else:
            comparison_sheet.write(
                3,
                1,
                comparison.get(
                    "start_at"
                ),
            )

        comparison_sheet.write(
            4,
            0,
            "Fin común exclusivo",
            header_format,
        )

        comparison_end = (
            _excel_datetime(
                comparison.get(
                    "end_at"
                )
            )
        )

        if comparison_end is not None:
            comparison_sheet.write_datetime(
                4,
                1,
                comparison_end,
                timestamp_format,
            )
        else:
            comparison_sheet.write(
                4,
                1,
                comparison.get(
                    "end_at"
                ),
            )

        comparison_sheet.write(
            5,
            0,
            "Duración",
            header_format,
        )

        duration_seconds = (
            comparison.get(
                "duration_seconds"
            )
        )

        if isinstance(
            duration_seconds,
            (int, float),
        ) and not isinstance(
            duration_seconds,
            bool,
        ):
            comparison_sheet.write(
                5,
                1,
                (
                    float(
                        duration_seconds
                    )
                    / 3600
                ),
                decimal_format,
            )

            comparison_sheet.write(
                5,
                2,
                "horas",
            )
        else:
            comparison_sheet.write(
                5,
                1,
                None,
            )

        comparison_sheet.write(
            6,
            0,
            "Convención temporal",
            header_format,
        )

        comparison_sheet.write(
            6,
            1,
            (
                "[inicio, fin): o inicio inclúese "
                "e o instante final exclúese."
            ),
            note_format,
        )

        reason = comparison.get(
            "reason"
        )

        if not available:
            comparison_sheet.write(
                7,
                0,
                "Motivo",
                header_format,
            )

            comparison_sheet.write(
                7,
                1,
                (
                    str(reason)
                    if reason is not None
                    else (
                        "Non existe unha xanela "
                        "temporal común utilizable."
                    )
                ),
                note_format,
            )

        comparison_headers = [
            "Preset",
            "Paquetes",
            "Nodos",
            "Paquetes con RF",
            "Mostras RF",
            "Paquetes >1 gateway",
            "Paquetes >1 etapa",
            "RouteDiscovery",
            "Mostras telemetría",
            "SNR media",
            "SNR mediana",
            "RSSI media",
            "RSSI mediana",
            "Gateways media",
            "Channel utilization media",
            "Air util TX media",
            "Primeira observación",
            "Última observación",
        ]

        comparison_header_row = 9

        for column, header in enumerate(
            comparison_headers
        ):
            comparison_sheet.write(
                comparison_header_row,
                column,
                header,
                header_format,
            )

        comparison_rows = (
            _comparison_rows(
                document
            )
        )

        for row_index, values in enumerate(
            comparison_rows,
            start=(
                comparison_header_row
                + 1
            ),
        ):
            for column, value in enumerate(
                values
            ):
                if column in (
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    8,
                ):
                    comparison_sheet.write(
                        row_index,
                        column,
                        value,
                        integer_format,
                    )

                elif column in (
                    9,
                    10,
                    11,
                    12,
                    13,
                    14,
                    15,
                ):
                    comparison_sheet.write(
                        row_index,
                        column,
                        value,
                        decimal_format,
                    )

                elif column in (
                    16,
                    17,
                ):
                    parsed = (
                        _excel_datetime(
                            value
                        )
                    )

                    if parsed is None:
                        comparison_sheet.write(
                            row_index,
                            column,
                            value,
                        )
                    else:
                        comparison_sheet.write_datetime(
                            row_index,
                            column,
                            parsed,
                            timestamp_format,
                        )

                else:
                    comparison_sheet.write(
                        row_index,
                        column,
                        value,
                    )

        if comparison_rows:
            comparison_sheet.autofilter(
                comparison_header_row,
                0,
                (
                    comparison_header_row
                    + len(
                        comparison_rows
                    )
                ),
                len(
                    comparison_headers
                ) - 1,
            )

        comparison_sheet.freeze_panes(
            comparison_header_row + 1,
            1,
        )

        comparison_sheet.set_column(
            0,
            0,
            22,
        )

        comparison_sheet.set_column(
            1,
            8,
            17,
        )

        comparison_sheet.set_column(
            9,
            15,
            20,
        )

        comparison_sheet.set_column(
            16,
            17,
            21,
        )

        # --------------------------------------------------
        # Series por preset
        # --------------------------------------------------

        series = document.get(
            "series"
        )

        if not isinstance(
            series,
            Mapping,
        ):
            raise ValueError(
                "document.series debe ser un mapping"
            )

        for channel in (
            "LongFast",
            "NarrowFast",
        ):
            sheet = (
                workbook.add_worksheet(
                    channel
                )
            )

            sheet.freeze_panes(
                1,
                3,
            )

            for column, key in enumerate(
                SERIES_COLUMNS
            ):
                sheet.write(
                    0,
                    column,
                    SERIES_HEADERS[key],
                    header_format,
                )

            rows = series.get(
                channel,
                [],
            )

            if not isinstance(
                rows,
                list,
            ):
                raise ValueError(
                    f"series.{channel} "
                    "debe ser unha lista"
                )

            for row_index, source in enumerate(
                rows,
                start=1,
            ):
                if not isinstance(
                    source,
                    Mapping,
                ):
                    continue

                for column, key in enumerate(
                    SERIES_COLUMNS
                ):
                    value = (
                        channel
                        if key == "channel"
                        else source.get(key)
                    )

                    if key in (
                        "start_at",
                        "end_at",
                    ):
                        parsed = (
                            _excel_datetime(
                                value
                            )
                        )

                        if parsed is None:
                            sheet.write(
                                row_index,
                                column,
                                value,
                            )
                        else:
                            sheet.write_datetime(
                                row_index,
                                column,
                                parsed,
                                timestamp_format,
                            )

                    elif key in (
                        "start_us",
                        "end_us",
                        "packets",
                        "nodes",
                        "packets_with_rf",
                        "rf_samples",
                        "packets_multi_gateway",
                        "packets_multi_stage",
                        "route_discovery_packets",
                        "telemetry_samples",
                    ):
                        sheet.write(
                            row_index,
                            column,
                            value,
                            integer_format,
                        )

                    elif key in (
                        "snr_mean",
                        "snr_median",
                        "rssi_mean",
                        "rssi_median",
                        "gateway_mean",
                        "channel_utilization_mean",
                        "air_util_tx_mean",
                    ):
                        sheet.write(
                            row_index,
                            column,
                            value,
                            decimal_format,
                        )

                    else:
                        sheet.write(
                            row_index,
                            column,
                            value,
                        )

            if rows:
                sheet.autofilter(
                    0,
                    0,
                    len(rows),
                    len(
                        SERIES_COLUMNS
                    ) - 1,
                )

            sheet.set_column(
                0,
                0,
                13,
            )

            sheet.set_column(
                1,
                2,
                20,
            )

            sheet.set_column(
                3,
                4,
                18,
            )

            sheet.set_column(
                5,
                12,
                18,
            )

            sheet.set_column(
                13,
                19,
                19,
            )

        # --------------------------------------------------
        # Territorios
        # --------------------------------------------------

        territory_integer_fields = {
            "packets",
            "nodes",
            "exact_nodes",
            "compatible_nodes",
            "packets_with_rf",
            "rf_samples",
            "packets_multi_gateway",
            "packets_multi_stage",
            "route_discovery_packets",
            "telemetry_samples",
            "channel_utilization_samples",
            "air_util_tx_samples",
        }

        territory_decimal_fields = {
            "snr_mean",
            "snr_median",
            "snr_p10",
            "snr_p90",
            "rssi_mean",
            "rssi_median",
            "rssi_p10",
            "rssi_p90",
            "gateway_mean",
            "gateway_median",
            "stage_mean",
            "stage_median",
            "channel_utilization_mean",
            "channel_utilization_median",
            "channel_utilization_p10",
            "channel_utilization_p90",
            "air_util_tx_mean",
            "air_util_tx_median",
            "air_util_tx_p10",
            "air_util_tx_p90",
        }

        territory_datetime_fields = {
            "oldest_at",
            "newest_at",
        }

        for (
            sheet_name,
            territory_level,
        ) in (
            (
                "Provincias",
                "province",
            ),
            (
                "Concellos",
                "municipality",
            ),
        ):
            sheet = workbook.add_worksheet(
                sheet_name
            )

            rows = _territory_rows(
                document,
                level=territory_level,
            )

            sheet.freeze_panes(
                1,
                6,
            )

            for column, key in enumerate(
                TERRITORY_COLUMNS
            ):
                sheet.write(
                    0,
                    column,
                    TERRITORY_HEADERS[key],
                    header_format,
                )

            for row_index, source in enumerate(
                rows,
                start=1,
            ):
                for column, key in enumerate(
                    TERRITORY_COLUMNS
                ):
                    value = source.get(key)

                    if key in territory_integer_fields:
                        sheet.write(
                            row_index,
                            column,
                            value,
                            integer_format,
                        )

                    elif key in territory_decimal_fields:
                        sheet.write(
                            row_index,
                            column,
                            value,
                            decimal_format,
                        )

                    elif key in territory_datetime_fields:
                        parsed = _excel_datetime(
                            value
                        )

                        if parsed is None:
                            sheet.write(
                                row_index,
                                column,
                                value,
                            )
                        else:
                            sheet.write_datetime(
                                row_index,
                                column,
                                parsed,
                                timestamp_format,
                            )

                    else:
                        sheet.write(
                            row_index,
                            column,
                            value,
                        )

            if rows:
                sheet.autofilter(
                    0,
                    0,
                    len(rows),
                    len(
                        TERRITORY_COLUMNS
                    ) - 1,
                )

            sheet.set_column(
                0,
                1,
                14,
            )

            sheet.set_column(
                2,
                2,
                19,
            )

            sheet.set_column(
                3,
                5,
                22,
            )

            sheet.set_column(
                6,
                15,
                18,
            )

            sheet.set_column(
                16,
                37,
                17,
            )

            sheet.set_column(
                38,
                39,
                21,
            )

        # --------------------------------------------------
        # Metodoloxía
        # --------------------------------------------------

        methodology_sheet = (
            workbook.add_worksheet(
                "Metodoloxía"
            )
        )

        methodology_sheet.write(
            0,
            0,
            "Metodoloxía",
            title_format,
        )

        methodology_sheet.write_row(
            2,
            0,
            [
                "Propiedade",
                "Valor",
                "Explicación",
            ],
            header_format,
        )

        methodology = (
            document.get(
                "methodology"
            )
        )

        if not isinstance(
            methodology,
            Mapping,
        ):
            methodology = {}

        explanations = {
            "rf_zero_zero_missing": (
                "Os pares RSSI/SNR 0/0 "
                "trátanse como medida ausente."
            ),
            (
                "delivery_rate_requires_"
                "controlled_test"
            ): (
                "A taxa de entrega require "
                "coñecer cantos paquetes se "
                "enviaron deliberadamente."
            ),
            (
                "collisions_are_not_"
                "directly_observed"
            ): (
                "As colisións radio non se "
                "observan directamente nesta "
                "fonte de datos."
            ),
            (
                "ingestion_delay_is_not_"
                "radio_latency"
            ): (
                "O retardo de importación non "
                "é latencia extremo a extremo "
                "da radio."
            ),
        }

        for row_index, (
            key,
            value,
        ) in enumerate(
            methodology.items(),
            start=3,
        ):
            methodology_sheet.write(
                row_index,
                0,
                key,
            )

            methodology_sheet.write(
                row_index,
                1,
                str(value),
            )

            methodology_sheet.write(
                row_index,
                2,
                explanations.get(
                    key,
                    "",
                ),
                note_format,
            )

        methodology_sheet.set_column(
            0,
            0,
            43,
        )

        methodology_sheet.set_column(
            1,
            1,
            12,
        )

        methodology_sheet.set_column(
            2,
            2,
            75,
        )

        workbook.close()
        workbook = None

        os.replace(
            temporary,
            target,
        )

    except BaseException:
        if workbook is not None:
            try:
                workbook.close()
            except Exception:
                pass

        temporary.unlink(
            missing_ok=True
        )

        raise

    return target
