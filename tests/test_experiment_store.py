"""Probas da persistencia experimental LongFast/NarrowFast."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
import unittest

from mesh_noroeste.experiment_store import (
    connect_experiment_store,
    observation_from_event,
    store_live_document,
)


def event(
    *,
    event_id: str = (
        "meshtastic:live_packet:"
        "123:!a5b7f496"
    ),
    packet_id: int = 123,
    channel: str = "LongFast",
    portnum: int = 67,
) -> dict:
    return {
        "id": event_id,
        "network": "meshtastic",
        "source": "ozulo_map",
        "packet_id": packet_id,
        "from_id": (
            "meshtastic:!a5b7f496"
        ),
        "to_id": (
            "meshtastic:!ffffffff"
        ),
        "portnum": portnum,
        "channel": channel,
        "imported_at_us": (
            1787136568438957
        ),
        "long_name": "Nodo proba",
        "to_long_name": None,
        "evidence": [
            "gateway_observation",
        ],
        "observed": {
            "gateway_count": 2,
            "stage_count": 1,
            "stages": [
                {
                    "hop_limit": 2,
                    "hop_start": 3,
                    "hops_used": 1,
                    "gateways": [
                        {
                            "gateway_id": (
                                "meshtastic:"
                                "!11111111"
                            ),
                            "rx_time": (
                                1787136528
                            ),
                            "snr_db": 6.25,
                            "rssi_dbm": -91.0,
                            "imported_at_us": (
                                1787136568439000
                            ),
                        },
                        {
                            "gateway_id": (
                                "meshtastic:"
                                "!22222222"
                            ),
                            "rx_time": (
                                1787136529
                            ),
                            "snr_db": 0.0,
                            "rssi_dbm": 0.0,
                            "imported_at_us": (
                                1787136569439000
                            ),
                        },
                    ],
                },
            ],
        },
        "telemetry": {
            "time": 1787136500,
            "device_metrics": {
                "battery_level": 88,
                "voltage": 4.039,
                "channel_utilization": (
                    13.341667
                ),
                "air_util_tx": (
                    2.1988335
                ),
                "uptime_seconds": (
                    1726483
                ),
            },
            "environment_metrics": None,
            "power_metrics": None,
        },
        "traceroute": None,
    }


class ExperimentObservationTests(
    unittest.TestCase
):
    def test_event_is_normalized(
        self,
    ) -> None:
        result = observation_from_event(
            event()
        )

        self.assertIsNotNone(result)

        assert result is not None

        self.assertEqual(
            result.channel,
            "LongFast",
        )
        self.assertEqual(
            result.snr_values,
            (6.25,),
        )
        self.assertEqual(
            result.rssi_values,
            (-91.0,),
        )
        self.assertEqual(
            result.channel_utilization,
            13.341667,
        )
        self.assertEqual(
            result.air_util_tx,
            2.1988335,
        )


    def test_zero_zero_radio_pair_is_missing(
        self,
    ) -> None:
        source = event()

        source["observed"]["stages"][0][
            "gateways"
        ] = [
            {
                "gateway_id": (
                    "meshtastic:!11111111"
                ),
                "rx_time": 1,
                "snr_db": 0.0,
                "rssi_dbm": 0.0,
                "imported_at_us": 2,
            },
        ]

        result = observation_from_event(
            source
        )

        assert result is not None

        self.assertEqual(
            result.snr_values,
            (),
        )
        self.assertEqual(
            result.rssi_values,
            (),
        )


    def test_other_channel_is_ignored(
        self,
    ) -> None:
        self.assertIsNone(
            observation_from_event(
                event(
                    channel="MediumFast"
                )
            )
        )


    def test_route_discovery_is_marked(
        self,
    ) -> None:
        result = observation_from_event(
            event(
                portnum=70
            )
        )

        assert result is not None

        self.assertTrue(
            result.route_discovery
        )


class ExperimentStoreTests(
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


    def tearDown(self) -> None:
        self.connection.close()
        self.temporary.cleanup()


    def count_rows(self) -> int:
        row = self.connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM experiment_observations
            """
        ).fetchone()

        assert row is not None

        return int(row["total"])


    def test_live_document_is_stored(
        self,
    ) -> None:
        inserted = store_live_document(
            self.connection,
            {
                "events": [
                    event(),
                    event(
                        event_id=(
                            "meshtastic:"
                            "live_packet:"
                            "124:!a5b7f496"
                        ),
                        packet_id=124,
                        channel=(
                            "NarrowFast"
                        ),
                    ),
                ],
            },
        )

        self.assertEqual(
            inserted,
            2,
        )
        self.assertEqual(
            self.count_rows(),
            2,
        )


    def test_existing_event_is_enriched(
        self,
    ) -> None:
        original = event()

        original["observed"] = {
            "gateway_count": 1,
            "stage_count": 1,
            "stages": [
                {
                    "hop_limit": 2,
                    "hop_start": 3,
                    "hops_used": 1,
                    "gateways": [
                        {
                            "gateway_id": (
                                "meshtastic:"
                                "!11111111"
                            ),
                            "rx_time": 1,
                            "snr_db": 2.5,
                            "rssi_dbm": -105.0,
                            "imported_at_us": 2,
                        },
                    ],
                },
            ],
        }

        original["telemetry"] = None

        first = store_live_document(
            self.connection,
            {
                "events": [
                    original,
                ],
            },
        )

        enriched = event()

        enriched["observed"] = {
            "gateway_count": 2,
            "stage_count": 2,
            "stages": [
                {
                    "hop_limit": 2,
                    "hop_start": 3,
                    "hops_used": 1,
                    "gateways": [
                        {
                            "gateway_id": (
                                "meshtastic:"
                                "!11111111"
                            ),
                            "rx_time": 1,
                            "snr_db": 2.5,
                            "rssi_dbm": -105.0,
                            "imported_at_us": 2,
                        },
                    ],
                },
                {
                    "hop_limit": 1,
                    "hop_start": 3,
                    "hops_used": 2,
                    "gateways": [
                        {
                            "gateway_id": (
                                "meshtastic:"
                                "!22222222"
                            ),
                            "rx_time": 3,
                            "snr_db": 6.0,
                            "rssi_dbm": -91.0,
                            "imported_at_us": 4,
                        },
                    ],
                },
            ],
        }

        second = store_live_document(
            self.connection,
            {
                "events": [
                    enriched,
                ],
            },
        )

        self.assertEqual(first, 1)
        self.assertEqual(second, 0)
        self.assertEqual(
            self.count_rows(),
            1,
        )

        row = self.connection.execute(
            """
            SELECT
                gateway_count,
                stage_count,
                snr_values_json,
                rssi_values_json,
                channel_utilization,
                air_util_tx
            FROM experiment_observations
            WHERE event_id = ?
            """,
            (
                enriched["id"],
            ),
        ).fetchone()

        assert row is not None

        self.assertEqual(
            row["gateway_count"],
            2,
        )
        self.assertEqual(
            row["stage_count"],
            2,
        )
        self.assertEqual(
            row["snr_values_json"],
            "[2.5, 6.0]",
        )
        self.assertEqual(
            row["rssi_values_json"],
            "[-105.0, -91.0]",
        )
        self.assertEqual(
            row["channel_utilization"],
            13.341667,
        )
        self.assertEqual(
            row["air_util_tx"],
            2.1988335,
        )


    def test_store_is_idempotent(
        self,
    ) -> None:
        document = {
            "events": [
                event(),
            ],
        }

        first = store_live_document(
            self.connection,
            document,
        )

        second = store_live_document(
            self.connection,
            document,
        )

        self.assertEqual(first, 1)
        self.assertEqual(second, 0)
        self.assertEqual(
            self.count_rows(),
            1,
        )


    def test_channels_remain_separate(
        self,
    ) -> None:
        store_live_document(
            self.connection,
            {
                "events": [
                    event(),
                    event(
                        event_id=(
                            "meshtastic:"
                            "live_packet:"
                            "999:!bbbbbbbb"
                        ),
                        packet_id=999,
                        channel=(
                            "NarrowFast"
                        ),
                    ),
                ],
            },
        )

        rows = self.connection.execute(
            """
            SELECT
                channel,
                COUNT(*) AS total
            FROM experiment_observations
            GROUP BY channel
            ORDER BY channel
            """
        ).fetchall()

        result = {
            row["channel"]: row["total"]
            for row in rows
        }

        self.assertEqual(
            result,
            {
                "LongFast": 1,
                "NarrowFast": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
