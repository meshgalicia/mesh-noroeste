"""Pruebas del adaptador de nodos de Malha Portugal."""
from __future__ import annotations

from datetime import datetime, timezone
import unittest

from mesh_noroeste.malha_pt import (
    MalhaPtError,
    parse_malha_pt,
    parse_malha_pt_traceroutes,
)


OBSERVED_AT = datetime(
    2026,
    7,
    25,
    11,
    58,
    tzinfo=timezone.utc,
)


def record() -> dict[str, object]:
    return {
        "node_id": int("0123abcd", 16),
        "hex_id": "!0123abcd",
        "timestamp": OBSERVED_AT.timestamp(),
        "latitude": 43.1,
        "longitude": -8.1,
        "altitude": 120,
        "short_name": " BRMA ",
        "long_name": " Bruma Connection ",
        "hw_model": " HELTEC_V4 ",
        "role": " CLIENT_MUTE ",
        "avg_snr": 7.25,
        "primary_channel": " LongFast ",
    }


class MalhaPtTests(unittest.TestCase):
    def test_valid_record_is_normalized(self) -> None:
        observations = parse_malha_pt(
            {"locations": [record()]}
        )

        self.assertEqual(len(observations), 1)

        observation = observations[0]

        self.assertEqual(
            observation.id,
            "meshtastic:!0123abcd",
        )
        self.assertEqual(
            observation.source,
            "malha_pt",
        )
        self.assertEqual(
            observation.network,
            "meshtastic",
        )
        self.assertEqual(
            observation.short_name,
            "BRMA",
        )
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
        self.assertIsNone(observation.first_seen)
        self.assertEqual(
            observation.observed_at,
            "2026-07-25T11:58:00Z",
        )
        self.assertEqual(observation.latitude, 43.1)
        self.assertEqual(observation.longitude, -8.1)
        self.assertEqual(observation.altitude_m, 120.0)
        self.assertEqual(
            observation.position_updated_at,
            "2026-07-25T11:58:00Z",
        )
        self.assertEqual(
            observation.metrics["snr_db"],
            7.25,
        )
        self.assertEqual(
            observation.radio["channel"],
            "LongFast",
        )

    def test_nullable_metadata_is_accepted(self) -> None:
        item = record()
        item["short_name"] = None
        item["long_name"] = None
        item["hw_model"] = None
        item["role"] = None
        item["altitude"] = None
        item["avg_snr"] = None
        item["primary_channel"] = None

        observation = parse_malha_pt(
            {"locations": [item]}
        )[0]

        self.assertIsNone(observation.short_name)
        self.assertIsNone(observation.long_name)
        self.assertIsNone(observation.hardware)
        self.assertIsNone(observation.role)
        self.assertIsNone(observation.altitude_m)
        self.assertIsNone(
            observation.metrics["snr_db"]
        )
        self.assertIsNone(
            observation.radio["channel"]
        )

    def test_invalid_root_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            MalhaPtError,
            "raíz.*objeto",
        ):
            parse_malha_pt([])

    def test_missing_locations_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            MalhaPtError,
            "no contiene 'locations'",
        ):
            parse_malha_pt({})

    def test_non_object_record_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            MalhaPtError,
            "Registro 0.*objeto",
        ):
            parse_malha_pt(
                {"locations": [None]}
            )

    def test_id_mismatch_is_rejected(self) -> None:
        item = record()
        item["node_id"] = int("0123abce", 16)

        with self.assertRaisesRegex(
            MalhaPtError,
            "hex_id y node_id",
        ):
            parse_malha_pt(
                {"locations": [item]}
            )

    def test_duplicate_id_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            MalhaPtError,
            "id duplicado",
        ):
            parse_malha_pt(
                {
                    "locations": [
                        record(),
                        record(),
                    ]
                }
            )

    def test_invalid_timestamp_is_rejected(
        self,
    ) -> None:
        item = record()
        item["timestamp"] = True

        with self.assertRaisesRegex(
            MalhaPtError,
            "timestamp",
        ):
            parse_malha_pt(
                {"locations": [item]}
            )

    def test_invalid_coordinates_are_rejected(
        self,
    ) -> None:
        item = record()
        item["latitude"] = 91

        with self.assertRaisesRegex(
            MalhaPtError,
            "latitude.*fuera de rango",
        ):
            parse_malha_pt(
                {"locations": [item]}
            )

    def test_zero_zero_is_rejected(self) -> None:
        item = record()
        item["latitude"] = 0
        item["longitude"] = 0

        with self.assertRaisesRegex(
            MalhaPtError,
            "0,0",
        ):
            parse_malha_pt(
                {"locations": [item]}
            )

    def test_missing_required_field_is_rejected(
        self,
    ) -> None:
        item = record()
        del item["primary_channel"]

        with self.assertRaisesRegex(
            MalhaPtError,
            "falta el campo 'primary_channel'",
        ):
            parse_malha_pt(
                {"locations": [item]}
            )


