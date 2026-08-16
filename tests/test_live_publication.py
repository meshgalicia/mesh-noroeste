"""Probas do contrato público do tráfico Meshtastic en directo."""

from __future__ import annotations

import unittest

from mesh_noroeste.domain import (
    MeshtasticLivePacket,
    MeshtasticLiveReception,
)
from mesh_noroeste.live_publication import (
    LIVE_SCHEMA_ID,
    LiveSourceState,
    build_live_document,
    live_event_document,
)
from mesh_noroeste.live_view import (
    build_live_packet_view,
)


GENERATED_AT = "2026-08-16T20:00:00Z"


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


def reception() -> MeshtasticLiveReception:
    return MeshtasticLiveReception(
        source="ozulo_map",
        packet_id=100,
        from_source_id="!00000001",
        gateway_source_id="!000000aa",
        rx_time=900,
        hop_limit=2,
        hop_start=3,
        snr_db=5.25,
        rssi_dbm=-81.0,
        channel="LongFast",
        topic=(
            "msh/EU_868/2/e/"
            "LongFast/!000000aa"
        ),
        imported_at_us=1001,
    )


class LivePublicationTests(unittest.TestCase):
    def test_regular_event_is_public_without_raw_payload(
        self,
    ) -> None:
        view = build_live_packet_view(
            packet(payload="segredo bruto"),
            (reception(),),
        )

        event = live_event_document(view)

        self.assertNotIn("payload", event)

        self.assertEqual(
            event,
            {
                "id": (
                    "meshtastic:live_packet:"
                    "100:!00000001"
                ),
                "network": "meshtastic",
                "source": "ozulo_map",
                "packet_id": 100,
                "from_id": (
                    "meshtastic:!00000001"
                ),
                "to_id": (
                    "meshtastic:!00000002"
                ),
                "portnum": 3,
                "channel": "LongFast",
                "imported_at_us": 1000,
                "long_name": "Orixe",
                "to_long_name": "Destino",
                "evidence": [
                    "gateway_observation"
                ],
                "observed": {
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
                                        "!000000aa"
                                    ),
                                    "rx_time": 900,
                                    "snr_db": 5.25,
                                    "rssi_dbm": -81.0,
                                    "imported_at_us": 1001,
                                }
                            ],
                        }
                    ],
                },
                "traceroute": None,
            },
        )

    def test_traceroute_is_published_structurally(
        self,
    ) -> None:
        view = build_live_packet_view(
            packet(
                portnum=70,
                payload=(
                    "route: 3\n"
                    "snr_towards: -12\n"
                    "route_back: 4\n"
                    "snr_back: 8\n"
                ),
            ),
            (),
        )

        event = live_event_document(view)

        self.assertEqual(
            event["traceroute"],
            {
                "towards": [
                    "meshtastic:!00000001",
                    "meshtastic:!00000003",
                    "meshtastic:!00000002",
                ],
                "back": [
                    "meshtastic:!00000002",
                    "meshtastic:!00000004",
                    "meshtastic:!00000001",
                ],
                "snr_towards": [-12],
                "snr_back": [8],
            },
        )

    def test_empty_route_discovery_is_explicit(
        self,
    ) -> None:
        view = build_live_packet_view(
            packet(
                portnum=70,
                payload="",
            ),
            (),
        )

        event = live_event_document(view)

        self.assertEqual(
            event["traceroute"],
            {
                "towards": [],
                "back": [],
                "snr_towards": [],
                "snr_back": [],
            },
        )
        self.assertEqual(event["evidence"], [])

    def test_document_has_source_specific_cursor_state(
        self,
    ) -> None:
        document = build_live_document(
            [
                build_live_packet_view(
                    packet(),
                    (),
                )
            ],
            generated_at=GENERATED_AT,
            source_states={
                "ozulo_map": LiveSourceState(
                    previous_cursor=900,
                    next_cursor=1000,
                    possible_gap=False,
                )
            },
        )

        self.assertEqual(
            document["schema"],
            LIVE_SCHEMA_ID,
        )
        self.assertEqual(
            document["generated_at"],
            GENERATED_AT,
        )
        self.assertEqual(
            document["sources"],
            {
                "ozulo_map": {
                    "previous_cursor": 900,
                    "next_cursor": 1000,
                    "possible_gap": False,
                }
            },
        )

    def test_events_are_ordered_oldest_first(
        self,
    ) -> None:
        older = build_live_packet_view(
            packet(
                packet_id=1,
                imported_at_us=100,
            ),
            (),
        )
        newer = build_live_packet_view(
            packet(
                packet_id=2,
                imported_at_us=200,
            ),
            (),
        )

        document = build_live_document(
            [newer, older],
            generated_at=GENERATED_AT,
            source_states={},
        )

        self.assertEqual(
            [
                event["packet_id"]
                for event in document["events"]
            ],
            [1, 2],
        )

    def test_cursor_cannot_move_backwards(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "non pode retroceder",
        ):
            build_live_document(
                [],
                generated_at=GENERATED_AT,
                source_states={
                    "ozulo_map": LiveSourceState(
                        previous_cursor=200,
                        next_cursor=100,
                        possible_gap=False,
                    )
                },
            )

    def test_duplicate_events_are_rejected(
        self,
    ) -> None:
        view = build_live_packet_view(
            packet(),
            (),
        )

        with self.assertRaisesRegex(
            ValueError,
            "eventos live duplicados",
        ):
            build_live_document(
                [view, view],
                generated_at=GENERATED_AT,
                source_states={},
            )


if __name__ == "__main__":
    unittest.main()
