"""Probas do adaptador de nodos de MeshCore Hub."""

from __future__ import annotations

import unittest

from mesh_noroeste.meshcore_hub import (
    MeshCoreHubError,
    parse_meshcore_hub_nodes,
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
