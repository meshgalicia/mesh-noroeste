"""Probas do adaptador de nodos de MeshCore Hub."""

from __future__ import annotations

import unittest

from mesh_noroeste.meshcore_hub import (
    MeshCoreHubError,
    parse_meshcore_hub_advertisements,
    parse_meshcore_hub_nodes,
    parse_meshcore_hub_packet_group_edges,
)


PUBLIC_KEY = "01" * 32


def node(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "public_key": PUBLIC_KEY,
        "name": " Repetidor do Hub ",
        "adv_type": "repeater",
        "flags": 146,
        "first_seen": "2026-08-05T08:30:00Z",
        "last_seen": "2026-08-05T08:36:06.483384Z",
        "lat": 43.1,
        "lon": -8.1,
        "is_observer": False,
        "created_at": "2026-08-05T08:30:00Z",
        "updated_at": "2026-08-05T08:36:06.483384Z",
        "tags": [],
        "adopted_by": None,
    }
    result.update(overrides)
    return result


def document(*nodes: object) -> dict[str, object]:
    return {
        "items": list(nodes),
        "limit": 100,
        "offset": 0,
        "total": len(nodes),
    }


class MeshCoreHubAdvertisementTests(unittest.TestCase):
    def advertisement(
        self,
        **overrides: object,
    ) -> dict[str, object]:
        result: dict[str, object] = {
            "public_key": "01" * 32,
            "received_at": "2026-08-07T07:10:57Z",
            "packet_hash": "338FFB499235B61F",
            "observers": [
                {
                    "node_id": "observer-uuid",
                    "public_key": "ab" * 32,
                    "name": "Mapache",
                    "tag_name": None,
                    "snr": -6.75,
                    "path_len": 2,
                    "observed_at": (
                        "2026-08-07T07:10:57.369025Z"
                    ),
                }
            ],
        }
        result.update(overrides)
        return result

    def advertisement_document(
        self,
        *records: object,
    ) -> dict[str, object]:
        return {
            "items": list(records),
            "limit": 100,
            "offset": 0,
            "total": len(records),
        }

    def test_receptions_are_normalized(self) -> None:
        receptions = parse_meshcore_hub_advertisements(
            self.advertisement_document(
                self.advertisement(
                    observers=[
                        {
                            "public_key": "ab" * 32,
                            "snr": -6.75,
                            "path_len": 2,
                            "observed_at": (
                                "2026-08-07T07:10:57.369025Z"
                            ),
                        },
                        {
                            "public_key": "cd" * 32,
                            "snr": 3.5,
                            "path_len": None,
                            "observed_at": (
                                "2026-08-07T07:10:58.411675Z"
                            ),
                        },
                    ]
                )
            ),
            source="meshcore_hub",
        )

        self.assertEqual(len(receptions), 2)
        self.assertEqual(
            receptions[0].node_source_id,
            "01" * 32,
        )
        self.assertEqual(
            receptions[0].observer_source_id,
            "ab" * 32,
        )
        self.assertEqual(
            receptions[0].packet_hash,
            "338FFB499235B61F",
        )
        self.assertEqual(
            receptions[0].observed_at,
            "2026-08-07T07:10:57Z",
        )
        self.assertEqual(receptions[0].snr_db, -6.75)
        self.assertEqual(receptions[0].path_len, 2)
        self.assertEqual(
            receptions[1].observer_source_id,
            "cd" * 32,
        )
        self.assertEqual(receptions[1].snr_db, 3.5)
        self.assertIsNone(receptions[1].path_len)

    def test_advertisement_without_packet_hash_is_ignored(
        self,
    ) -> None:
        receptions = parse_meshcore_hub_advertisements(
            self.advertisement_document(
                self.advertisement(packet_hash=None)
            ),
            source="meshcore_hub",
        )

        self.assertEqual(receptions, ())

    def test_empty_observers_are_valid(self) -> None:
        receptions = parse_meshcore_hub_advertisements(
            self.advertisement_document(
                self.advertisement(observers=[])
            ),
            source="meshcore_hub",
        )

        self.assertEqual(receptions, ())

    def test_invalid_observers_are_rejected(self) -> None:
        with self.assertRaisesRegex(
            MeshCoreHubError,
            "observers debe ser unha lista",
        ):
            parse_meshcore_hub_advertisements(
                self.advertisement_document(
                    self.advertisement(observers=None)
                ),
                source="meshcore_hub",
            )

    def test_invalid_observer_public_key_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            MeshCoreHubError,
            "64 caracteres hexadecimais",
        ):
            parse_meshcore_hub_advertisements(
                self.advertisement_document(
                    self.advertisement(
                        observers=[
                            {
                                "public_key": "abcd",
                                "snr": 1.0,
                                "path_len": None,
                                "observed_at": (
                                    "2026-08-07T07:10:57Z"
                                ),
                            }
                        ]
                    )
                ),
                source="meshcore_hub",
            )

    def test_reused_packet_hash_at_different_times_is_valid(
        self,
    ) -> None:
        observer = {
            "public_key": "ab" * 32,
            "snr": -6.75,
            "path_len": None,
            "observed_at": "2026-08-07T07:10:57Z",
        }
        later_observer = dict(observer)
        later_observer["observed_at"] = (
            "2026-08-08T07:10:57Z"
        )

        receptions = parse_meshcore_hub_advertisements(
            self.advertisement_document(
                self.advertisement(
                    observers=[observer]
                ),
                self.advertisement(
                    observers=[later_observer]
                ),
            ),
            source="meshcore_hub",
        )

        self.assertEqual(len(receptions), 2)
        self.assertEqual(
            [item.observed_at for item in receptions],
            [
                "2026-08-07T07:10:57Z",
                "2026-08-08T07:10:57Z",
            ],
        )

    def test_duplicate_observer_reception_is_rejected(
        self,
    ) -> None:
        observer = {
            "public_key": "ab" * 32,
            "snr": -6.75,
            "path_len": None,
            "observed_at": "2026-08-07T07:10:57Z",
        }

        with self.assertRaisesRegex(
            MeshCoreHubError,
            "recepción duplicada",
        ):
            parse_meshcore_hub_advertisements(
                self.advertisement_document(
                    self.advertisement(
                        observers=[observer, dict(observer)]
                    )
                ),
                source="meshcore_hub",
            )

    def test_negative_path_length_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            MeshCoreHubError,
            "path_len non pode ser negativo",
        ):
            parse_meshcore_hub_advertisements(
                self.advertisement_document(
                    self.advertisement(
                        observers=[
                            {
                                "public_key": "ab" * 32,
                                "snr": None,
                                "path_len": -1,
                                "observed_at": (
                                    "2026-08-07T07:10:57Z"
                                ),
                            }
                        ]
                    )
                ),
                source="meshcore_hub",
            )


