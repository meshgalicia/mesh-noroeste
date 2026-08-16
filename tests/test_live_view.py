"""Probas da vista unificada do tráfico Meshtastic en directo."""

from __future__ import annotations

import unittest

from mesh_noroeste.domain import (
    MeshtasticLivePacket,
    MeshtasticLiveReception,
)
from mesh_noroeste.live_view import (
    build_live_packet_view,
)


def packet(
    *,
    portnum: int = 3,
    payload: str = "",
    to_source_id: str = "!00000002",
) -> MeshtasticLivePacket:
    return MeshtasticLivePacket(
        source="ozulo_map",
        packet_id=100,
        from_source_id="!00000001",
        to_source_id=to_source_id,
        portnum=portnum,
        channel="LongFast",
        imported_at_us=1000,
        long_name="Orixe",
        to_long_name="Destino",
        payload=payload,
    )


def reception(
    *,
    gateway: str = "!000000aa",
    hop_limit: int = 2,
    hop_start: int | None = 3,
) -> MeshtasticLiveReception:
    return MeshtasticLiveReception(
        source="ozulo_map",
        packet_id=100,
        from_source_id="!00000001",
        gateway_source_id=gateway,
        rx_time=10,
        hop_limit=hop_limit,
        hop_start=hop_start,
        snr_db=5.0,
        rssi_dbm=-80.0,
        channel="LongFast",
        topic=None,
        imported_at_us=1001,
    )


class LivePacketViewTests(unittest.TestCase):
    def test_regular_packet_keeps_gateway_evidence_only(
        self,
    ) -> None:
        result = build_live_packet_view(
            packet(),
            (reception(),),
        )

        self.assertTrue(
            result.has_gateway_observations
        )
        self.assertFalse(result.has_traceroute)
        self.assertIsNone(result.traceroute)
        self.assertEqual(
            result.evidence_types,
            ("gateway_observation",),
        )

    def test_traceroute_and_gateway_evidence_remain_separate(
        self,
    ) -> None:
        result = build_live_packet_view(
            packet(
                portnum=70,
                payload=(
                    "route: 3\n"
                    "snr_towards: -12\n"
                    "route_back: 4\n"
                    "snr_back: 8\n"
                ),
            ),
            (
                reception(
                    gateway="!000000aa",
                    hop_limit=2,
                ),
                reception(
                    gateway="!000000bb",
                    hop_limit=1,
                ),
            ),
        )

        self.assertEqual(
            result.observed_path.observed_gateway_count,
            2,
        )
        self.assertIsNotNone(result.traceroute)
        assert result.traceroute is not None

        self.assertEqual(
            result.traceroute.towards,
            (
                "!00000001",
                "!00000003",
                "!00000002",
            ),
        )
        self.assertEqual(
            result.traceroute.back,
            (
                "!00000002",
                "!00000004",
                "!00000001",
            ),
        )
        self.assertEqual(
            result.evidence_types,
            (
                "gateway_observation",
                "traceroute",
            ),
        )

    def test_empty_traceroute_payload_is_not_invented(
        self,
    ) -> None:
        result = build_live_packet_view(
            packet(
                portnum=70,
                payload="",
            ),
            (reception(),),
        )

        self.assertIsNotNone(result.traceroute)
        assert result.traceroute is not None

        self.assertEqual(
            result.traceroute.towards,
            (),
        )
        self.assertEqual(
            result.traceroute.back,
            (),
        )
        self.assertFalse(result.has_traceroute)
        self.assertEqual(
            result.evidence_types,
            ("gateway_observation",),
        )

    def test_packet_without_receptions_is_valid(
        self,
    ) -> None:
        result = build_live_packet_view(
            packet(),
            (),
        )

        self.assertFalse(
            result.has_gateway_observations
        )
        self.assertEqual(
            result.observed_path.stages,
            (),
        )
        self.assertEqual(result.evidence_types, ())

    def test_traceroute_without_gateway_receptions_is_valid(
        self,
    ) -> None:
        result = build_live_packet_view(
            packet(
                portnum=70,
                payload="route: 3\nsnr_towards: -12",
            ),
            (),
        )

        self.assertFalse(
            result.has_gateway_observations
        )
        self.assertTrue(result.has_traceroute)
        self.assertEqual(
            result.evidence_types,
            ("traceroute",),
        )

    def test_reception_from_another_origin_is_rejected(
        self,
    ) -> None:
        wrong = MeshtasticLiveReception(
            source="ozulo_map",
            packet_id=100,
            from_source_id="!00000099",
            gateway_source_id="!000000aa",
            rx_time=10,
            hop_limit=2,
            hop_start=3,
            snr_db=5.0,
            rssi_dbm=-80.0,
            channel="LongFast",
            topic=None,
            imported_at_us=1001,
        )

        with self.assertRaisesRegex(
            ValueError,
            "outro nodo de orixe",
        ):
            build_live_packet_view(
                packet(),
                (wrong,),
            )


if __name__ == "__main__":
    unittest.main()
