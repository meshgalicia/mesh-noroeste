"""Probas do adaptador dos JSON consolidados de O Zulo."""

from __future__ import annotations

import unittest

from mesh_noroeste.ozulo_map import (
    OzuloMapError,
    parse_ozulo_map_edges,
    parse_ozulo_map_nodes,
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

    def test_invalid_node_root_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            OzuloMapError,
            "raíz.*obxecto",
        ):
            parse_ozulo_map_nodes(
                [],
                source="ozulo_map",
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
