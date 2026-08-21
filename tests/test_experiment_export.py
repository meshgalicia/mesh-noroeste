"""Probas dos exportadores CSV e XLSX experimentais."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from mesh_noroeste.experiment_export import (
    EXPERIMENT_CSV_FILENAME,
    EXPERIMENT_TERRITORIES_CSV_FILENAME,
    EXPERIMENT_XLSX_FILENAME,
    SERIES_COLUMNS,
    TERRITORY_COLUMNS,
    write_experiment_csv,
    write_experiment_territories_csv,
    write_experiment_xlsx,
)


def document() -> dict:
    bucket = {
        "channel": "LongFast",
        "start_at": (
            "2026-08-19T12:00:00Z"
        ),
        "end_at": (
            "2026-08-19T12:15:00Z"
        ),
        "start_us": 1787140800000000,
        "end_us": 1787141700000000,
        "packets": 10,
        "nodes": 4,
        "packets_with_rf": 9,
        "rf_samples": 17,
        "packets_multi_gateway": 3,
        "packets_multi_stage": 2,
        "route_discovery_packets": 1,
        "telemetry_samples": 2,
        "snr_mean": 4.25,
        "snr_median": 5.0,
        "rssi_mean": -91.5,
        "rssi_median": -90.0,
        "gateway_mean": 1.4,
        "channel_utilization_mean": 8.5,
        "air_util_tx_mean": 2.25,
    }

    def summary(
        channel: str,
        *,
        packets: int,
        nodes: int,
    ) -> dict:
        return {
            "channel": channel,
            "packets": packets,
            "nodes": nodes,
            "oldest_us": 1787140800000000,
            "newest_us": 1787141700000000,
            "oldest_at": (
                "2026-08-19T12:00:00Z"
            ),
            "newest_at": (
                "2026-08-19T12:15:00Z"
            ),
            "packets_with_rf": packets,
            "rf_samples": packets * 2,
            "packets_multi_gateway": 2,
            "packets_multi_stage": 1,
            "route_discovery_packets": 1,
            "telemetry_samples": 2,
            "snr": {
                "mean": 4.25,
                "median": 5.0,
                "p10": -2.0,
                "p90": 7.0,
            },
            "rssi": {
                "mean": -91.5,
                "median": -90.0,
                "p10": -115.0,
                "p90": -70.0,
            },
            "gateways": {
                "mean": 1.4,
                "median": 1.0,
            },
            "stages": {
                "mean": 1.2,
                "median": 1.0,
            },
            "channel_utilization": {
                "samples": 2,
                "mean": 8.5,
                "median": 8.5,
                "p10": 7.0,
                "p90": 10.0,
            },
            "air_util_tx": {
                "samples": 2,
                "mean": 2.25,
                "median": 2.25,
                "p10": 1.5,
                "p90": 3.0,
            },
        }

    narrow_bucket = dict(bucket)
    narrow_bucket.update({
        "channel": "NarrowFast",
        "start_us": 1787141700000000,
        "end_us": 1787142600000000,
        "start_at": (
            "2026-08-19T12:15:00Z"
        ),
        "end_at": (
            "2026-08-19T12:30:00Z"
        ),
        "packets": 3,
        "nodes": 1,
        "rf_samples": 0,
        "snr_mean": None,
        "snr_median": None,
        "rssi_mean": None,
        "rssi_median": None,
        "channel_utilization_mean": None,
        "air_util_tx_mean": None,
    })

    return {
        "schema": (
            "mesh-noroeste."
            "meshtastic-experiment/v1"
        ),
        "generated_at": (
            "2026-08-19T12:30:00Z"
        ),
        "window": {
            "start_us": None,
            "end_us": None,
            "start_at": None,
            "end_at": None,
        },
        "bucket_seconds": 900,
        "channels": {
            "LongFast": summary(
                "LongFast",
                packets=10,
                nodes=4,
            ),
            "NarrowFast": summary(
                "NarrowFast",
                packets=3,
                nodes=1,
            ),
        },
        "comparison_window": {
            "available": True,
            "reason": None,
            "missing_channels": [],
            "start_us": 1787140800000000,
            "end_us": 1787141700000000,
            "start_at": (
                "2026-08-19T12:00:00Z"
            ),
            "end_at": (
                "2026-08-19T12:15:00Z"
            ),
            "duration_seconds": 900.0,
            "channels": {
                "LongFast": summary(
                    "LongFast",
                    packets=8,
                    nodes=4,
                ),
                "NarrowFast": summary(
                    "NarrowFast",
                    packets=2,
                    nodes=1,
                ),
            },
        },
        "series": {
            "LongFast": [
                bucket,
            ],
            "NarrowFast": [
                narrow_bucket,
            ],
        },
        "methodology": {
            "rf_zero_zero_missing": True,
            (
                "delivery_rate_requires_"
                "controlled_test"
            ): True,
            (
                "collisions_are_not_"
                "directly_observed"
            ): True,
            (
                "ingestion_delay_is_not_"
                "radio_latency"
            ): True,
        },
    }


def territorial_document() -> dict:
    source = document()

    long_metrics = dict(
        source["channels"]["LongFast"]
    )

    narrow_metrics = dict(
        source["channels"]["NarrowFast"]
    )

    source["territories"] = {
        "LongFast": {
            "provinces": [
                {
                    "name": "Pontevedra",
                    "metrics": long_metrics,
                }
            ],
            "municipalities": [
                {
                    "id": "es-ga-36008",
                    "name": "Cangas de Morrazo",
                    "province": "Pontevedra",
                    "country": "ES",
                    "classification": {
                        "exact_nodes": 3,
                        "compatible_nodes": 1,
                    },
                    "metrics": long_metrics,
                }
            ],
        },
        "NarrowFast": {
            "provinces": [
                {
                    "name": "Pontevedra",
                    "metrics": narrow_metrics,
                }
            ],
            "municipalities": [
                {
                    "id": "es-ga-36008",
                    "name": "Cangas de Morrazo",
                    "province": "Pontevedra",
                    "country": "ES",
                    "classification": {
                        "exact_nodes": 1,
                        "compatible_nodes": 0,
                    },
                    "metrics": narrow_metrics,
                }
            ],
        },
    }

    return source


class ExperimentExportTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.temporary = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temporary.cleanup
        )

        self.root = Path(
            self.temporary.name
        )


    def test_csv_contains_both_presets(
        self,
    ) -> None:
        path = (
            write_experiment_csv(
                document(),
                self.root
                / EXPERIMENT_CSV_FILENAME,
            )
        )

        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            rows = list(
                csv.reader(handle)
            )

        self.assertEqual(
            len(rows),
            3,
        )

        self.assertEqual(
            rows[0],
            [
                "Preset",
                "Inicio UTC",
                "Fin UTC",
                "Inicio Unix µs",
                "Fin Unix µs",
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
            ],
        )

        self.assertEqual(
            rows[1][0],
            "LongFast",
        )

        self.assertEqual(
            rows[2][0],
            "NarrowFast",
        )


    def test_territory_csv_contains_both_levels(
        self,
    ) -> None:
        path = (
            write_experiment_territories_csv(
                territorial_document(),
                self.root
                / EXPERIMENT_TERRITORIES_CSV_FILENAME,
            )
        )

        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            rows = list(
                csv.DictReader(handle)
            )

        self.assertEqual(
            len(rows),
            4,
        )

        self.assertEqual(
            set(rows[0]),
            {
                (
                    "Preset"
                    if key == "channel"
                    else {
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
                    }[key]
                )
                for key in TERRITORY_COLUMNS
            },
        )

        cangas = next(
            row
            for row in rows
            if (
                row["Nivel"] == "municipality"
                and row["Preset"] == "LongFast"
            )
        )

        self.assertEqual(
            cangas["Territorio"],
            "Cangas de Morrazo",
        )

        self.assertEqual(
            cangas["Provincia"],
            "Pontevedra",
        )

        self.assertEqual(
            cangas["Emisores exactos"],
            "3",
        )

        self.assertEqual(
            cangas["ChUtil media"],
            "8.5",
        )


    def test_xlsx_is_valid_zip_with_expected_sheets(
        self,
    ) -> None:
        path = (
            write_experiment_xlsx(
                territorial_document(),
                self.root
                / EXPERIMENT_XLSX_FILENAME,
            )
        )

        self.assertTrue(
            zipfile.is_zipfile(path)
        )

        with zipfile.ZipFile(
            path
        ) as archive:
            workbook_xml = (
                archive.read(
                    "xl/workbook.xml"
                ).decode(
                    "utf-8"
                )
            )

        for sheet_name in (
            "Resumo",
            "Comparación",
            "LongFast",
            "NarrowFast",
            "Provincias",
            "Concellos",
            "Metodoloxía",
        ):
            self.assertIn(
                sheet_name,
                workbook_xml,
            )


    def test_exports_do_not_modify_source_document(
        self,
    ) -> None:
        source = document()

        before = json.dumps(
            source,
            ensure_ascii=False,
            sort_keys=True,
        )

        write_experiment_csv(
            source,
            self.root
            / EXPERIMENT_CSV_FILENAME,
        )

        write_experiment_xlsx(
            source,
            self.root
            / EXPERIMENT_XLSX_FILENAME,
        )

        write_experiment_territories_csv(
            source,
            self.root
            / EXPERIMENT_TERRITORIES_CSV_FILENAME,
        )

        after = json.dumps(
            source,
            ensure_ascii=False,
            sort_keys=True,
        )

        self.assertEqual(
            before,
            after,
        )


if __name__ == "__main__":
    unittest.main()
