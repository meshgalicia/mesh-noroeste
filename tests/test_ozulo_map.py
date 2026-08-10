"""Probas do adaptador dos JSON consolidados de O Zulo."""

from __future__ import annotations

import unittest

from mesh_noroeste.ozulo_map import (
    OzuloMapError,
    parse_ozulo_map_edges,
    parse_ozulo_map_nodes,
    parse_ozulo_neighbor_packets,
)


def node_record() -> dict[str, object]:
    return {
        "node_id": "!70e4b96f",
        "first_seen": 1_782_661_488,
        "last_seen": 1_785_325_863,
        "updated_at": 1_785_325_864,
        "short_name": "ath0",
        "long_name": "ea2ath-0 😀",
        "hardware": "TRACKER_T1000_E",
        "role": "CLIENT",
        "latitude": 42.3493632,
        "longitude": -7.2482816,
        "altitude": 630,
        "precision_bits": 14,
        "battery_level": 76,
        "voltage": 4.02,
        "channel_util": 3.5,
        "air_util_tx": 1.2,
        "snr": 7.25,
        "rssi": -91,
        "channel": "LongFast",
        "firmware": "2.7.15",
        "hops_away": 2,
        "is_mqtt_gateway": 0,
    }


class OzuloMapTests(unittest.TestCase):
    def test_valid_node_is_normalized(self) -> None:
        observation = parse_ozulo_map_nodes(
            {"count": 1, "nodes": [node_record()]},
            source="ozulo_map",
        )[0]

        self.assertEqual(
            observation.id,
            "meshtastic:!70e4b96f",
        )
        self.assertEqual(observation.source, "ozulo_map")
        self.assertEqual(
            observation.first_seen,
            "2026-06-28T15:44:48Z",
        )
        self.assertEqual(
            observation.observed_at,
            "2026-07-29T11:51:03Z",
        )
        self.assertEqual(
            observation.position_updated_at,
            "2026-07-29T11:51:03Z",
        )
        self.assertEqual(observation.latitude, 42.3493632)
        self.assertEqual(observation.longitude, -7.2482816)
        self.assertEqual(observation.altitude_m, 630.0)
        self.assertEqual(
            observation.position_precision_bits,
            14,
        )
        self.assertEqual(
            observation.metrics["battery_percent"],
            76.0,
        )
        self.assertEqual(
            observation.radio["mqtt_gateway"],
            False,
        )

    def test_inconsistent_first_seen_is_omitted(self) -> None:
        item = node_record()
        item["first_seen"] = 1_785_325_900

        observation = parse_ozulo_map_nodes(
            {"nodes": [item]},
            source="ozulo_map",
        )[0]

        self.assertIsNone(observation.first_seen)
        self.assertEqual(
            observation.observed_at,
            "2026-07-29T11:51:03Z",
        )

    def test_node_without_position_is_accepted(self) -> None:
        item = node_record()
        item["latitude"] = None
        item["longitude"] = None
        item["altitude"] = None
        item["precision_bits"] = None

        observation = parse_ozulo_map_nodes(
            {"nodes": [item]},
            source="ozulo_map",
        )[0]

        self.assertIsNone(observation.latitude)
        self.assertIsNone(observation.longitude)
        self.assertIsNone(
            observation.position_updated_at
        )

    def test_precision_without_position_is_omitted(self) -> None:
        item = node_record()
        item["latitude"] = None
        item["longitude"] = None
        item["altitude"] = None
        item["precision_bits"] = 13

        observation = parse_ozulo_map_nodes(
            {"nodes": [item]},
            source="ozulo_map",
        )[0]

        self.assertIsNone(observation.latitude)
        self.assertIsNone(observation.longitude)
        self.assertIsNone(
            observation.position_precision_bits
        )
        self.assertIsNone(
            observation.position_updated_at
        )

    def test_invalid_node_root_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            OzuloMapError,
            "raíz.*obxecto",
        ):
            parse_ozulo_map_nodes(
                [],
                source="ozulo_map",
            )

    def test_neighbor_packets_preserve_history(self) -> None:
        observations = parse_ozulo_neighbor_packets(
            {
                "latest_import_time": 1_785_814_685,
                "packets": [
                    {
                        "id": 1,
                        "import_time_us": 1_785_793_084_412_839,
                        "from_node_id": 2_956_739_956,
                        "to_node_id": 1,
                        "portnum": 71,
                        "payload": (
                            "node_id: 2956739956\n"
                            "neighbors {\n"
                            "  node_id: 2905611713\n"
                            "  snr: 1.0\n"
                            "}\n"
                        ),
                    },
                    {
                        "id": 2,
                        "import_time_us": 1_785_814_685_059_745,
                        "from_node_id": 2_956_739_956,
                        "to_node_id": 1,
                        "portnum": 71,
                        "payload": (
                            "node_id: 2956739956\n"
                            "neighbors {\n"
                            "  node_id: 2905611713\n"
                            "  snr: 4.0\n"
                            "}\n"
                            "neighbors {\n"
                            "  node_id: 899165990\n"
                            "  snr: 6.75\n"
                            "}\n"
                        ),
                    },
                ],
            },
            source="ozulo_map",
        )

        self.assertEqual(len(observations), 3)
        self.assertEqual(
            [
                observation.observed_at
                for observation in observations
            ],
            [
                "2026-08-03T21:38:04Z",
                "2026-08-04T03:38:05Z",
                "2026-08-04T03:38:05Z",
            ],
        )
        self.assertEqual(
            [
                (
                    observation.from_source_id,
                    observation.to_source_id,
                    observation.snr_db,
                )
                for observation in observations
            ],
            [
                ("!b03c4574", "!ad301dc1", 1.0),
                ("!b03c4574", "!35982f26", 6.75),
                ("!b03c4574", "!ad301dc1", 4.0),
            ],
        )

    def test_duplicate_neighbor_in_packet_is_ignored(
        self,
    ) -> None:
        packet = {
            "import_time_us": 1_785_814_685_059_745,
            "from_node_id": 2_956_739_956,
            "portnum": 71,
            "payload": (
                "node_id: 2956739956\n"
                "neighbors { node_id: 2905611713 snr: 4.0 }\n"
                "neighbors { node_id: 2905611713 snr: 4.0 }\n"
            ),
        }

        observations = parse_ozulo_neighbor_packets(
            {"packets": [packet]},
            source="ozulo_map",
        )

        self.assertEqual(len(observations), 1)

    def test_neighbor_packet_emitter_mismatch_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            OzuloMapError,
            "non coincide",
        ):
            parse_ozulo_neighbor_packets(
                {
                    "packets": [{
                        "import_time_us": (
                            1_785_814_685_059_745
                        ),
                        "from_node_id": 2_956_739_956,
                        "portnum": 71,
                        "payload": (
                            "node_id: 2905611713\n"
                        ),
                    }]
                },
                source="ozulo_map",
            )

    def test_neighbor_without_snr_is_ignored(
        self,
    ) -> None:
        observations = parse_ozulo_neighbor_packets(
            {
                "packets": [{
                    "import_time_us": (
                        1_785_814_685_059_745
                    ),
                    "from_node_id": 2_956_739_956,
                    "portnum": 71,
                    "payload": (
                        "node_id: 2956739956\n"
                        "neighbors {\n"
                        "  node_id: 2905611713\n"
                        "}\n"
                        "neighbors {\n"
                        "  node_id: 899165990\n"
                        "  snr: 6.75\n"
                        "}\n"
                    ),
                }]
            },
            source="ozulo_map",
        )

        self.assertEqual(len(observations), 1)
        self.assertEqual(
            observations[0].from_source_id,
            "!b03c4574",
        )
        self.assertEqual(
            observations[0].to_source_id,
            "!35982f26",
        )
        self.assertEqual(
            observations[0].snr_db,
            6.75,
        )

    def test_traceroute_edge_is_normalized(self) -> None:
        edges = parse_ozulo_map_edges(
            {
                "edges": [
                    {
                        "from_node": "!157fb546",
                        "to_node": "!9e780100",
                        "edge_type": "traceroute",
                        "last_seen": 1_785_325_865,
                        "snr": 5.75,
                    }
                ]
            },
            source="ozulo_map",
        )

        self.assertEqual(len(edges), 1)
        edge = edges[0]
        self.assertEqual(edge.source, "ozulo_map")
        self.assertEqual(edge.from_source_id, "!157fb546")
        self.assertEqual(edge.to_source_id, "!9e780100")
        self.assertEqual(edge.edge_type, "traceroute")
        self.assertIs(edge.directed, True)
        self.assertEqual(
            edge.observed_at,
            "2026-07-29T11:51:05Z",
        )
        self.assertEqual(edge.metrics["snr_db"], 5.75)

    def test_latest_duplicate_edge_is_kept(self) -> None:
        edges = parse_ozulo_map_edges(
            {
                "edges": [
                    {
                        "from_node": "!157fb546",
                        "to_node": "!9e780100",
                        "edge_type": "traceroute",
                        "last_seen": 1_785_325_800,
                        "snr": None,
                    },
                    {
                        "from_node": "!157fb546",
                        "to_node": "!9e780100",
                        "edge_type": "traceroute",
                        "last_seen": 1_785_325_865,
                        "snr": 4.0,
                    },
                ]
            },
            source="ozulo_map",
        )

        self.assertEqual(len(edges), 1)
        self.assertEqual(
            edges[0].observed_at,
            "2026-07-29T11:51:05Z",
        )
        self.assertEqual(edges[0].metrics["snr_db"], 4.0)


if __name__ == "__main__":
    unittest.main()
