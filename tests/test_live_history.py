"""Probas da persistencia independente do histórico live."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from mesh_noroeste.live_history import (
    LIVE_HISTORY_SCHEMA_VERSION,
    LiveHistoryStore,
)


def event(
    *,
    event_id: str,
    imported_at_us: int,
    traceroute: dict | None = None,
) -> dict:
    return {
        "id": event_id,
        "network": "meshtastic",
        "source": "ozulo_map",
        "packet_id": 123,
        "from_id": "meshtastic:!00000001",
        "to_id": "meshtastic:!ffffffff",
        "portnum": 70 if traceroute else 3,
        "channel": "LongFast",
        "imported_at_us": imported_at_us,
        "long_name": "Nodo",
        "to_long_name": None,
        "evidence": (
            ["gateway_observation", "traceroute"]
            if traceroute
            else ["gateway_observation"]
        ),
        "observed": {
            "gateway_count": 1,
            "stage_count": 1,
            "stages": [],
        },
        "traceroute": traceroute,
    }


class LiveHistoryStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)

        self.path = (
            Path(self.temporary.name)
            / "live-history.db"
        )

        self.store = LiveHistoryStore(
            self.path
        )


    def test_initializes_independent_database(
        self,
    ) -> None:
        self.store.initialize()

        self.assertTrue(
            self.path.exists()
        )

        import sqlite3

        connection = sqlite3.connect(
            self.path
        )

        try:
            version = connection.execute(
                """
                SELECT value
                FROM metadata
                WHERE key = 'schema_version'
                """
            ).fetchone()[0]

            self.assertEqual(
                version,
                str(
                    LIVE_HISTORY_SCHEMA_VERSION
                ),
            )

        finally:
            connection.close()


    def test_events_are_saved_idempotently(
        self,
    ) -> None:
        item = event(
            event_id="event-1",
            imported_at_us=100,
        )

        self.store.save_events([item])
        self.store.save_events([item])

        self.assertEqual(
            self.store.count(),
            1,
        )


    def test_full_public_event_is_preserved(
        self,
    ) -> None:
        item = event(
            event_id="event-route",
            imported_at_us=200,
            traceroute={
                "towards": [
                    "meshtastic:!00000001",
                    "meshtastic:!00000002",
                ],
                "back": [],
                "snr_towards": [],
                "snr_back": [],
            },
        )

        self.store.save_events([item])

        import sqlite3

        connection = sqlite3.connect(
            self.path
        )

        try:
            row = connection.execute(
                """
                SELECT
                    has_traceroute,
                    event_json
                FROM live_events
                WHERE event_id = ?
                """,
                ("event-route",),
            ).fetchone()

        finally:
            connection.close()

        self.assertEqual(
            row[0],
            1,
        )

        self.assertEqual(
            json.loads(row[1]),
            item,
        )

    def test_query_events_by_time_range(
        self,
    ) -> None:
        self.store.save_events(
            [
                event(
                    event_id="before",
                    imported_at_us=90,
                ),
                event(
                    event_id="first",
                    imported_at_us=100,
                ),
                event(
                    event_id="second",
                    imported_at_us=200,
                ),
                event(
                    event_id="after",
                    imported_at_us=300,
                ),
            ]
        )

        result = self.store.query_events(
            start_us=100,
            end_us=300,
        )

        self.assertEqual(
            [
                item["id"]
                for item in result.events
            ],
            [
                "first",
                "second",
            ],
        )
        self.assertEqual(
            result.total,
            2,
        )
        self.assertFalse(
            result.truncated
        )


    def test_query_events_can_filter_traceroutes(
        self,
    ) -> None:
        self.store.save_events(
            [
                event(
                    event_id="packet",
                    imported_at_us=100,
                ),
                event(
                    event_id="route",
                    imported_at_us=200,
                    traceroute={
                        "towards": [
                            "meshtastic:!00000001",
                            "meshtastic:!00000002",
                        ],
                        "back": [],
                        "snr_towards": [],
                        "snr_back": [],
                    },
                ),
            ]
        )

        routes = self.store.query_events(
            start_us=0,
            end_us=300,
            kind="traceroute",
        )

        packets = self.store.query_events(
            start_us=0,
            end_us=300,
            kind="packet",
        )

        self.assertEqual(
            [item["id"] for item in routes.events],
            ["route"],
        )

        self.assertEqual(
            [item["id"] for item in packets.events],
            ["packet"],
        )


    def test_query_events_reports_truncation(
        self,
    ) -> None:
        self.store.save_events(
            [
                event(
                    event_id=f"event-{index}",
                    imported_at_us=index,
                )
                for index in range(10)
            ]
        )

        result = self.store.query_events(
            start_us=0,
            end_us=20,
            limit=3,
        )

        self.assertEqual(
            len(result.events),
            3,
        )
        self.assertEqual(
            result.total,
            10,
        )
        self.assertTrue(
            result.truncated
        )


    def test_query_events_rejects_invalid_range(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "end_us debe ser maior",
        ):
            self.store.query_events(
                start_us=200,
                end_us=100,
            )


    def test_query_events_rejects_excessive_limit(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "entre 1 e 5000",
        ):
            self.store.query_events(
                start_us=0,
                end_us=100,
                limit=5001,
            )


    def test_hour_buckets_group_events_by_utc_hour(
        self,
    ) -> None:
        hour_us = 60 * 60 * 1_000_000

        self.store.save_events(
            [
                event(
                    event_id="h0-a",
                    imported_at_us=100,
                ),
                event(
                    event_id="h0-b",
                    imported_at_us=200,
                    traceroute={
                        "towards": [
                            "meshtastic:!00000001",
                            "meshtastic:!00000002",
                        ],
                        "back": [],
                        "snr_towards": [],
                        "snr_back": [],
                    },
                ),
                event(
                    event_id="h1",
                    imported_at_us=(
                        hour_us + 100
                    ),
                ),
            ]
        )

        buckets = self.store.hour_buckets()

        self.assertEqual(
            len(buckets),
            2,
        )

        self.assertEqual(
            buckets[0].start_us,
            0,
        )
        self.assertEqual(
            buckets[0].end_us,
            hour_us,
        )
        self.assertEqual(
            buckets[0].events,
            2,
        )
        self.assertEqual(
            buckets[0].traceroutes,
            1,
        )

        self.assertEqual(
            buckets[1].start_us,
            hour_us,
        )
        self.assertEqual(
            buckets[1].events,
            1,
        )



    def test_node_hours_indexes_all_event_participants(
        self,
    ) -> None:
        hour_us = 60 * 60 * 1_000_000

        first_hour = 10 * hour_us
        second_hour = 11 * hour_us

        first = event(
            event_id="first",
            imported_at_us=first_hour + 100,
        )

        first["from_id"] = "meshtastic:!00000001"
        first["to_id"] = "meshtastic:!00000002"
        first["observed"] = {
            "stages": [
                {
                    "gateways": [
                        {
                            "gateway_id":
                                "meshtastic:!00000003",
                        },
                        {
                            "gateway_id":
                                "meshtastic:!00000001",
                        },
                    ],
                },
            ],
        }
        first["traceroute"] = {
            "towards": [
                "meshtastic:!00000001",
                "meshtastic:!00000004",
                "meshtastic:!00000005",
            ],
            "back": [
                "meshtastic:!00000005",
                "meshtastic:!00000006",
                "meshtastic:!00000001",
            ],
            "snr_towards": [],
            "snr_back": [],
        }

        broadcast = event(
            event_id="broadcast",
            imported_at_us=first_hour + 200,
        )
        broadcast["from_id"] = "meshtastic:!00000007"
        broadcast["to_id"] = "meshtastic:!ffffffff"

        later = event(
            event_id="later",
            imported_at_us=second_hour + 100,
        )
        later["from_id"] = "meshtastic:!00000001"
        later["to_id"] = "meshtastic:!00000008"

        self.store.save_events(
            [
                first,
                broadcast,
                later,
            ]
        )

        result = self.store.node_hours()

        self.assertEqual(
            result["meshtastic:!00000001"],
            (
                first_hour,
                second_hour,
            ),
        )

        for node_id in (
            "meshtastic:!00000002",
            "meshtastic:!00000003",
            "meshtastic:!00000004",
            "meshtastic:!00000005",
            "meshtastic:!00000006",
            "meshtastic:!00000007",
        ):
            with self.subTest(node_id=node_id):
                self.assertEqual(
                    result[node_id],
                    (first_hour,),
                )

        self.assertEqual(
            result["meshtastic:!00000008"],
            (second_hour,),
        )

        self.assertNotIn(
            "meshtastic:!ffffffff",
            result,
        )


    def test_time_bounds_are_available(
        self,
    ) -> None:
        self.store.save_events(
            [
                event(
                    event_id="old",
                    imported_at_us=100,
                ),
                event(
                    event_id="new",
                    imported_at_us=300,
                ),
            ]
        )

        self.assertEqual(
            self.store.time_bounds(),
            (100, 300),
        )


    def test_prune_respects_retention(
        self,
    ) -> None:
        day_us = 24 * 60 * 60 * 1_000_000

        now_us = (
            1_800_000_000
            * 1_000_000
        )

        self.store.save_events(
            [
                event(
                    event_id="expired",
                    imported_at_us=(
                        now_us - 31 * day_us
                    ),
                ),
                event(
                    event_id="kept",
                    imported_at_us=(
                        now_us - 29 * day_us
                    ),
                ),
            ]
        )

        deleted = self.store.prune(
            reference=1_800_000_000,
        )

        self.assertEqual(
            deleted,
            1,
        )

        self.assertEqual(
            self.store.count(),
            1,
        )


if __name__ == "__main__":
    unittest.main()