class MalhaPtTracerouteTests(unittest.TestCase):
    def traceroute(
        self,
        *,
        from_node_id: int = 0x0123ABCD,
        to_node_id: int = 0x89ABCDEF,
        last_seen: float | None = None,
    ) -> dict[str, object]:
        return {
            "from_node_id": from_node_id,
            "to_node_id": to_node_id,
            "last_seen": (
                OBSERVED_AT.timestamp()
                if last_seen is None
                else last_seen
            ),
            "avg_snr": 6.5,
            "is_bidirectional": True,
            "success_rate": 100,
            "total_hops_seen": 2,
        }

    def test_valid_traceroute_is_normalized(
        self,
    ) -> None:
        edges = parse_malha_pt_traceroutes(
            {
                "traceroute_links": [
                    self.traceroute()
                ]
            }
        )

        self.assertEqual(len(edges), 1)

        edge = edges[0]

        self.assertEqual(edge.source, "malha_pt")
        self.assertEqual(edge.network, "meshtastic")
        self.assertEqual(
            edge.from_source_id,
            "!0123abcd",
        )
        self.assertEqual(
            edge.to_source_id,
            "!89abcdef",
        )
        self.assertEqual(
            edge.from_id,
            "meshtastic:!0123abcd",
        )
        self.assertEqual(
            edge.to_id,
            "meshtastic:!89abcdef",
        )
        self.assertEqual(
            edge.id,
            (
                "meshtastic:traceroute:"
                "!0123abcd:!89abcdef"
            ),
        )
        self.assertEqual(edge.edge_type, "traceroute")
        self.assertTrue(edge.directed)
        self.assertEqual(
            edge.observed_at,
            "2026-07-25T11:58:00Z",
        )
        self.assertEqual(
            edge.metrics,
            {
                "snr_db": 6.5,
                "rssi_dbm": None,
            },
        )

    def test_reciprocal_routes_remain_distinct(
        self,
    ) -> None:
        first = self.traceroute(
            from_node_id=0x0123ABCD,
            to_node_id=0x89ABCDEF,
        )
        second = self.traceroute(
            from_node_id=0x89ABCDEF,
            to_node_id=0x0123ABCD,
        )

        edges = parse_malha_pt_traceroutes(
            {
                "traceroute_links": [
                    first,
                    second,
                ]
            }
        )

        self.assertEqual(len(edges), 2)
        self.assertNotEqual(edges[0].id, edges[1].id)

    def test_self_link_is_discarded(self) -> None:
        edges = parse_malha_pt_traceroutes(
            {
                "traceroute_links": [
                    self.traceroute(
                        from_node_id=0x0123ABCD,
                        to_node_id=0x0123ABCD,
                    )
                ]
            }
        )

        self.assertEqual(edges, ())

    def test_duplicate_directed_route_is_rejected(
        self,
    ) -> None:
        item = self.traceroute()

        with self.assertRaisesRegex(
            MalhaPtError,
            "conexión duplicada",
        ):
            parse_malha_pt_traceroutes(
                {
                    "traceroute_links": [
                        item,
                        dict(item),
                    ]
                }
            )

    def test_missing_traceroute_links_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            MalhaPtError,
            "no contiene 'traceroute_links'",
        ):
            parse_malha_pt_traceroutes({})

    def test_non_list_traceroutes_are_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            MalhaPtError,
            "debe ser una lista",
        ):
            parse_malha_pt_traceroutes(
                {"traceroute_links": {}}
            )

    def test_non_object_traceroute_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            MalhaPtError,
            "Traceroute 0.*objeto",
        ):
            parse_malha_pt_traceroutes(
                {"traceroute_links": [None]}
            )

    def test_invalid_endpoint_is_rejected(
        self,
    ) -> None:
        item = self.traceroute()
        item["from_node_id"] = True

        with self.assertRaisesRegex(
            MalhaPtError,
            "from_node_id",
        ):
            parse_malha_pt_traceroutes(
                {"traceroute_links": [item]}
            )

    def test_invalid_last_seen_is_rejected(
        self,
    ) -> None:
        item = self.traceroute()
        item["last_seen"] = True

        with self.assertRaisesRegex(
            MalhaPtError,
            "last_seen",
        ):
            parse_malha_pt_traceroutes(
                {"traceroute_links": [item]}
            )

    def test_nullable_snr_is_accepted(self) -> None:
        item = self.traceroute()
        item["avg_snr"] = None

        edge = parse_malha_pt_traceroutes(
            {"traceroute_links": [item]}
        )[0]

        self.assertIsNone(edge.metrics["snr_db"])


if __name__ == "__main__":
    unittest.main()
