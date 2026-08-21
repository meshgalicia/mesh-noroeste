"""Probas da execución segura dunha iteración live."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from mesh_noroeste.live_history import (
    LIVE_HISTORY_RETENTION_SECONDS,
    LiveHistoryStore,
)
from mesh_noroeste.live_history_publication import (
    HOUR_US,
    publish_history_hour,
)
from mesh_noroeste.live_runner import (
    run_ozulo_live_once,
)
from mesh_noroeste.ozulo_live_poll import (
    OzuloLiveBatch,
)
from mesh_noroeste.storage import ObservationStore


GENERATED_AT = "2026-08-17T06:00:00Z"


def batch(
    *,
    previous_cursor: int | None,
    next_cursor: int | None,
    saturated: bool = False,
) -> OzuloLiveBatch:
    return OzuloLiveBatch(
        observations=(),
        previous_cursor=previous_cursor,
        next_cursor=next_cursor,
        saturated=saturated,
        bytes_received=123,
    )


def public_event(
    *,
    event_id: str,
    imported_at_us: int,
) -> dict:
    return {
        "id": event_id,
        "network": "meshtastic",
        "source": "ozulo_map",
        "packet_id": 123,
        "from_id": "meshtastic:!00000001",
        "to_id": "meshtastic:!ffffffff",
        "portnum": 3,
        "channel": "LongFast",
        "imported_at_us": imported_at_us,
        "long_name": "Nodo",
        "to_long_name": None,
        "evidence": [
            "gateway_observation"
        ],
        "observed": {
            "gateway_count": 0,
            "stage_count": 0,
            "stages": [],
        },
        "traceroute": None,
    }



class LiveRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)

        self.root = Path(self.temporary.name)

        self.store = ObservationStore(
            self.root / "state.db"
        )

        self.output = self.root / "public"

    def test_success_confirms_cursor_after_write(
        self,
    ) -> None:
        calls: list[str] = []

        def poller(*, cursor):
            calls.append("poll")
            self.assertIsNone(cursor)

            return batch(
                previous_cursor=None,
                next_cursor=200,
            )

        def builder(received, *, generated_at):
            calls.append("build")

            self.assertEqual(
                received.next_cursor,
                200,
            )
            self.assertEqual(
                generated_at,
                GENERATED_AT,
            )

            return {
                "schema": "mesh-noroeste.live/v1",
                "generated_at": generated_at,
                "sources": {},
                "events": [],
            }

        def writer(output, document):
            calls.append("write")

            self.assertIsNone(
                self.store.load_live_cursor(
                    "ozulo_map"
                )
            )

            path = Path(output) / "live.json"
            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            path.write_text(
                "{}\n",
                encoding="utf-8",
            )

            return path

        result = run_ozulo_live_once(
            self.store,
            self.output,
            generated_at=GENERATED_AT,
            poller=poller,
            document_builder=builder,
            writer=writer,
        )

        self.assertEqual(
            calls,
            ["poll", "build", "write"],
        )
        self.assertEqual(
            self.store.load_live_cursor(
                "ozulo_map"
            ),
            200,
        )
        self.assertEqual(
            result.previous_cursor,
            None,
        )
        self.assertEqual(
            result.next_cursor,
            200,
        )
        self.assertEqual(
            result.events,
            0,
        )
        self.assertFalse(
            result.possible_gap
        )
        self.assertEqual(
            result.bytes_received,
            123,
        )

    def test_success_creates_history_database(
        self,
    ) -> None:
        def poller(*, cursor):
            return batch(
                previous_cursor=cursor,
                next_cursor=100,
            )

        run_ozulo_live_once(
            self.store,
            self.output,
            generated_at=GENERATED_AT,
            poller=poller,
        )

        history_path = (
            self.store.database_path.with_name(
                "live-history.db"
            )
        )

        self.assertTrue(
            history_path.exists()
        )

    def test_success_publishes_history_manifest(
        self,
    ) -> None:
        def poller(*, cursor):
            return batch(
                previous_cursor=cursor,
                next_cursor=100,
            )

        run_ozulo_live_once(
            self.store,
            self.output,
            generated_at=GENERATED_AT,
            poller=poller,
        )

        manifest = (
            self.output
            / "history"
            / "manifest.json"
        )

        self.assertTrue(
            manifest.exists()
        )


    def test_success_publishes_hour_touched_by_batch(
        self,
    ) -> None:
        hour_us = (
            60 * 60 * 1_000_000
        )

        start_us = (
            1_800_000_000
            * 1_000_000
        )
        start_us -= (
            start_us % hour_us
        )

        def poller(*, cursor):
            return batch(
                previous_cursor=cursor,
                next_cursor=100,
            )

        def builder(received, *, generated_at):
            return {
                "schema": "mesh-noroeste.live/v1",
                "generated_at": generated_at,
                "sources": {},
                "events": [
                    public_event(
                        event_id="event-1",
                        imported_at_us=(
                            start_us + 100
                        ),
                    )
                ],
            }

        run_ozulo_live_once(
            self.store,
            self.output,
            generated_at=GENERATED_AT,
            poller=poller,
            document_builder=builder,
        )

        from datetime import (
            datetime,
            timezone,
        )

        moment = datetime.fromtimestamp(
            start_us / 1_000_000,
            tz=timezone.utc,
        )

        path = (
            self.output
            / "history"
            / moment.strftime("%Y-%m-%d")
            / (
                moment.strftime("%H")
                + ".json"
            )
        )

        self.assertTrue(
            path.exists()
        )


    def test_batch_crossing_hour_publishes_both_hours(
        self,
    ) -> None:
        hour_us = (
            60 * 60 * 1_000_000
        )

        first_hour = (
            1_800_000_000
            * 1_000_000
        )
        first_hour -= (
            first_hour % hour_us
        )

        second_hour = (
            first_hour + hour_us
        )

        def poller(*, cursor):
            return batch(
                previous_cursor=cursor,
                next_cursor=100,
            )

        def builder(received, *, generated_at):
            return {
                "schema": "mesh-noroeste.live/v1",
                "generated_at": generated_at,
                "sources": {},
                "events": [
                    public_event(
                        event_id="before-boundary",
                        imported_at_us=(
                            first_hour
                            + hour_us
                            - 1
                        ),
                    ),
                    public_event(
                        event_id="after-boundary",
                        imported_at_us=(
                            second_hour + 1
                        ),
                    ),
                ],
            }

        run_ozulo_live_once(
            self.store,
            self.output,
            generated_at=GENERATED_AT,
            poller=poller,
            document_builder=builder,
        )

        from datetime import (
            datetime,
            timezone,
        )

        for start_us in (
            first_hour,
            second_hour,
        ):
            moment = datetime.fromtimestamp(
                start_us / 1_000_000,
                tz=timezone.utc,
            )

            path = (
                self.output
                / "history"
                / moment.strftime("%Y-%m-%d")
                / (
                    moment.strftime("%H")
                    + ".json"
                )
            )

            self.assertTrue(
                path.exists()
            )



    def test_prune_republishes_retention_boundary_hour(
        self,
    ) -> None:
        reference = datetime(
            2026,
            8,
            17,
            6,
            23,
            tzinfo=timezone.utc,
        )

        cutoff = (
            reference
            - timedelta(
                seconds=LIVE_HISTORY_RETENTION_SECONDS
            )
        )

        cutoff_us = int(
            cutoff.timestamp()
            * 1_000_000
        )

        boundary_hour_us = (
            cutoff_us // HOUR_US
        ) * HOUR_US

        expired_us = (
            boundary_hour_us
            + 10 * 60 * 1_000_000
        )

        retained_us = (
            boundary_hour_us
            + 40 * 60 * 1_000_000
        )

        self.assertLess(
            expired_us,
            cutoff_us,
        )
        self.assertGreaterEqual(
            retained_us,
            cutoff_us,
        )

        history_store = LiveHistoryStore(
            self.store.database_path.with_name(
                "live-history.db"
            )
        )

        history_store.save_events(
            [
                public_event(
                    event_id="expired",
                    imported_at_us=expired_us,
                ),
                public_event(
                    event_id="retained",
                    imported_at_us=retained_us,
                ),
            ]
        )

        hour_path = publish_history_hour(
            history_store,
            self.output,
            start_us=boundary_hour_us,
            generated_at=reference.isoformat(),
        )

        before = json.loads(
            hour_path.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            {
                event["id"]
                for event in before["events"]
            },
            {
                "expired",
                "retained",
            },
        )

        def poller(*, cursor):
            return batch(
                previous_cursor=cursor,
                next_cursor=100,
            )

        run_ozulo_live_once(
            self.store,
            self.output,
            generated_at=(
                reference
                .isoformat()
                .replace("+00:00", "Z")
            ),
            poller=poller,
        )

        after = json.loads(
            hour_path.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            [
                event["id"]
                for event in after["events"]
            ],
            ["retained"],
        )

        self.assertEqual(
            after["event_count"],
            1,
        )

        self.assertEqual(
            history_store.count(),
            1,
        )


    def test_existing_cursor_is_used_for_poll(
        self,
    ) -> None:
        self.store.save_live_cursor(
            "ozulo_map",
            100,
            updated_at="2026-08-17T05:00:00Z",
        )

        received_cursor: list[int | None] = []

        def poller(*, cursor):
            received_cursor.append(cursor)

            return batch(
                previous_cursor=100,
                next_cursor=150,
            )

        run_ozulo_live_once(
            self.store,
            self.output,
            generated_at=GENERATED_AT,
            poller=poller,
        )

        self.assertEqual(
            received_cursor,
            [100],
        )
        self.assertEqual(
            self.store.load_live_cursor(
                "ozulo_map"
            ),
            150,
        )

    def test_poll_failure_does_not_advance_cursor(
        self,
    ) -> None:
        self.store.save_live_cursor(
            "ozulo_map",
            100,
            updated_at="2026-08-17T05:00:00Z",
        )

        def poller(*, cursor):
            self.assertEqual(cursor, 100)
            raise RuntimeError("fallo HTTP")

        with self.assertRaisesRegex(
            RuntimeError,
            "fallo HTTP",
        ):
            run_ozulo_live_once(
                self.store,
                self.output,
                generated_at=GENERATED_AT,
                poller=poller,
            )

        self.assertEqual(
            self.store.load_live_cursor(
                "ozulo_map"
            ),
            100,
        )

    def test_build_failure_does_not_advance_cursor(
        self,
    ) -> None:
        self.store.save_live_cursor(
            "ozulo_map",
            100,
            updated_at="2026-08-17T05:00:00Z",
        )

        def poller(*, cursor):
            return batch(
                previous_cursor=cursor,
                next_cursor=200,
            )

        def builder(received, *, generated_at):
            raise RuntimeError(
                "fallo construíndo documento"
            )

        with self.assertRaisesRegex(
            RuntimeError,
            "fallo construíndo",
        ):
            run_ozulo_live_once(
                self.store,
                self.output,
                generated_at=GENERATED_AT,
                poller=poller,
                document_builder=builder,
            )

        self.assertEqual(
            self.store.load_live_cursor(
                "ozulo_map"
            ),
            100,
        )

    def test_write_failure_does_not_advance_cursor(
        self,
    ) -> None:
        self.store.save_live_cursor(
            "ozulo_map",
            100,
            updated_at="2026-08-17T05:00:00Z",
        )

        def poller(*, cursor):
            return batch(
                previous_cursor=cursor,
                next_cursor=200,
            )

        def writer(output, document):
            raise OSError(
                "fallo escribindo live.json"
            )

        with self.assertRaisesRegex(
            OSError,
            "fallo escribindo",
        ):
            run_ozulo_live_once(
                self.store,
                self.output,
                generated_at=GENERATED_AT,
                poller=poller,
                writer=writer,
            )

        self.assertEqual(
            self.store.load_live_cursor(
                "ozulo_map"
            ),
            100,
        )

    def test_initial_empty_batch_without_cursor_keeps_none(
        self,
    ) -> None:
        def poller(*, cursor):
            self.assertIsNone(cursor)

            return batch(
                previous_cursor=None,
                next_cursor=None,
            )

        result = run_ozulo_live_once(
            self.store,
            self.output,
            generated_at=GENERATED_AT,
            poller=poller,
        )

        self.assertIsNone(
            self.store.load_live_cursor(
                "ozulo_map"
            )
        )
        self.assertIsNone(
            result.next_cursor
        )

    def test_empty_incremental_batch_can_keep_cursor(
        self,
    ) -> None:
        self.store.save_live_cursor(
            "ozulo_map",
            100,
            updated_at="2026-08-17T05:00:00Z",
        )

        def poller(*, cursor):
            return batch(
                previous_cursor=cursor,
                next_cursor=cursor,
            )

        result = run_ozulo_live_once(
            self.store,
            self.output,
            generated_at=GENERATED_AT,
            poller=poller,
        )

        self.assertEqual(
            self.store.load_live_cursor(
                "ozulo_map"
            ),
            100,
        )
        self.assertEqual(
            result.previous_cursor,
            100,
        )
        self.assertEqual(
            result.next_cursor,
            100,
        )

    def test_mismatched_batch_cursor_is_rejected(
        self,
    ) -> None:
        self.store.save_live_cursor(
            "ozulo_map",
            100,
            updated_at="2026-08-17T05:00:00Z",
        )

        def poller(*, cursor):
            return batch(
                previous_cursor=99,
                next_cursor=200,
            )

        with self.assertRaisesRegex(
            ValueError,
            "non corresponde",
        ):
            run_ozulo_live_once(
                self.store,
                self.output,
                generated_at=GENERATED_AT,
                poller=poller,
            )

        self.assertEqual(
            self.store.load_live_cursor(
                "ozulo_map"
            ),
            100,
        )


if __name__ == "__main__":
    unittest.main()