class MeshCoreHubPacketGroupEdgeTests(unittest.TestCase):
    def test_two_byte_path_is_resolved_to_observed_edges(
        self,
    ) -> None:
        nodes = {
            "EA2B": ("ea2b" + "11" * 30),
            "48B4": ("48b4" + "22" * 30),
            "CAC2": ("cac2" + "33" * 30),
        }

        document = {
            "items": [
                {
                    "packet_hash": "64C4F8DA7624E41C",
                    "path_hash_bytes": 2,
                    "receptions": [
                        {
                            "observed_by": "ab" * 32,
                            "observer_name": "Mapache",
                            "snr": -4.5,
                            "received_at": (
                                "2026-08-10T11:30:00Z"
                            ),
                            "path_hashes": [
                                "EA2B",
                                "48B4",
                                "CAC2",
                            ],
                        }
                    ],
                }
            ],
            "limit": 100,
            "offset": 0,
            "total": 1,
        }

        edges = parse_meshcore_hub_packet_group_edges(
            document,
            source="meshcore_hub",
            public_keys_by_path_hash=nodes,
        )

        self.assertEqual(len(edges), 2)

        self.assertEqual(
            edges[0].from_source_id,
            nodes["EA2B"],
        )
        self.assertEqual(
            edges[0].to_source_id,
            nodes["48B4"],
        )
        self.assertEqual(
            edges[1].from_source_id,
            nodes["48B4"],
        )
        self.assertEqual(
            edges[1].to_source_id,
            nodes["CAC2"],
        )

        self.assertTrue(edges[0].directed)
        self.assertEqual(
            edges[0].edge_type,
            "observed",
        )
        self.assertEqual(
            edges[0].observed_at,
            "2026-08-10T11:30:00Z",
        )
        self.assertEqual(
            edges[0].metrics["snr_db"],
            -4.5,
        )

    def test_two_byte_path_preserves_route_identity(
        self,
    ) -> None:
        nodes = {
            "EA2B": ("ea2b" + "11" * 30),
            "48B4": ("48b4" + "22" * 30),
            "CAC2": ("cac2" + "33" * 30),
        }

        document = {
            "items": [
                {
                    "packet_hash": "64C4F8DA7624E41C",
                    "path_hash_bytes": 2,
                    "receptions": [
                        {
                            "observed_by": "ab" * 32,
                            "snr": -4.5,
                            "received_at": (
                                "2026-08-10T11:30:00Z"
                            ),
                            "path_hashes": [
                                "EA2B",
                                "48B4",
                                "CAC2",
                            ],
                        }
                    ],
                }
            ],
            "limit": 100,
            "offset": 0,
            "total": 1,
        }

        edges = parse_meshcore_hub_packet_group_edges(
            document,
            source="meshcore_hub",
            public_keys_by_path_hash=nodes,
        )

        self.assertEqual(len(edges), 2)
        self.assertIsNotNone(edges[0].route_id)
        self.assertEqual(
            edges[0].route_id,
            edges[1].route_id,
        )
        self.assertEqual(
            [edge.route_index for edge in edges],
            [0, 1],
        )

    def test_unresolved_path_segment_is_not_invented(
        self,
    ) -> None:
        first = "ea2b" + "11" * 30
        third = "cac2" + "33" * 30

        document = {
            "items": [
                {
                    "packet_hash": "HASH",
                    "path_hash_bytes": 2,
                    "receptions": [
                        {
                            "observed_by": "ab" * 32,
                            "snr": None,
                            "received_at": (
                                "2026-08-10T11:30:00Z"
                            ),
                            "path_hashes": [
                                "EA2B",
                                "FFFF",
                                "CAC2",
                            ],
                        }
                    ],
                }
            ],
            "limit": 100,
            "offset": 0,
            "total": 1,
        }

        edges = parse_meshcore_hub_packet_group_edges(
            document,
            source="meshcore_hub",
            public_keys_by_path_hash={
                "EA2B": first,
                "CAC2": third,
            },
        )

        self.assertEqual(edges, ())

    def test_non_two_byte_paths_are_ignored(
        self,
    ) -> None:
        document = {
            "items": [
                {
                    "packet_hash": "HASH",
                    "path_hash_bytes": 1,
                    "receptions": [
                        {
                            "observed_by": "ab" * 32,
                            "received_at": (
                                "2026-08-10T11:30:00Z"
                            ),
                            "path_hashes": [
                                "EA",
                                "48",
                            ],
                        }
                    ],
                }
            ],
            "limit": 100,
            "offset": 0,
            "total": 1,
        }

        edges = parse_meshcore_hub_packet_group_edges(
            document,
            source="meshcore_hub",
            public_keys_by_path_hash={},
        )

        self.assertEqual(edges, ())


