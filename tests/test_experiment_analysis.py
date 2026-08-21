"""Probas da análise agregada LongFast/NarrowFast."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
import unittest

from mesh_noroeste.experiment_analysis import (
    analyze_experiment,
    summarize_channel,
)
from mesh_noroeste.experiment_store import (
    connect_experiment_store,
)


class ExperimentAnalysisTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.temporary = (
            tempfile.TemporaryDirectory()
        )

        self.database = (
            Path(self.temporary.name)
            / "experiment.db"
        )

        self.connection = (
            connect_experiment_store(
                self.database
            )
        )

        self._insert(
            event_id="lf-1",
            packet_id=1,
            from_id="meshtastic:!00000001",
            channel="LongFast",
            imported_at_us=100,
            gateway_count=1,
            stage_count=1,
            snrs=[2.0],
            rssis=[-100.0],
            route_discovery=0,
            channel_utilization=10.0,
            air_util_tx=1.0,
        )

        self._insert(
            event_id="lf-2",
            packet_id=2,
            from_id="meshtastic:!00000002",
            channel="LongFast",
            imported_at_us=200,
            gateway_count=3,
            stage_count=2,
            snrs=[4.0, 6.0],
            rssis=[-90.0, -80.0],
            route_discovery=1,
            channel_utilization=20.0,
            air_util_tx=3.0,
        )

        self._insert(
            event_id="nf-1",
            packet_id=3,
            from_id="meshtastic:!00000003",
            channel="NarrowFast",
            imported_at_us=300,
            gateway_count=1,
            stage_count=1,
            snrs=[],
            rssis=[],
            route_discovery=1,
            channel_utilization=None,
            air_util_tx=None,
        )

        self.connection.commit()


    def tearDown(self) -> None:
        self.connection.close()
        self.temporary.cleanup()


    def _insert(
        self,
        *,
        event_id: str,
        packet_id: int,
        from_id: str,
        channel: str,
        imported_at_us: int,
        gateway_count: int,
        stage_count: int,
        snrs: list[float],
        rssis: list[float],
        route_discovery: int,
        channel_utilization: float | None,
        air_util_tx: float | None,
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
                packet_id,
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
                json.dumps(snrs),
                json.dumps(rssis),
                route_discovery,
                None,
                channel_utilization,
                air_util_tx,
                None,
                None,
                None,
            ),
        )


    def test_longfast_summary(
        self,
    ) -> None:
        result = summarize_channel(
            self.connection,
            "LongFast",
        )

        self.assertEqual(
            result.packets,
            2,
        )

        self.assertEqual(
            result.nodes,
            2,
        )

        self.assertEqual(
            result.packets_with_rf,
            2,
        )

        self.assertEqual(
            result.rf_samples,
            3,
        )

        self.assertEqual(
            result.packets_multi_gateway,
            1,
        )

        self.assertEqual(
            result.packets_multi_stage,
            1,
        )

        self.assertEqual(
            result.route_discovery_packets,
            1,
        )

        self.assertEqual(
            result.telemetry_samples,
            2,
        )

        self.assertEqual(
            result.oldest_us,
            100,
        )

        self.assertEqual(
            result.newest_us,
            200,
        )

        self.assertEqual(
            result.snr_mean,
            4.0,
        )

        self.assertEqual(
            result.snr_median,
            4.0,
        )

        self.assertEqual(
            result.rssi_mean,
            -90.0,
        )

        self.assertEqual(
            result.gateway_mean,
            2.0,
        )

        self.assertEqual(
            result.gateway_median,
            2.0,
        )

        self.assertEqual(
            result.stage_mean,
            1.5,
        )

        self.assertEqual(
            result.channel_utilization_mean,
            15.0,
        )

        self.assertEqual(
            result.air_util_tx_mean,
            2.0,
        )


    def test_narrowfast_without_rf_is_explicit(
        self,
    ) -> None:
        result = summarize_channel(
            self.connection,
            "NarrowFast",
        )

        self.assertEqual(
            result.packets,
            1,
        )

        self.assertEqual(
            result.packets_with_rf,
            0,
        )

        self.assertEqual(
            result.rf_samples,
            0,
        )

        self.assertIsNone(
            result.snr_mean
        )

        self.assertIsNone(
            result.rssi_mean
        )

        self.assertIsNone(
            result.channel_utilization_mean
        )


    def test_time_window_is_applied(
        self,
    ) -> None:
        result = summarize_channel(
            self.connection,
            "LongFast",
            start_us=150,
            end_us=250,
        )

        self.assertEqual(
            result.packets,
            1,
        )

        self.assertEqual(
            result.nodes,
            1,
        )

        self.assertEqual(
            result.oldest_us,
            200,
        )

        self.assertEqual(
            result.newest_us,
            200,
        )


    def test_full_analysis_contains_both_presets(
        self,
    ) -> None:
        result = analyze_experiment(
            self.connection
        )

        self.assertEqual(
            set(result.by_channel),
            {
                "LongFast",
                "NarrowFast",
            },
        )

        self.assertEqual(
            result.by_channel[
                "LongFast"
            ].packets,
            2,
        )

        self.assertEqual(
            result.by_channel[
                "NarrowFast"
            ].packets,
            1,
        )


    def test_empty_window_returns_empty_summary(
        self,
    ) -> None:
        result = summarize_channel(
            self.connection,
            "LongFast",
            start_us=1000,
            end_us=2000,
        )

        self.assertEqual(
            result.packets,
            0,
        )

        self.assertEqual(
            result.nodes,
            0,
        )

        self.assertIsNone(
            result.oldest_us
        )

        self.assertIsNone(
            result.snr_mean
        )


    def test_invalid_channel_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "LongFast ou NarrowFast",
        ):
            summarize_channel(
                self.connection,
                "MediumFast",
            )


    def test_invalid_range_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "end_us debe ser maior",
        ):
            analyze_experiment(
                self.connection,
                start_us=500,
                end_us=100,
            )


if __name__ == "__main__":
    unittest.main()


class ExperimentTimeBucketTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.temporary = (
            tempfile.TemporaryDirectory()
        )

        self.database = (
            Path(self.temporary.name)
            / "experiment.db"
        )

        self.connection = (
            connect_experiment_store(
                self.database
            )
        )

        self.bucket_us = (
            15 * 60 * 1_000_000
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
        gateway_count: int = 1,
        stage_count: int = 1,
        snrs: list[float] | None = None,
        rssis: list[float] | None = None,
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
                (
                    "meshtastic:"
                    "!00000001"
                ),
                channel,
                3,
                imported_at_us,
                gateway_count,
                stage_count,
                json.dumps(
                    snrs or []
                ),
                json.dumps(
                    rssis or []
                ),
                0,
                None,
                utilization,
                air_tx,
                None,
                None,
                None,
            ),
        )

        self.connection.commit()


    def test_groups_same_interval(
        self,
    ) -> None:
        from mesh_noroeste.experiment_analysis import (
            experiment_time_buckets,
        )

        self.insert(
            event_id="a",
            channel="LongFast",
            imported_at_us=(
                self.bucket_us + 100
            ),
            gateway_count=1,
            snrs=[2.0],
            rssis=[-100.0],
        )

        self.insert(
            event_id="b",
            channel="LongFast",
            imported_at_us=(
                self.bucket_us + 200
            ),
            gateway_count=3,
            stage_count=2,
            snrs=[6.0],
            rssis=[-80.0],
        )

        result = (
            experiment_time_buckets(
                self.connection,
                "LongFast",
            )
        )

        self.assertEqual(
            len(result),
            1,
        )

        bucket = result[0]

        self.assertEqual(
            bucket.start_us,
            self.bucket_us,
        )

        self.assertEqual(
            bucket.end_us,
            self.bucket_us * 2,
        )

        self.assertEqual(
            bucket.packets,
            2,
        )

        self.assertEqual(
            bucket.packets_multi_gateway,
            1,
        )

        self.assertEqual(
            bucket.snr_mean,
            4.0,
        )

        self.assertEqual(
            bucket.rssi_mean,
            -90.0,
        )

        self.assertEqual(
            bucket.gateway_mean,
            2.0,
        )


    def test_separates_intervals(
        self,
    ) -> None:
        from mesh_noroeste.experiment_analysis import (
            experiment_time_buckets,
        )

        self.insert(
            event_id="a",
            channel="LongFast",
            imported_at_us=100,
        )

        self.insert(
            event_id="b",
            channel="LongFast",
            imported_at_us=(
                self.bucket_us + 100
            ),
        )

        result = (
            experiment_time_buckets(
                self.connection,
                "LongFast",
            )
        )

        self.assertEqual(
            len(result),
            2,
        )

        self.assertEqual(
            result[0].start_us,
            0,
        )

        self.assertEqual(
            result[1].start_us,
            self.bucket_us,
        )


    def test_presets_remain_separate(
        self,
    ) -> None:
        from mesh_noroeste.experiment_analysis import (
            experiment_time_buckets,
        )

        self.insert(
            event_id="lf",
            channel="LongFast",
            imported_at_us=100,
        )

        self.insert(
            event_id="nf",
            channel="NarrowFast",
            imported_at_us=200,
        )

        longfast = (
            experiment_time_buckets(
                self.connection,
                "LongFast",
            )
        )

        narrowfast = (
            experiment_time_buckets(
                self.connection,
                "NarrowFast",
            )
        )

        self.assertEqual(
            longfast[0].packets,
            1,
        )

        self.assertEqual(
            narrowfast[0].packets,
            1,
        )


    def test_telemetry_is_aggregated(
        self,
    ) -> None:
        from mesh_noroeste.experiment_analysis import (
            experiment_time_buckets,
        )

        self.insert(
            event_id="a",
            channel="LongFast",
            imported_at_us=100,
            utilization=10.0,
            air_tx=2.0,
        )

        self.insert(
            event_id="b",
            channel="LongFast",
            imported_at_us=200,
            utilization=20.0,
            air_tx=4.0,
        )

        bucket = (
            experiment_time_buckets(
                self.connection,
                "LongFast",
            )[0]
        )

        self.assertEqual(
            bucket.telemetry_samples,
            2,
        )

        self.assertEqual(
            bucket.channel_utilization_mean,
            15.0,
        )

        self.assertEqual(
            bucket.air_util_tx_mean,
            3.0,
        )


    def test_empty_period_has_no_fake_buckets(
        self,
    ) -> None:
        from mesh_noroeste.experiment_analysis import (
            experiment_time_buckets,
        )

        self.insert(
            event_id="a",
            channel="LongFast",
            imported_at_us=100,
        )

        result = (
            experiment_time_buckets(
                self.connection,
                "LongFast",
                start_us=(
                    self.bucket_us * 10
                ),
                end_us=(
                    self.bucket_us * 11
                ),
            )
        )

        self.assertEqual(
            result,
            (),
        )


    def test_custom_bucket_size(
        self,
    ) -> None:
        from mesh_noroeste.experiment_analysis import (
            experiment_time_buckets,
        )

        self.insert(
            event_id="a",
            channel="LongFast",
            imported_at_us=100,
        )

        self.insert(
            event_id="b",
            channel="LongFast",
            imported_at_us=(
                20 * 60 * 1_000_000
            ),
        )

        result = (
            experiment_time_buckets(
                self.connection,
                "LongFast",
                bucket_seconds=60 * 60,
            )
        )

        self.assertEqual(
            len(result),
            1,
        )

        self.assertEqual(
            result[0].packets,
            2,
        )


if __name__ == "__main__":
    unittest.main()
