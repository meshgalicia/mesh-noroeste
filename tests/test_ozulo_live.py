"""Probas do adaptador live de O Zulo."""

from __future__ import annotations

import unittest

from mesh_noroeste.ozulo_live import (
    OzuloLiveError,
    parse_ozulo_live_packets,
    parse_ozulo_live_receptions,
)


class OzuloLiveTests(unittest.TestCase):
    def test_packet_is_normalized(self) -> None:
        packet = parse_ozulo_live_packets(
            {
                "latest_import_time": 1786869415119829,
                "packets": [
                    {
                        "id": 1428774103,
                        "import_time_us": 1786869415119829,
                        "channel": "LongFast",
                        "from_node_id": 3966556642,
                        "to_node_id": 4294967295,
                        "portnum": 3,
                        "long_name": "WIO L1 ALFA-CHE",
                        "payload": "latitude_i: 432996352",
                        "to_long_name": "",
                    }
                ],
            }
        )[0]

        self.assertEqual(packet.packet_id, 1428774103)
        self.assertEqual(
            packet.from_source_id,
            "!ec6cd9e2",
        )
        self.assertEqual(
            packet.to_source_id,
            "!ffffffff",
        )
        self.assertEqual(packet.portnum, 3)
        self.assertEqual(packet.channel, "LongFast")
        self.assertEqual(
            packet.imported_at_us,
            1786869415119829,
        )
        self.assertEqual(
            packet.long_name,
            "WIO L1 ALFA-CHE",
        )
        self.assertIsNone(packet.to_long_name)
        self.assertEqual(
            packet.id,
            "meshtastic:live_packet:"
            "1428774103:!ec6cd9e2",
        )

    def test_receptions_are_normalized(self) -> None:
        receptions = parse_ozulo_live_receptions(
            {
                "seen": [
                    {
                        "packet_id": 1213616148,
                        "node_id": 2956739956,
                        "rx_time": 1786871092,
                        "hop_limit": 0,
                        "hop_start": 4,
                        "channel": "LongFast",
                        "rx_snr": 4.25,
                        "rx_rssi": -96,
                        "topic": (
                            "msh/EU_868/2/e/"
                            "LongFast/!b03c4574"
                        ),
                        "import_time_us": 1786871130735628,
                    },
                    {
                        "packet_id": 1213616148,
                        "node_id": 2697758372,
                        "rx_time": 1786871089,
                        "hop_limit": 1,
                        "hop_start": 4,
                        "channel": "LongFast",
                        "rx_snr": 5.5,
                        "rx_rssi": -59,
                        "topic": (
                            "msh/EU_868/2/e/"
                            "LongFast/!a0cc86a4"
                        ),
                        "import_time_us": 1786871127730549,
                    },
                ]
            },
            packet_id=1213616148,
            from_source_id=3726181341,
        )

        self.assertEqual(len(receptions), 2)
        self.assertEqual(
            receptions[0].gateway_source_id,
            "!b03c4574",
        )
        self.assertEqual(receptions[0].hop_limit, 0)
        self.assertEqual(receptions[0].hop_start, 4)
        self.assertEqual(receptions[0].snr_db, 4.25)
        self.assertEqual(receptions[0].rssi_dbm, -96.0)
        self.assertEqual(
            receptions[1].gateway_source_id,
            "!a0cc86a4",
        )

    def test_reception_identity_includes_packet_origin(self) -> None:
        document = {
            "seen": [
                {
                    "packet_id": 99,
                    "node_id": 2956739956,
                    "rx_time": 1,
                    "hop_limit": 1,
                    "hop_start": 3,
                    "import_time_us": 100,
                }
            ]
        }

        first = parse_ozulo_live_receptions(
            document,
            packet_id=99,
            from_source_id=1,
        )[0]
        second = parse_ozulo_live_receptions(
            document,
            packet_id=99,
            from_source_id=2,
        )[0]

        self.assertNotEqual(first.id, second.id)
        self.assertEqual(first.from_source_id, "!00000001")
        self.assertEqual(second.from_source_id, "!00000002")

    def test_packet_id_mismatch_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            OzuloLiveError,
            "packet_id non coincide",
        ):
            parse_ozulo_live_receptions(
                {
                    "seen": [
                        {
                            "packet_id": 2,
                            "node_id": 1,
                            "rx_time": 1,
                            "hop_limit": 1,
                            "hop_start": 1,
                            "import_time_us": 2,
                        }
                    ]
                },
                packet_id=1,
                from_source_id=10,
            )

    def test_invalid_packet_root_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            OzuloLiveError,
            "raíz.*obxecto",
        ):
            parse_ozulo_live_packets([])

    def test_invalid_reception_root_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            OzuloLiveError,
            "raíz.*obxecto",
        ):
            parse_ozulo_live_receptions(
                [],
                packet_id=1,
                from_source_id=10,
            )


if __name__ == "__main__":
    unittest.main()
