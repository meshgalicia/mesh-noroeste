"""Probas da execución segura dunha iteración live."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

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
