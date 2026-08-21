"""Probas da publicación estática do histórico live."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from mesh_noroeste.live_history import (
    LiveHistoryStore,
)
from mesh_noroeste.live_history_publication import (
    HISTORY_HOUR_SCHEMA_ID,
    HISTORY_MANIFEST_SCHEMA_ID,
    HOUR_US,
    build_history_hour_document,
    build_history_manifest,
    cleanup_history_publication,
    history_hour_key,
    history_hour_path,
    publish_history_hour,
    publish_history_manifest,
)


GENERATED_AT = "2026-08-19T10:00:00Z"


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


class LiveHistoryPublicationTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(
            self.temporary.cleanup
        )

        self.root = Path(
            self.temporary.name
        )

        self.store = LiveHistoryStore(
            self.root / "live-history.db"
        )

        self.output = (
            self.root / "public"
        )


    def test_hour_key_and_path_are_utc(
        self,
    ) -> None:
        start_us = int(
            1787122800 * 1_000_000
        )

        self.assertEqual(
            history_hour_key(start_us),
            "2026-08-19T07",
        )

        self.assertEqual(
            history_hour_path(start_us),
            "2026-08-19/07.json",
        )


    def test_hour_document_contains_only_that_hour(
        self,
    ) -> None:
        start_us = (
            1_800_000_000
            * 1_000_000
        )

        start_us -= (
            start_us % HOUR_US
        )

        self.store.save_events(
            [
                event(
                    event_id="before",
                    imported_at_us=(
                        start_us - 1
                    ),
                ),
                event(
                    event_id="inside",
                    imported_at_us=(
                        start_us + 100
                    ),
                ),
                event(
                    event_id="after",
                    imported_at_us=(
                        start_us + HOUR_US
                    ),
                ),
            ]
        )

        document = (
            build_history_hour_document(
                self.store,
                start_us=start_us,
                generated_at=GENERATED_AT,
            )
        )

        self.assertEqual(
            document["schema"],
            HISTORY_HOUR_SCHEMA_ID,
        )
        self.assertEqual(
            document["event_count"],
            1,
        )
        self.assertEqual(
            [
                item["id"]
                for item in document["events"]
            ],
            ["inside"],
        )


    def test_manifest_lists_available_hours(
        self,
    ) -> None:
        start_us = (
            1_800_000_000
            * 1_000_000
        )

        start_us -= (
            start_us % HOUR_US
        )

        self.store.save_events(
            [
                event(
                    event_id="first",
                    imported_at_us=(
                        start_us + 1
                    ),
                ),
                event(
                    event_id="second",
                    imported_at_us=(
                        start_us
                        + HOUR_US
                        + 1
                    ),
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

        document = build_history_manifest(
            self.store,
            generated_at=GENERATED_AT,
        )

        self.assertEqual(
            document["schema"],
            HISTORY_MANIFEST_SCHEMA_ID,
        )
        self.assertEqual(
            document["hour_count"],
            2,
        )
        self.assertEqual(
            document["event_count"],
            2,
        )
        self.assertEqual(
            document["traceroute_count"],
            1,
        )
        self.assertEqual(
            len(document["hours"]),
            2,
        )


    def test_manifest_indexes_hours_by_node(
        self,
    ) -> None:
        start_us = int(
            1787122800 * 1_000_000
        )

        first = event(
            event_id="first",
            imported_at_us=(
                start_us + 1
            ),
        )
        first["from_id"] = (
            "meshtastic:!00000001"
        )
        first["to_id"] = (
            "meshtastic:!00000002"
        )
        first["observed"] = {
            "stages": [
                {
                    "gateways": [
                        {
                            "gateway_id":
                                "meshtastic:!00000003",
                        },
                    ],
                },
            ],
        }

        second = event(
            event_id="second",
            imported_at_us=(
                start_us
                + HOUR_US
                + 1
            ),
        )
        second["from_id"] = (
            "meshtastic:!00000001"
        )
        second["to_id"] = (
            "meshtastic:!ffffffff"
        )

        self.store.save_events(
            [
                first,
                second,
            ]
        )

        document = build_history_manifest(
            self.store,
            generated_at=GENERATED_AT,
        )

        self.assertEqual(
            document["node_hours"][
                "meshtastic:!00000001"
            ],
            [
                "2026-08-19T07",
                "2026-08-19T08",
            ],
        )

        self.assertEqual(
            document["node_hours"][
                "meshtastic:!00000002"
            ],
            [
                "2026-08-19T07",
            ],
        )

        self.assertEqual(
            document["node_hours"][
                "meshtastic:!00000003"
            ],
            [
                "2026-08-19T07",
            ],
        )

        self.assertNotIn(
            "meshtastic:!ffffffff",
            document["node_hours"],
        )


    def test_hour_is_written_to_dated_path(
        self,
    ) -> None:
        start_us = int(
            1787122800 * 1_000_000
        )

        self.store.save_events(
            [
                event(
                    event_id="inside",
                    imported_at_us=(
                        start_us + 1
                    ),
                )
            ]
        )

        path = publish_history_hour(
            self.store,
            self.output,
            start_us=start_us,
            generated_at=GENERATED_AT,
        )

        self.assertEqual(
            path,
            (
                self.output
                / "history"
                / "2026-08-19"
                / "07.json"
            ).resolve(),
        )

        document = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            document["event_count"],
            1,
        )


    def test_manifest_is_written_atomically(
        self,
    ) -> None:
        self.store.initialize()

        path = publish_history_manifest(
            self.store,
            self.output,
            generated_at=GENERATED_AT,
        )

        self.assertEqual(
            path,
            (
                self.output
                / "history"
                / "manifest.json"
            ).resolve(),
        )

        document = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            document["schema"],
            HISTORY_MANIFEST_SCHEMA_ID,
        )


    def test_cleanup_removes_only_stale_hour_documents(
        self,
    ) -> None:
        start_us = int(
            1787122800 * 1_000_000
        )

        self.store.save_events(
            [
                event(
                    event_id="kept",
                    imported_at_us=(
                        start_us + 1
                    ),
                )
            ]
        )

        kept = publish_history_hour(
            self.store,
            self.output,
            start_us=start_us,
            generated_at=GENERATED_AT,
        )

        stale_directory = (
            self.output
            / "history"
            / "2026-08-18"
        )
        stale_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        stale = (
            stale_directory
            / "06.json"
        )
        stale.write_text(
            "{}\n",
            encoding="utf-8",
        )

        unrelated = (
            stale_directory
            / "notes.json"
        )
        unrelated.write_text(
            "{}\n",
            encoding="utf-8",
        )

        manifest = (
            self.output
            / "history"
            / "manifest.json"
        )
        manifest.write_text(
            "{}\n",
            encoding="utf-8",
        )

        removed = cleanup_history_publication(
            self.store,
            self.output,
        )

        self.assertEqual(
            removed,
            1,
        )
        self.assertTrue(
            kept.exists()
        )
        self.assertFalse(
            stale.exists()
        )
        self.assertTrue(
            unrelated.exists()
        )
        self.assertTrue(
            manifest.exists()
        )


    def test_cleanup_removes_empty_date_directory(
        self,
    ) -> None:
        stale_directory = (
            self.output
            / "history"
            / "2026-08-18"
        )
        stale_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        (
            stale_directory
            / "06.json"
        ).write_text(
            "{}\n",
            encoding="utf-8",
        )

        removed = cleanup_history_publication(
            self.store,
            self.output,
        )

        self.assertEqual(
            removed,
            1,
        )
        self.assertFalse(
            stale_directory.exists()
        )


    def test_hour_start_must_be_aligned(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "inicio dunha hora UTC",
        ):
            build_history_hour_document(
                self.store,
                start_us=123,
                generated_at=GENERATED_AT,
            )


if __name__ == "__main__":
    unittest.main()
