"""Pruebas del adaptador de Meshview España."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest

from mesh_noroeste.meshview_es import (
    MeshviewEsError,
    parse_meshview_es,
    parse_meshview_es_position_precisions,
    parse_meshview_es_edges,
)


FIRST_SEEN = datetime(
    2026,
    7,
    20,
    9,
    10,
    tzinfo=timezone.utc,
)
LAST_SEEN = datetime(
    2026,
    7,
    25,
    11,
    58,
    tzinfo=timezone.utc,
)


def microseconds(value: datetime) -> int:
    return int(value.timestamp() * 1_000_000)


def record() -> dict[str, object]:
    return {
        "id": "!0123abcd",
        "node_id": int("0123abcd", 16),
        "first_seen_us": microseconds(FIRST_SEEN),
        "last_seen_us": microseconds(LAST_SEEN),
        "short_name": " BRMA ",
        "long_name": " Bruma Connection ",
        "hw_model": " HELTEC_V4 ",
        "role": " CLIENT_MUTE ",
        "last_lat": 431_000_000,
        "last_long": -81_000_000,
        "channel": " LongFast ",
        "firmware": " 2.7.15 ",
        "is_mqtt_gateway": False,
    }


class MeshviewEsTests(unittest.TestCase):
    def test_valid_record_is_normalized(self) -> None:
        observations = parse_meshview_es(
            {"nodes": [record()]}
        )

        self.assertEqual(len(observations), 1)

        observation = observations[0]

        self.assertEqual(
            observation.id,
            "meshtastic:!0123abcd",
        )
        self.assertEqual(
            observation.source,
            "meshview_es",
        )
        self.assertEqual(
            observation.network,
            "meshtastic",
        )
        self.assertEqual(observation.short_name, "BRMA")
        self.assertEqual(
            observation.long_name,
            "Bruma Connection",
        )
        self.assertEqual(
            observation.hardware,
            "HELTEC_V4",
        )
        self.assertEqual(
            observation.role,
            "CLIENT_MUTE",
        )
        self.assertEqual(
            observation.first_seen,
            "2026-07-20T09:10:00Z",
        )
        self.assertEqual(
            observation.observed_at,
            "2026-07-25T11:58:00Z",
        )
        self.assertEqual(observation.latitude, 43.1)
        self.assertEqual(observation.longitude, -8.1)
        self.assertEqual(
            observation.position_updated_at,
            "2026-07-25T11:58:00Z",
        )
        self.assertEqual(
            observation.radio["channel"],
            "LongFast",
        )
        self.assertEqual(
            observation.radio["firmware"],
            "2.7.15",
        )
        self.assertIs(
            observation.radio["mqtt_gateway"],
            False,
        )

    def test_node_source_can_be_parameterized(self) -> None:
        observation = parse_meshview_es(
            {"nodes": [record()]},
            source=" MALHA_PT ",
        )[0]

        self.assertEqual(observation.source, "malha_pt")

    def test_missing_position_is_accepted(self) -> None:
        item = record()
        item["last_lat"] = None
        item["last_long"] = None

        observation = parse_meshview_es(
            {"nodes": [item]}
        )[0]

        self.assertIsNone(observation.latitude)
        self.assertIsNone(observation.longitude)
        self.assertIsNone(
            observation.position_updated_at
        )

    def test_id_mismatch_is_rejected(self) -> None:
        item = record()
        item["node_id"] = int("0123abce", 16)

        with self.assertRaisesRegex(
            MeshviewEsError,
            "id y node_id",
        ):
            parse_meshview_es({"nodes": [item]})

    def test_invalid_root_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            MeshviewEsError,
            "raíz.*objeto",
        ):
            parse_meshview_es([])

    def test_missing_nodes_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            MeshviewEsError,
            "no contiene 'nodes'",
        ):
            parse_meshview_es({})

    def test_non_object_record_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            MeshviewEsError,
            "Registro 0.*objeto",
        ):
            parse_meshview_es({"nodes": [None]})

    def test_partial_coordinates_are_rejected(
        self,
    ) -> None:
        item = record()
        item["last_long"] = None

        with self.assertRaisesRegex(
            MeshviewEsError,
            "deben aparecer juntos",
        ):
            parse_meshview_es({"nodes": [item]})

    def test_duplicate_id_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            MeshviewEsError,
            "id duplicado",
        ):
            parse_meshview_es(
                {"nodes": [record(), record()]}
            )

    def test_invalid_timestamp_is_rejected(
        self,
    ) -> None:
        item = record()
        item["first_seen_us"] = True

        with self.assertRaisesRegex(
            MeshviewEsError,
            "first_seen_us",
        ):
            parse_meshview_es({"nodes": [item]})


    def test_position_precision_uses_latest_packet(
        self,
    ) -> None:
        node_id = int("0123abcd", 16)

        precisions = parse_meshview_es_position_precisions(
            {
                "packets": [
                    {
                        "from_node_id": node_id,
                        "import_time_us": microseconds(
                            FIRST_SEEN
                        ),
                        "payload": (
                            "latitude_i: 431000000\n"
                            "longitude_i: -81000000\n"
                            "precision_bits: 13"
                        ),
                    },
                    {
                        "from_node_id": node_id,
                        "import_time_us": microseconds(
                            LAST_SEEN
                        ),
                        "payload": (
                            "latitude_i: 431000000\n"
                            "longitude_i: -81000000\n"
                            "precision_bits: 18"
                        ),
                    },
                ]
            }
        )

        precision = precisions["!0123abcd"]

        self.assertEqual(precision.latitude_i, 431_000_000)
        self.assertEqual(precision.longitude_i, -81_000_000)
        self.assertEqual(precision.precision_bits, 18)
        self.assertEqual(
            precision.import_time_us,
            microseconds(LAST_SEEN),
        )

    def test_packet_without_precision_is_ignored(
        self,
    ) -> None:
        precisions = parse_meshview_es_position_precisions(
            {
                "packets": [
                    {
                        "from_node_id": int(
                            "0123abcd",
                            16,
                        ),
                        "import_time_us": microseconds(
                            LAST_SEEN
                        ),
                        "payload": (
                            "latitude_i: 431000000\n"
                            "longitude_i: -81000000"
                        ),
                    }
                ]
            }
        )

        self.assertEqual(precisions, {})


    def test_precision_is_attached_only_to_matching_position(
        self,
    ) -> None:
        node_id = int("0123abcd", 16)
        precisions = parse_meshview_es_position_precisions(
            {
                "packets": [
                    {
                        "from_node_id": node_id,
                        "import_time_us": microseconds(
                            LAST_SEEN
                        ),
                        "payload": (
                            "latitude_i: 431000000\n"
                            "longitude_i: -81000000\n"
                            "precision_bits: 18"
                        ),
                    }
                ]
            }
        )

        matching = parse_meshview_es(
            {"nodes": [record()]},
            position_precisions=precisions,
        )[0]

        self.assertEqual(
            matching.position_precision_bits,
            18,
        )

        changed = record()
        changed["last_lat"] = 432_000_000

        mismatching = parse_meshview_es(
            {"nodes": [changed]},
            position_precisions=precisions,
        )[0]

        self.assertIsNone(
            mismatching.position_precision_bits
        )

    def test_traceroute_edge_is_normalized(self) -> None:
        observed_at = datetime(
            2026,
            7,
            26,
            15,
            31,
            tzinfo=timezone.utc,
        )

        edges = parse_meshview_es_edges(
            {
                "edges": [
                    {
                        "from": int("761467c0", 16),
                        "to": int("0123abcd", 16),
                        "type": "traceroute",
                    }
                ]
            },
            edge_type="traceroute",
            observed_at=observed_at,
        )

        self.assertEqual(len(edges), 1)
        edge = edges[0]
        self.assertEqual(edge.source, "meshview_es")
        self.assertEqual(edge.network, "meshtastic")
        self.assertEqual(edge.from_source_id, "!761467c0")
        self.assertEqual(edge.to_source_id, "!0123abcd")
        self.assertEqual(edge.edge_type, "traceroute")
        self.assertIs(edge.directed, True)
        self.assertEqual(
            edge.observed_at,
            "2026-07-26T15:31:00Z",
        )

    def test_edge_source_can_be_parameterized(self) -> None:
        edges = parse_meshview_es_edges(
            {
                "edges": [
                    {
                        "from": int("761467c0", 16),
                        "to": int("0123abcd", 16),
                        "type": "traceroute",
                    }
                ]
            },
            edge_type="traceroute",
            observed_at=LAST_SEEN,
            source=" MALHA_PT ",
        )

        self.assertEqual(edges[0].source, "malha_pt")

    def test_self_edge_is_discarded(self) -> None:
        edges = parse_meshview_es_edges(
            {
                "edges": [
                    {
                        "from": int("761467c0", 16),
                        "to": int("761467c0", 16),
                        "type": "traceroute",
                    }
                ]
            },
            edge_type="traceroute",
            observed_at=LAST_SEEN,
        )

        self.assertEqual(edges, ())

    def test_reciprocal_neighbors_are_deduplicated(
        self,
    ) -> None:
        edges = parse_meshview_es_edges(
            {
                "edges": [
                    {
                        "from": int("761467c0", 16),
                        "to": int("0123abcd", 16),
                        "type": "neighbor",
                    },
                    {
                        "from": int("0123abcd", 16),
                        "to": int("761467c0", 16),
                        "type": "neighbor",
                    },
                ]
            },
            edge_type="neighbor",
            observed_at=LAST_SEEN,
        )

        self.assertEqual(len(edges), 1)
        self.assertIs(edges[0].directed, False)
        self.assertEqual(
            {
                edges[0].from_source_id,
                edges[0].to_source_id,
            },
            {"!761467c0", "!0123abcd"},
        )

    def test_reciprocal_traceroutes_are_preserved(
        self,
    ) -> None:
        edges = parse_meshview_es_edges(
            {
                "edges": [
                    {
                        "from": int("761467c0", 16),
                        "to": int("0123abcd", 16),
                        "type": "traceroute",
                    },
                    {
                        "from": int("0123abcd", 16),
                        "to": int("761467c0", 16),
                        "type": "traceroute",
                    },
                ]
            },
            edge_type="traceroute",
            observed_at=LAST_SEEN,
        )

        self.assertEqual(len(edges), 2)
        self.assertEqual(
            {
                (
                    edge.from_source_id,
                    edge.to_source_id,
                )
                for edge in edges
            },
            {
                ("!761467c0", "!0123abcd"),
                ("!0123abcd", "!761467c0"),
            },
        )


if __name__ == "__main__":
    unittest.main()
