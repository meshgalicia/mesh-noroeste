"""Probas do informe experimental Meshtastic."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from mesh_noroeste.experiment_report import (
    EXPERIMENT_REPORT_SCHEMA,
    build_experiment_report,
    build_experiment_territories,
    channel_summary,
    write_experiment_report,
)
from mesh_noroeste.experiment_store import (
    connect_experiment_store,
)


class ExperimentReportTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.temporary = (
            tempfile.TemporaryDirectory()
        )

        self.root = Path(
            self.temporary.name
        )

        self.database = (
            self.root
            / "experiment.db"
        )

        self.connection = (
            connect_experiment_store(
                self.database
            )
        )


    def tearDown(self) -> None:
        self.connection.close()
        self.temporary.cleanup()


    def insert(
        self,
        *,
        event_id: str,
        channel: str,
        imported_at_us: int,
        from_id: str,
        gateway_count: int,
        stage_count: int,
        snrs: list[float],
        rssis: list[float],
        route_discovery: int = 0,
        utilization: float | None = None,
        air_tx: float | None = None,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO experiment_observations (
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
            )
            VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
            """,
            (
                event_id,
                len(event_id),
                from_id,
                channel,
                (
                    70
                    if route_discovery
                    else 3
                ),
                imported_at_us,
                gateway_count,
                stage_count,
                json.dumps(
                    snrs
                ),
                json.dumps(
                    rssis
                ),
                route_discovery,
                None,
                utilization,
                air_tx,
                None,
                None,
                None,
            ),
        )

        self.connection.commit()


    def test_builds_two_channel_report(
        self,
    ) -> None:
        self.insert(
            event_id="lf-1",
            channel="LongFast",
            imported_at_us=100,
            from_id=(
                "meshtastic:"
                "!00000001"
            ),
            gateway_count=2,
            stage_count=2,
            snrs=[2.0, 6.0],
            rssis=[-100.0, -80.0],
            utilization=10.0,
            air_tx=2.0,
        )

        self.insert(
            event_id="nf-1",
            channel="NarrowFast",
            imported_at_us=200,
            from_id=(
                "meshtastic:"
                "!00000002"
            ),
            gateway_count=1,
            stage_count=1,
            snrs=[],
            rssis=[],
            route_discovery=1,
        )

        report = (
            build_experiment_report(
                self.connection,
                generated_at=(
                    "2026-08-19T12:00:00Z"
                ),
            )
        )

        self.assertEqual(
            report["schema"],
            EXPERIMENT_REPORT_SCHEMA,
        )

        self.assertEqual(
            set(
                report["channels"]
            ),
            {
                "LongFast",
                "NarrowFast",
            },
        )

        longfast = (
            report["channels"][
                "LongFast"
            ]
        )

        self.assertEqual(
            longfast["packets"],
            1,
        )

        self.assertEqual(
            longfast["nodes"],
            1,
        )

        self.assertEqual(
            longfast[
                "packets_multi_gateway"
            ],
            1,
        )

        self.assertEqual(
            longfast["snr"]["mean"],
            4.0,
        )

        self.assertEqual(
            longfast["rssi"]["mean"],
            -90.0,
        )

        self.assertEqual(
            longfast[
                "channel_utilization"
            ]["mean"],
            10.0,
        )

        narrowfast = (
            report["channels"][
                "NarrowFast"
            ]
        )

        self.assertEqual(
            narrowfast["packets"],
            1,
        )

        self.assertEqual(
            narrowfast[
                "route_discovery_packets"
            ],
            1,
        )

        self.assertIsNone(
            narrowfast["snr"]["mean"]
        )


    def test_series_are_included(
        self,
    ) -> None:
        self.insert(
            event_id="lf-1",
            channel="LongFast",
            imported_at_us=100,
            from_id=(
                "meshtastic:"
                "!00000001"
            ),
            gateway_count=1,
            stage_count=1,
            snrs=[5.0],
            rssis=[-90.0],
        )

        report = (
            build_experiment_report(
                self.connection,
                generated_at=(
                    "2026-08-19T12:00:00Z"
                ),
                bucket_seconds=900,
            )
        )

        series = (
            report["series"][
                "LongFast"
            ]
        )

        self.assertEqual(
            len(series),
            1,
        )

        self.assertEqual(
            series[0]["packets"],
            1,
        )

        self.assertIn(
            "start_at",
            series[0],
        )

        self.assertIn(
            "end_at",
            series[0],
        )


    def test_empty_channel_is_explicit(
        self,
    ) -> None:
        report = (
            build_experiment_report(
                self.connection,
                generated_at=(
                    "2026-08-19T12:00:00Z"
                ),
            )
        )

        narrowfast = (
            report["channels"][
                "NarrowFast"
            ]
        )

        self.assertEqual(
            narrowfast["packets"],
            0,
        )

        self.assertEqual(
            narrowfast["nodes"],
            0,
        )

        self.assertIsNone(
            narrowfast["snr"]["mean"]
        )

        self.assertEqual(
            report["series"][
                "NarrowFast"
            ],
            [],
        )


    def test_methodology_is_explicit(
        self,
    ) -> None:
        report = (
            build_experiment_report(
                self.connection,
                generated_at=(
                    "2026-08-19T12:00:00Z"
                ),
            )
        )

        methodology = (
            report["methodology"]
        )

        self.assertTrue(
            methodology[
                "rf_zero_zero_missing"
            ]
        )

        self.assertTrue(
            methodology[
                "delivery_rate_requires_controlled_test"
            ]
        )

        self.assertTrue(
            methodology[
                "collisions_are_not_directly_observed"
            ]
        )

        self.assertTrue(
            methodology[
                "ingestion_delay_is_not_radio_latency"
            ]
        )


    def test_evidence_contract_is_explicit(
        self,
    ) -> None:
        report = (
            build_experiment_report(
                self.connection,
                generated_at=(
                    "2026-08-19T12:00:00Z"
                ),
            )
        )

        evidence = report[
            "evidence"
        ]

        self.assertEqual(
            set(evidence),
            {
                "observational",
                "controlled",
            },
        )

        observational = evidence[
            "observational"
        ]

        self.assertTrue(
            observational[
                "available"
            ]
        )

        self.assertEqual(
            observational[
                "source"
            ],
            "passive_observation",
        )

        controlled = evidence[
            "controlled"
        ]

        self.assertFalse(
            controlled[
                "available"
            ]
        )

        self.assertEqual(
            controlled[
                "tests"
            ],
            [],
        )

        self.assertIsNone(
            controlled[
                "methodology"
            ]
        )


    def test_methodology_marks_observational_limit(
        self,
    ) -> None:
        report = (
            build_experiment_report(
                self.connection,
                generated_at=(
                    "2026-08-19T12:00:00Z"
                ),
            )
        )

        methodology = (
            report["methodology"]
        )

        self.assertTrue(
            methodology[
                "observational_data_does_not_"
                "isolate_preset_effect"
            ]
        )


    def test_range_filters_report(
        self,
    ) -> None:
        self.insert(
            event_id="old",
            channel="LongFast",
            imported_at_us=100,
            from_id=(
                "meshtastic:"
                "!00000001"
            ),
            gateway_count=1,
            stage_count=1,
            snrs=[1.0],
            rssis=[-100.0],
        )

        self.insert(
            event_id="new",
            channel="LongFast",
            imported_at_us=500,
            from_id=(
                "meshtastic:"
                "!00000002"
            ),
            gateway_count=1,
            stage_count=1,
            snrs=[5.0],
            rssis=[-80.0],
        )

        report = (
            build_experiment_report(
                self.connection,
                generated_at=(
                    "2026-08-19T12:00:00Z"
                ),
                start_us=400,
                end_us=600,
            )
        )

        summary = (
            report["channels"][
                "LongFast"
            ]
        )

        self.assertEqual(
            summary["packets"],
            1,
        )

        self.assertEqual(
            summary["snr"]["mean"],
            5.0,
        )


    def test_invalid_range_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "end_us debe ser maior",
        ):
            build_experiment_report(
                self.connection,
                start_us=500,
                end_us=100,
            )


    def test_comparison_window_uses_temporal_overlap(
        self,
    ) -> None:
        observations = [
            (
                "lf-before",
                "LongFast",
                100,
                "!00000001",
            ),
            (
                "lf-start",
                "LongFast",
                300,
                "!00000001",
            ),
            (
                "lf-end",
                "LongFast",
                400,
                "!00000002",
            ),
            (
                "lf-after",
                "LongFast",
                500,
                "!00000003",
            ),
            (
                "nf-start",
                "NarrowFast",
                300,
                "!00000011",
            ),
            (
                "nf-end",
                "NarrowFast",
                400,
                "!00000012",
            ),
        ]

        for (
            event_id,
            channel,
            timestamp,
            source_id,
        ) in observations:
            self.insert(
                event_id=event_id,
                channel=channel,
                imported_at_us=timestamp,
                from_id=(
                    "meshtastic:"
                    + source_id
                ),
                gateway_count=1,
                stage_count=1,
                snrs=[5.0],
                rssis=[-90.0],
            )

        report = (
            build_experiment_report(
                self.connection,
                generated_at=(
                    "2026-08-19T12:00:00Z"
                ),
            )
        )

        comparison = (
            report[
                "comparison_window"
            ]
        )

        self.assertTrue(
            comparison["available"]
        )

        self.assertIsNone(
            comparison["reason"]
        )

        self.assertEqual(
            comparison["start_us"],
            300,
        )

        # O extremo é exclusivo e debe incluír
        # a observación situada exactamente en 400.
        self.assertEqual(
            comparison["end_us"],
            401,
        )

        self.assertEqual(
            comparison[
                "channels"
            ][
                "LongFast"
            ][
                "packets"
            ],
            2,
        )

        self.assertEqual(
            comparison[
                "channels"
            ][
                "NarrowFast"
            ][
                "packets"
            ],
            2,
        )


    def test_comparison_window_requires_both_channels(
        self,
    ) -> None:
        self.insert(
            event_id="lf-only",
            channel="LongFast",
            imported_at_us=100,
            from_id=(
                "meshtastic:"
                "!00000001"
            ),
            gateway_count=1,
            stage_count=1,
            snrs=[5.0],
            rssis=[-90.0],
        )

        report = (
            build_experiment_report(
                self.connection,
                generated_at=(
                    "2026-08-19T12:00:00Z"
                ),
            )
        )

        comparison = (
            report[
                "comparison_window"
            ]
        )

        self.assertFalse(
            comparison["available"]
        )

        self.assertEqual(
            comparison["reason"],
            "missing_channel_data",
        )

        self.assertEqual(
            comparison[
                "missing_channels"
            ],
            [
                "NarrowFast",
            ],
        )

        self.assertEqual(
            comparison["channels"],
            {},
        )


    def test_comparison_window_detects_no_overlap(
        self,
    ) -> None:
        self.insert(
            event_id="lf",
            channel="LongFast",
            imported_at_us=100,
            from_id=(
                "meshtastic:"
                "!00000001"
            ),
            gateway_count=1,
            stage_count=1,
            snrs=[5.0],
            rssis=[-90.0],
        )

        self.insert(
            event_id="nf",
            channel="NarrowFast",
            imported_at_us=300,
            from_id=(
                "meshtastic:"
                "!00000002"
            ),
            gateway_count=1,
            stage_count=1,
            snrs=[5.0],
            rssis=[-90.0],
        )

        report = (
            build_experiment_report(
                self.connection,
                generated_at=(
                    "2026-08-19T12:00:00Z"
                ),
            )
        )

        comparison = (
            report[
                "comparison_window"
            ]
        )

        self.assertFalse(
            comparison["available"]
        )

        self.assertEqual(
            comparison["reason"],
            "no_temporal_overlap",
        )

        self.assertEqual(
            comparison["channels"],
            {},
        )


    def test_comparison_window_respects_report_range(
        self,
    ) -> None:
        for event_id, channel, timestamp in [
            ("lf-old", "LongFast", 100),
            ("lf-a", "LongFast", 500),
            ("lf-b", "LongFast", 700),
            ("nf-old", "NarrowFast", 200),
            ("nf-a", "NarrowFast", 600),
            ("nf-b", "NarrowFast", 800),
        ]:
            self.insert(
                event_id=event_id,
                channel=channel,
                imported_at_us=timestamp,
                from_id=(
                    "meshtastic:"
                    "!00000001"
                ),
                gateway_count=1,
                stage_count=1,
                snrs=[5.0],
                rssis=[-90.0],
            )

        report = (
            build_experiment_report(
                self.connection,
                generated_at=(
                    "2026-08-19T12:00:00Z"
                ),
                start_us=400,
                end_us=750,
            )
        )

        comparison = (
            report[
                "comparison_window"
            ]
        )

        self.assertTrue(
            comparison["available"]
        )

        self.assertEqual(
            comparison["start_us"],
            600,
        )

        self.assertEqual(
            comparison["end_us"],
            601,
        )


    def test_report_can_be_written(
        self,
    ) -> None:
        self.connection.close()

        output = (
            self.root
            / "report.json"
        )

        path = (
            write_experiment_report(
                self.database,
                output,
                generated_at=(
                    "2026-08-19T12:00:00Z"
                ),
            )
        )

        self.connection = (
            connect_experiment_store(
                self.database
            )
        )

        self.assertEqual(
            path,
            output.resolve(),
        )

        document = json.loads(
            output.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            document["schema"],
            EXPERIMENT_REPORT_SCHEMA,
        )

        self.assertEqual(
            document[
                "bucket_seconds"
            ],
            900,
        )


