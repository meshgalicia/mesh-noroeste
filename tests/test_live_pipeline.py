"""Probas da xeración e escritura do documento live."""

from __future__ import annotations

import json
from pathlib import Path
import stat
import tempfile
import unittest

from mesh_noroeste.domain import (
    MeshtasticLivePacket,
    MeshtasticLiveReception,
)
from mesh_noroeste.live_pipeline import (
    LIVE_RETENTION_SECONDS,
    build_live_document_from_ozulo_batch,
    merge_live_documents,
    read_live_document,
    write_live_document,
)
from mesh_noroeste.ozulo_live_poll import (
    OzuloLiveBatch,
    OzuloLivePacketObservation,
)


GENERATED_AT = "2026-08-16T20:30:00Z"


def packet(
    *,
    packet_id: int = 100,
    imported_at_us: int = 1000,
    portnum: int = 3,
    payload: str = "",
) -> MeshtasticLivePacket:
    return MeshtasticLivePacket(
        source="ozulo_map",
        packet_id=packet_id,
        from_source_id="!00000001",
        to_source_id="!00000002",
        portnum=portnum,
        channel="LongFast",
        imported_at_us=imported_at_us,
        long_name="Orixe",
        to_long_name="Destino",
        payload=payload,
    )


def reception(
    *,
    packet_id: int = 100,
    imported_at_us: int = 1001,
) -> MeshtasticLiveReception:
    return MeshtasticLiveReception(
        source="ozulo_map",
        packet_id=packet_id,
        from_source_id="!00000001",
        gateway_source_id="!000000aa",
        rx_time=900,
        hop_limit=2,
        hop_start=3,
        snr_db=5.0,
        rssi_dbm=-80.0,
        channel="LongFast",
        topic=None,
        imported_at_us=imported_at_us,
    )


def batch() -> OzuloLiveBatch:
    return OzuloLiveBatch(
        observations=(
            OzuloLivePacketObservation(
                packet=packet(
                    portnum=70,
                    payload=(
                        "route: 3\n"
                        "snr_towards: -12\n"
                    ),
                ),
                receptions=(
                    reception(),
                ),
            ),
        ),
        previous_cursor=900,
        next_cursor=1000,
        saturated=False,
        bytes_received=1234,
    )


