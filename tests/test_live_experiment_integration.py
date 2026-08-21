"""Probas da integración do Experiment Store no runner live."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mesh_noroeste.domain import (
    MeshtasticLivePacket,
)
from mesh_noroeste.live_runner import (
    run_ozulo_live_once,
)
from mesh_noroeste.ozulo_live_poll import (
    OzuloLiveBatch,
    OzuloLivePacketObservation,
)
from mesh_noroeste.storage import (
    ObservationStore,
)


GENERATED_AT = "2026-08-19T12:00:00Z"


def packet(
    *,
    packet_id: int = 123,
    imported_at_us: int = 1787137200000000,
) -> MeshtasticLivePacket:
    return MeshtasticLivePacket(
        source="ozulo_map",
        packet_id=packet_id,
        from_source_id="!a5b7f496",
        to_source_id="!ffffffff",
        portnum=67,
        channel="LongFast",
        imported_at_us=imported_at_us,
        long_name="Nodo proba",
        to_long_name=None,
        payload=(
            "time: 1787137190\n"
            "device_metrics {\n"
            "  battery_level: 88\n"
            "  voltage: 4.039\n"
            "  channel_utilization: 13.341667\n"
            "  air_util_tx: 2.1988335\n"
            "  uptime_seconds: 1726483\n"
            "}\n"
        ),
    )


def batch() -> OzuloLiveBatch:
    return OzuloLiveBatch(
        observations=(
            OzuloLivePacketObservation(
                packet=packet(),
                receptions=(),
            ),
        ),
        previous_cursor=None,
        next_cursor=1787137200000000,
        saturated=False,
        bytes_received=100,
    )


class LiveExperimentIntegrationTests(
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

        self.database = (
            self.root
            / "state"
            / "mesh-noroeste.db"
        )

        self.output = (
            self.root
            / "data"
        )

        self.store = ObservationStore(
            self.database
        )


    def test_live_run_persists_experiment_observation(
        self,
    ) -> None:
        source_batch = batch()

        def poller(**kwargs):
            self.assertIsNone(
                kwargs["cursor"]
            )

            return source_batch

        result = run_ozulo_live_once(
            self.store,
            self.output,
            generated_at=GENERATED_AT,
            poller=poller,
        )

        self.assertEqual(
            result.next_cursor,
            1787137200000000,
        )

        experiment_database = (
            self.database.with_name(
                "meshtastic-experiment.db"
            )
        )

        self.assertTrue(
            experiment_database.is_file()
        )

        import sqlite3

        connection = sqlite3.connect(
            experiment_database
        )

        connection.row_factory = (
            sqlite3.Row
        )

        try:
            row = connection.execute(
                """
                SELECT
                    channel,
                    portnum,
                    channel_utilization,
                    air_util_tx
                FROM experiment_observations
                WHERE event_id = ?
                """,
                (
                    (
                        "meshtastic:"
                        "live_packet:"
                        "123:!a5b7f496"
                    ),
                ),
            ).fetchone()

        finally:
            connection.close()

        self.assertIsNotNone(row)

        assert row is not None

        self.assertEqual(
            row["channel"],
            "LongFast",
        )

        self.assertEqual(
            row["portnum"],
            67,
        )

        self.assertEqual(
            row["channel_utilization"],
            13.341667,
        )

        self.assertEqual(
            row["air_util_tx"],
            2.1988335,
        )


    def test_live_run_publishes_experiment_report(
        self,
    ) -> None:
        source_batch = batch()

        def poller(**kwargs):
            return source_batch

        run_ozulo_live_once(
            self.store,
            self.output,
            generated_at=GENERATED_AT,
            poller=poller,
        )

        experiment_document = (
            self.output
            / "experiment.json"
        )

        self.assertTrue(
            experiment_document.is_file()
        )

        document = json.loads(
            experiment_document.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            document["schema"],
            (
                "mesh-noroeste."
                "meshtastic-experiment/v1"
            ),
        )

        self.assertEqual(
            document["generated_at"],
            GENERATED_AT,
        )

        self.assertEqual(
            document["channels"][
                "LongFast"
            ]["packets"],
            1,
        )

        self.assertEqual(
            document["channels"][
                "LongFast"
            ]["telemetry_samples"],
            1,
        )

        self.assertEqual(
            document["channels"][
                "LongFast"
            ][
                "channel_utilization"
            ][
                "mean"
            ],
            13.341667,
        )

        self.assertEqual(
            document["channels"][
                "LongFast"
            ][
                "air_util_tx"
            ][
                "mean"
            ],
            2.1988335,
        )

        self.assertEqual(
            document["channels"][
                "LongFast"
            ][
                "channel_utilization"
            ][
                "samples"
            ],
            1,
        )

        self.assertEqual(
            document["channels"][
                "LongFast"
            ][
                "air_util_tx"
            ][
                "samples"
            ],
            1,
        )


    def test_experiment_publication_failure_does_not_advance_cursor(
        self,
    ) -> None:
        source_batch = batch()

        def poller(**kwargs):
            return source_batch

        with patch(
            (
                "mesh_noroeste.live_runner."
                "publish_experiment_report"
            ),
            side_effect=RuntimeError(
                "fallo publicación experimental"
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "fallo publicación experimental",
            ):
                run_ozulo_live_once(
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

        experiment_database = (
            self.database.with_name(
                "meshtastic-experiment.db"
            )
        )

        self.assertTrue(
            experiment_database.is_file()
        )


    def test_experiment_failure_does_not_advance_cursor(
        self,
    ) -> None:
        source_batch = batch()

        def poller(**kwargs):
            return source_batch

        with patch(
            (
                "mesh_noroeste.live_runner."
                "store_live_document"
            ),
            side_effect=RuntimeError(
                "fallo experimental"
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "fallo experimental",
            ):
                run_ozulo_live_once(
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


    def test_repeated_batch_is_idempotent_in_experiment_store(
        self,
    ) -> None:
        source_batch = batch()

        def poller(**kwargs):
            return OzuloLiveBatch(
                observations=(
                    source_batch.observations
                ),
                previous_cursor=(
                    kwargs["cursor"]
                ),
                next_cursor=(
                    1787137200000000
                    if kwargs["cursor"] is None
                    else 1787137200000001
                ),
                saturated=False,
                        bytes_received=100,
            )

        run_ozulo_live_once(
            self.store,
            self.output,
            generated_at=GENERATED_AT,
            poller=poller,
        )

        run_ozulo_live_once(
            self.store,
            self.output,
            generated_at=(
                "2026-08-19T12:01:00Z"
            ),
            poller=poller,
        )

        import sqlite3

        connection = sqlite3.connect(
            self.database.with_name(
                "meshtastic-experiment.db"
            )
        )

        try:
            total = connection.execute(
                """
                SELECT COUNT(*)
                FROM experiment_observations
                """
            ).fetchone()[0]

        finally:
            connection.close()

        self.assertEqual(
            total,
            1,
        )


if __name__ == "__main__":
    unittest.main()