class MeshCoreHubTests(unittest.TestCase):
    def test_valid_node_is_normalized(self) -> None:
        observations = parse_meshcore_hub_nodes(
            document(node()),
            source="meshcore_hub",
        )

        self.assertEqual(len(observations), 1)

        observation = observations[0]

        self.assertEqual(
            observation.id,
            "meshcore:" + PUBLIC_KEY,
        )
        self.assertEqual(
            observation.short_name,
            "Repetidor do Hub",
        )
        self.assertEqual(
            observation.node_type,
            "repeater",
        )
        self.assertIs(observation.is_observer, False)
        self.assertEqual(
            observation.first_seen,
            "2026-08-05T08:30:00Z",
        )
        self.assertEqual(
            observation.observed_at,
            "2026-08-05T08:36:06Z",
        )
        self.assertEqual(observation.latitude, 43.1)
        self.assertEqual(observation.longitude, -8.1)
        self.assertEqual(
            observation.position_updated_at,
            "2026-08-05T08:36:06Z",
        )

    def test_chat_type_is_mapped_to_client(self) -> None:
        observation = parse_meshcore_hub_nodes(
            document(node(adv_type="chat")),
            source="meshcore_hub",
        )[0]

        self.assertEqual(observation.node_type, "client")

    def test_observer_without_position_is_valid(self) -> None:
        observation = parse_meshcore_hub_nodes(
            document(
                node(
                    name=None,
                    adv_type=None,
                    flags=None,
                    lat=None,
                    lon=None,
                    is_observer=True,
                )
            ),
            source="meshcore_hub",
        )[0]

        self.assertIsNone(observation.short_name)
        self.assertEqual(observation.node_type, "unknown")
        self.assertIs(observation.is_observer, True)
        self.assertIsNone(observation.latitude)
        self.assertIsNone(observation.position_updated_at)

    def test_zero_coordinates_are_discarded(self) -> None:
        observation = parse_meshcore_hub_nodes(
            document(node(lat=0.0, lon=0.0)),
            source="meshcore_hub",
        )[0]

        self.assertIsNone(observation.latitude)
        self.assertIsNone(observation.longitude)
        self.assertIsNone(observation.position_updated_at)

    def test_out_of_range_latitude_is_discarded(self) -> None:
        observation = parse_meshcore_hub_nodes(
            document(
                node(
                    lat=161.163191,
                    lon=-7.990788,
                )
            ),
            source="meshcore_hub",
        )[0]

        self.assertIsNone(observation.latitude)
        self.assertIsNone(observation.longitude)
        self.assertIsNone(observation.position_updated_at)

    def test_out_of_range_longitude_is_discarded(self) -> None:
        observation = parse_meshcore_hub_nodes(
            document(
                node(
                    lat=41.163191,
                    lon=-207.990788,
                )
            ),
            source="meshcore_hub",
        )[0]

        self.assertIsNone(observation.latitude)
        self.assertIsNone(observation.longitude)
        self.assertIsNone(observation.position_updated_at)

    def test_unknown_type_is_preserved_as_unknown(self) -> None:
        observation = parse_meshcore_hub_nodes(
            document(node(adv_type="future_role")),
            source="meshcore_hub",
        )[0]

        self.assertEqual(observation.node_type, "unknown")

    def test_duplicate_public_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            MeshCoreHubError,
            "public_key duplicada",
        ):
            parse_meshcore_hub_nodes(
                document(node(), node()),
                source="meshcore_hub",
            )

    def test_missing_required_field_is_rejected(self) -> None:
        invalid = node()
        del invalid["last_seen"]

        with self.assertRaisesRegex(
            MeshCoreHubError,
            "falta o campo 'last_seen'",
        ):
            parse_meshcore_hub_nodes(
                document(invalid),
                source="meshcore_hub",
            )

    def test_invalid_public_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            MeshCoreHubError,
            "64 caracteres hexadecimais",
        ):
            parse_meshcore_hub_nodes(
                document(node(public_key="abcd")),
                source="meshcore_hub",
            )

    def test_partial_coordinates_are_rejected(self) -> None:
        with self.assertRaisesRegex(
            MeshCoreHubError,
            "lat e lon deben aparecer xuntas",
        ):
            parse_meshcore_hub_nodes(
                document(node(lon=None)),
                source="meshcore_hub",
            )

    def test_invalid_tags_are_rejected(self) -> None:
        with self.assertRaisesRegex(
            MeshCoreHubError,
            "tags debe ser unha lista",
        ):
            parse_meshcore_hub_nodes(
                document(node(tags=None)),
                source="meshcore_hub",
            )

    def test_invalid_root_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            MeshCoreHubError,
            "raíz.*obxecto",
        ):
            parse_meshcore_hub_nodes(
                [],
                source="meshcore_hub",
            )


if __name__ == "__main__":
    unittest.main()