class LivePipelineTests(unittest.TestCase):
    def test_batch_becomes_public_live_document(
        self,
    ) -> None:
        document = (
            build_live_document_from_ozulo_batch(
                batch(),
                generated_at=GENERATED_AT,
            )
        )

        self.assertEqual(
            document["schema"],
            "mesh-noroeste.live/v1",
        )
        self.assertEqual(
            document["generated_at"],
            GENERATED_AT,
        )
        self.assertEqual(
            document["sources"]["ozulo_map"],
            {
                "previous_cursor": 900,
                "next_cursor": 1000,
                "possible_gap": False,
            },
        )

        self.assertEqual(
            len(document["events"]),
            1,
        )

        event = document["events"][0]

        self.assertEqual(
            event["evidence"],
            [
                "gateway_observation",
                "traceroute",
            ],
        )
        self.assertNotIn(
            "payload",
            event,
        )

    def test_saturated_batch_marks_possible_gap(
        self,
    ) -> None:
        source = batch()

        saturated = OzuloLiveBatch(
            observations=source.observations,
            previous_cursor=source.previous_cursor,
            next_cursor=source.next_cursor,
            saturated=True,
            bytes_received=source.bytes_received,
        )

        document = (
            build_live_document_from_ozulo_batch(
                saturated,
                generated_at=GENERATED_AT,
            )
        )

        self.assertIs(
            document["sources"][
                "ozulo_map"
            ]["possible_gap"],
            True,
        )

    def test_empty_batch_is_valid(
        self,
    ) -> None:
        empty = OzuloLiveBatch(
            observations=(),
            previous_cursor=1000,
            next_cursor=1000,
            saturated=False,
            bytes_received=20,
        )

        document = (
            build_live_document_from_ozulo_batch(
                empty,
                generated_at=GENERATED_AT,
            )
        )

        self.assertEqual(
            document["events"],
            [],
        )
        self.assertEqual(
            document["sources"][
                "ozulo_map"
            ]["next_cursor"],
            1000,
        )

    def test_live_documents_accumulate_within_retention(
        self,
    ) -> None:
        previous = {
            "schema": "mesh-noroeste.live/v1",
            "generated_at": "2026-08-16T20:29:00Z",
            "sources": {},
            "events": [
                {
                    "id": "event-1",
                    "imported_at_us": 1786912140000000,
                    "packet_id": 1,
                    "from_id": "meshtastic:!1",
                },
            ],
        }

        current = {
            "schema": "mesh-noroeste.live/v1",
            "generated_at": "2026-08-16T20:30:00Z",
            "sources": {
                "ozulo_map": {
                    "previous_cursor": 1,
                    "next_cursor": 2,
                    "possible_gap": False,
                },
            },
            "events": [
                {
                    "id": "event-2",
                    "imported_at_us": 1786912200000000,
                    "packet_id": 2,
                    "from_id": "meshtastic:!2",
                },
            ],
        }

        merged = merge_live_documents(
            previous,
            current,
        )

        self.assertEqual(
            [event["id"] for event in merged["events"]],
            ["event-1", "event-2"],
        )
        self.assertEqual(
            merged["generated_at"],
            current["generated_at"],
        )
        self.assertEqual(
            merged["sources"],
            current["sources"],
        )

    def test_live_documents_deduplicate_events(
        self,
    ) -> None:
        previous = {
            "schema": "mesh-noroeste.live/v1",
            "generated_at": "2026-08-16T20:29:00Z",
            "sources": {},
            "events": [
                {
                    "id": "same-event",
                    "imported_at_us": 1786912140000000,
                    "packet_id": 1,
                    "from_id": "meshtastic:!1",
                    "marker": "old",
                },
            ],
        }

        current = {
            "schema": "mesh-noroeste.live/v1",
            "generated_at": "2026-08-16T20:30:00Z",
            "sources": {},
            "events": [
                {
                    "id": "same-event",
                    "imported_at_us": 1786912140000000,
                    "packet_id": 1,
                    "from_id": "meshtastic:!1",
                    "marker": "new",
                },
            ],
        }

        merged = merge_live_documents(
            previous,
            current,
        )

        self.assertEqual(
            len(merged["events"]),
            1,
        )
        self.assertEqual(
            merged["events"][0]["marker"],
            "new",
        )

    def test_live_documents_expire_after_one_hour(
        self,
    ) -> None:
        previous = {
            "schema": "mesh-noroeste.live/v1",
            "generated_at": "2026-08-16T19:00:00Z",
            "sources": {},
            "events": [
                {
                    "id": "expired",
                    # 18:59:59 UTC: un segundo fóra
                    # da xanela de 60 minutos.
                    "imported_at_us": 1786906799000000,
                    "packet_id": 1,
                    "from_id": "meshtastic:!1",
                },
                {
                    "id": "boundary",
                    # 19:00:00 UTC: exactamente no límite.
                    "imported_at_us": 1786906800000000,
                    "packet_id": 2,
                    "from_id": "meshtastic:!2",
                },
                {
                    "id": "kept",
                    # 19:30:00 UTC.
                    "imported_at_us": 1786908600000000,
                    "packet_id": 3,
                    "from_id": "meshtastic:!3",
                },
            ],
        }

        current = {
            "schema": "mesh-noroeste.live/v1",
            "generated_at": "2026-08-16T20:00:00Z",
            "sources": {},
            "events": [],
        }

        merged = merge_live_documents(
            previous,
            current,
        )

        self.assertEqual(
            LIVE_RETENTION_SECONDS,
            60 * 60,
        )
        self.assertEqual(
            [event["id"] for event in merged["events"]],
            ["boundary", "kept"],
        )

    def test_empty_batch_keeps_recent_previous_events(
        self,
    ) -> None:
        previous = {
            "schema": "mesh-noroeste.live/v1",
            "generated_at": "2026-08-16T20:29:00Z",
            "sources": {},
            "events": [
                {
                    "id": "recent",
                    "imported_at_us": 1786912140000000,
                    "packet_id": 1,
                    "from_id": "meshtastic:!1",
                },
            ],
        }

        current = {
            "schema": "mesh-noroeste.live/v1",
            "generated_at": "2026-08-16T20:30:00Z",
            "sources": {},
            "events": [],
        }

        merged = merge_live_documents(
            previous,
            current,
        )

        self.assertEqual(
            [event["id"] for event in merged["events"]],
            ["recent"],
        )
        self.assertEqual(
            merged["generated_at"],
            "2026-08-16T20:30:00Z",
        )

    def test_read_old_v1_event_adds_null_telemetry(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            path = root / "live.json"

            path.write_text(
                json.dumps(
                    {
                        "schema": "mesh-noroeste.live/v1",
                        "generated_at": GENERATED_AT,
                        "sources": {},
                        "events": [
                            {
                                "id": "old-event",
                                "imported_at_us": 100,
                                "packet_id": 1,
                                "from_id": "meshtastic:!00000001",
                                "traceroute": None,
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            document = read_live_document(
                root
            )

            self.assertIsNotNone(
                document
            )

            assert document is not None

            self.assertIn(
                "telemetry",
                document["events"][0],
            )

            self.assertIsNone(
                document["events"][0]["telemetry"]
            )



    def test_written_live_document_can_be_read_back(
        self,
    ) -> None:
        document = (
            build_live_document_from_ozulo_batch(
                batch(),
                generated_at=GENERATED_AT,
            )
        )

        with tempfile.TemporaryDirectory() as temporary:
            write_live_document(
                temporary,
                document,
            )

            self.assertEqual(
                read_live_document(temporary),
                document,
            )


    def test_document_is_written_atomically(
        self,
    ) -> None:
        document = (
            build_live_document_from_ozulo_batch(
                batch(),
                generated_at=GENERATED_AT,
            )
        )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            path = write_live_document(
                root,
                document,
            )

            self.assertEqual(
                path,
                root / "live.json",
            )
            self.assertTrue(
                path.is_file()
            )

            stored = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                stored,
                document,
            )

            self.assertEqual(
                stat.S_IMODE(
                    path.stat().st_mode
                ),
                0o644,
            )

            self.assertEqual(
                list(
                    root.glob(
                        ".live.json.*.tmp"
                    )
                ),
                [],
            )

    def test_failed_serialization_preserves_previous_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "live.json"

            path.write_text(
                '{"previous": true}\n',
                encoding="utf-8",
            )

            invalid = {
                "schema": "mesh-noroeste.live/v1",
                "generated_at": GENERATED_AT,
                "sources": {},
                "events": [],
                "bad": float("nan"),
            }

            with self.assertRaises(
                ValueError
            ):
                write_live_document(
                    root,
                    invalid,
                )

            self.assertEqual(
                path.read_text(
                    encoding="utf-8"
                ),
                '{"previous": true}\n',
            )

            self.assertEqual(
                list(
                    root.glob(
                        ".live.json.*.tmp"
                    )
                ),
                [],
            )

    def test_wrong_schema_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                ValueError,
                "schema live esperado",
            ):
                write_live_document(
                    temporary,
                    {
                        "schema": "outra-cousa",
                        "generated_at": GENERATED_AT,
                    },
                )


if __name__ == "__main__":
    unittest.main()
