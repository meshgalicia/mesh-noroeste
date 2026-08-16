"""Probas da interpretación conservadora do tránsito live."""

from __future__ import annotations

import unittest

from mesh_noroeste.domain import (
    MeshtasticLivePacket,
    MeshtasticLiveReception,
)
from mesh_noroeste.live_path import build_observed_path


def packet() -> MeshtasticLivePacket:
    return MeshtasticLivePacket(
        source="ozulo_map",
        packet_id=100,
        from_source_id="!00000001",
        to_source_id="!ffffffff",
        portnum=3,
        channel="LongFast",
        imported_at_us=1000,
        long_name="Nodo",
        to_long_name=None,
        payload="",
    )


def reception(
    *,
    gateway: str,
    hop_limit: int,
    hop_start: int | None = 3,
    rx_time: int = 10,
    imported_at_us: int = 1000,
) -> MeshtasticLiveReception:
    return MeshtasticLiveReception(
        source="ozulo_map",
        packet_id=100,
        from_source_id="!00000001",
        gateway_source_id=gateway,
        rx_time=rx_time,
        hop_limit=hop_limit,
        hop_start=hop_start,
        snr_db=5.0,
        rssi_dbm=-80.0,
        channel="LongFast",
        topic=None,
        imported_at_us=imported_at_us,
    )


class LivePathTests(unittest.TestCase):
    def test_groups_same_hop_into_one_stage(self) -> None:
        result = build_observed_path(
            packet(),
            (
                reception(
                    gateway="!000000aa",
                    hop_limit=2,
                ),
                reception(
                    gateway="!000000bb",
                    hop_limit=2,
                ),
            ),
        )

        self.assertEqual(result.observed_stage_count, 1)
        self.assertEqual(result.observed_gateway_count, 2)
        self.assertEqual(
            [
                item.gateway_source_id
                for item in result.stages[0].gateways
            ],
            [
                "!000000aa",
                "!000000bb",
            ],
        )

    def test_stages_are_ordered_from_higher_hop_limit(
        self,
    ) -> None:
        result = build_observed_path(
            packet(),
            (
                reception(
                    gateway="!000000cc",
                    hop_limit=1,
                ),
                reception(
                    gateway="!000000aa",
                    hop_limit=3,
                ),
                reception(
                    gateway="!000000bb",
                    hop_limit=2,
                ),
            ),
        )

        self.assertEqual(
            [
                stage.hop_limit
                for stage in result.stages
            ],
            [3, 2, 1],
        )

        self.assertEqual(
            [
                stage.hops_used
                for stage in result.stages
            ],
            [0, 1, 2],
        )

    def test_missing_hop_start_keeps_hops_unknown(
        self,
    ) -> None:
        result = build_observed_path(
            packet(),
            (
                reception(
                    gateway="!000000aa",
                    hop_limit=2,
                    hop_start=None,
                ),
            ),
        )

        self.assertIsNone(
            result.stages[0].hops_used
        )

    def test_other_packet_is_rejected(self) -> None:
        wrong = reception(
            gateway="!000000aa",
            hop_limit=2,
        )

        wrong = MeshtasticLiveReception(
            source=wrong.source,
            packet_id=999,
            from_source_id=wrong.from_source_id,
            gateway_source_id=wrong.gateway_source_id,
            rx_time=wrong.rx_time,
            hop_limit=wrong.hop_limit,
            hop_start=wrong.hop_start,
            snr_db=wrong.snr_db,
            rssi_dbm=wrong.rssi_dbm,
            channel=wrong.channel,
            topic=wrong.topic,
            imported_at_us=wrong.imported_at_us,
        )

        with self.assertRaisesRegex(
            ValueError,
            "outro packet_id",
        ):
            build_observed_path(
                packet(),
                (wrong,),
            )

    def test_other_origin_is_rejected(self) -> None:
        wrong = reception(
            gateway="!000000aa",
            hop_limit=2,
        )

        wrong = MeshtasticLiveReception(
            source=wrong.source,
            packet_id=wrong.packet_id,
            from_source_id="!00000002",
            gateway_source_id=wrong.gateway_source_id,
            rx_time=wrong.rx_time,
            hop_limit=wrong.hop_limit,
            hop_start=wrong.hop_start,
            snr_db=wrong.snr_db,
            rssi_dbm=wrong.rssi_dbm,
            channel=wrong.channel,
            topic=wrong.topic,
            imported_at_us=wrong.imported_at_us,
        )

        with self.assertRaisesRegex(
            ValueError,
            "outro nodo de orixe",
        ):
            build_observed_path(
                packet(),
                (wrong,),
            )


if __name__ == "__main__":
    unittest.main()