if __name__ == "__main__":
    unittest.main()


class ExperimentTerritoryReportTests(unittest.TestCase):
    def _territory_index(self):
        from mesh_noroeste.territory import (
            TerritoryIndex,
        )

        return TerritoryIndex.from_geojson(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "id": "es-ga-a",
                            "name": "Concello A",
                            "level": "municipality",
                            "country": "ES",
                            "parent": "A Coruña",
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [-9.0, 42.0],
                                [-8.0, 42.0],
                                [-8.0, 43.0],
                                [-9.0, 43.0],
                                [-9.0, 42.0],
                            ]],
                        },
                    },
                    {
                        "type": "Feature",
                        "properties": {
                            "id": "es-ga-b",
                            "name": "Concello B",
                            "level": "municipality",
                            "country": "ES",
                            "parent": "Pontevedra",
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [-8.0, 42.0],
                                [-7.0, 42.0],
                                [-7.0, 43.0],
                                [-8.0, 43.0],
                                [-8.0, 42.0],
                            ]],
                        },
                    },
                ],
            }
        )

    def _nodes_document(self):
        return {
            "nodes": [
                {
                    "id": "meshtastic:!00000001",
                    "latitude": 42.5,
                    "longitude": -8.5,
                    "position_precision_bits": 32,
                    "long_name": "Nodo A",
                    "short_name": "A",
                },
                {
                    "id": "meshtastic:!00000002",
                    "latitude": 42.5,
                    "longitude": -7.5,
                    "position_precision_bits": 32,
                    "long_name": "Nodo B",
                    "short_name": "B",
                },
                {
                    "id": "meshtastic:!00000003",
                    "latitude": 43.01,
                    "longitude": -8.0,
                    "position_precision_bits": 13,
                    "long_name": "Nodo ambiguo",
                    "short_name": "AMB",
                },
            ],
        }

    def test_channel_summary_can_filter_emitters(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row

        connection.execute(
            """
            CREATE TABLE experiment_observations (
                event_id TEXT PRIMARY KEY,
                packet_id INTEGER NOT NULL,
                from_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                portnum INTEGER NOT NULL,
                imported_at_us INTEGER NOT NULL,
                gateway_count INTEGER NOT NULL,
                stage_count INTEGER NOT NULL,
                snr_values_json TEXT NOT NULL,
                rssi_values_json TEXT NOT NULL,
                route_discovery INTEGER NOT NULL,
                telemetry_time INTEGER,
                channel_utilization REAL,
                air_util_tx REAL,
                battery_level REAL,
                voltage REAL,
                uptime_seconds REAL
            )
            """
        )

        rows = [
            (
                "a1",
                1,
                "meshtastic:!00000001",
                "LongFast",
                1,
                100,
                1,
                1,
                "[]",
                "[]",
                0,
                None,
                None,
                None,
                None,
                None,
                None,
            ),
            (
                "a2",
                2,
                "meshtastic:!00000002",
                "LongFast",
                1,
                200,
                1,
                1,
                "[]",
                "[]",
                0,
                None,
                None,
                None,
                None,
                None,
                None,
            ),
        ]

        connection.executemany(
            """
            INSERT INTO experiment_observations
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
            """,
            rows,
        )

        summary = channel_summary(
            connection,
            "LongFast",
            from_ids={
                "meshtastic:!00000001",
            },
        )

        self.assertEqual(
            summary["packets"],
            1,
        )
        self.assertEqual(
            summary["nodes"],
            1,
        )

        connection.close()

    def test_territorial_report_partitions_packets(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row

        connection.execute(
            """
            CREATE TABLE experiment_observations (
                event_id TEXT PRIMARY KEY,
                packet_id INTEGER NOT NULL,
                from_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                portnum INTEGER NOT NULL,
                imported_at_us INTEGER NOT NULL,
                gateway_count INTEGER NOT NULL,
                stage_count INTEGER NOT NULL,
                snr_values_json TEXT NOT NULL,
                rssi_values_json TEXT NOT NULL,
                route_discovery INTEGER NOT NULL,
                telemetry_time INTEGER,
                channel_utilization REAL,
                air_util_tx REAL,
                battery_level REAL,
                voltage REAL,
                uptime_seconds REAL
            )
            """
        )

        rows = [
            (
                "a1", 1,
                "meshtastic:!00000001",
                "LongFast",
                1, 100, 1, 1,
                "[]", "[]", 0,
                None, None, None,
                None, None, None,
            ),
            (
                "a2", 2,
                "meshtastic:!00000002",
                "LongFast",
                1, 200, 1, 1,
                "[]", "[]", 0,
                None, None, None,
                None, None, None,
            ),
            (
                "a3", 3,
                "meshtastic:!00000003",
                "LongFast",
                1, 300, 1, 1,
                "[]", "[]", 0,
                None, None, None,
                None, None, None,
            ),
            (
                "a4", 4,
                "meshtastic:!ffffffff",
                "LongFast",
                1, 400, 1, 1,
                "[]", "[]", 0,
                None, None, None,
                None, None, None,
            ),
        ]

        connection.executemany(
            """
            INSERT INTO experiment_observations
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
            """,
            rows,
        )

        territories = build_experiment_territories(
            connection,
            nodes_document=self._nodes_document(),
            territory_index=self._territory_index(),
        )

        report = territories[
            "LongFast"
        ]

        total = report[
            "summary"
        ]["packets"]

        assigned = report[
            "summary"
        ]["assigned_packets"]

        ambiguous = report[
            "ambiguous"
        ]["metrics"]["packets"]

        outside = report[
            "outside"
        ]["metrics"]["packets"]

        self.assertEqual(
            total,
            assigned
            + ambiguous
            + outside,
        )

        self.assertEqual(
            total,
            4,
        )

        self.assertEqual(
            report["summary"][
                "assigned_emitters"
            ],
            2,
        )

        self.assertEqual(
            report["summary"][
                "ambiguous_emitters"
            ],
            1,
        )

        self.assertEqual(
            report["summary"][
                "unlocated_emitters"
            ],
            1,
        )

        connection.close()

    def test_build_report_omits_territories_without_inputs(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row

        connection.execute(
            """
            CREATE TABLE experiment_observations (
                event_id TEXT PRIMARY KEY,
                packet_id INTEGER NOT NULL,
                from_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                portnum INTEGER NOT NULL,
                imported_at_us INTEGER NOT NULL,
                gateway_count INTEGER NOT NULL,
                stage_count INTEGER NOT NULL,
                snr_values_json TEXT NOT NULL,
                rssi_values_json TEXT NOT NULL,
                route_discovery INTEGER NOT NULL,
                telemetry_time INTEGER,
                channel_utilization REAL,
                air_util_tx REAL,
                battery_level REAL,
                voltage REAL,
                uptime_seconds REAL
            )
            """
        )

        document = build_experiment_report(
            connection,
            generated_at=(
                "2026-08-20T00:00:00Z"
            ),
        )

        self.assertNotIn(
            "territories",
            document,
        )

        connection.close()
