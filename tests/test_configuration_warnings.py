"""Pruebas de los avisos de configuración."""

from __future__ import annotations

import unittest

from mesh_noroeste.configuration_warnings import (
    ConfigurationWarningsError,
    build_configuration_warnings_document,
    build_unavailable_configuration_warnings_document,
)


GENERATED_AT = "2026-07-28T02:30:00Z"
UPDATED = 1_785_193_457


def published(
    node_id: str = "meshtastic:!0123abcd",
    *,
    network: str = "meshtastic",
    sources: list[str] | None = None,
) -> dict[str, object]:
    return {
        "id": node_id,
        "network": network,
        "sources": (
            ["ozulo_map"]
            if sources is None
            else sources
        ),
    }


def record(
    node_id: str = "!0123abcd",
    *,
    issues: list[object] | None = None,
) -> dict[str, object]:
    return {
        "id": node_id,
        "issues": [] if issues is None else issues,
    }


class ConfigurationWarningsTests(unittest.TestCase):
    def test_valid_document_is_normalized(self) -> None:
        document = build_configuration_warnings_document(
            {
                "updated": UPDATED,
                "nodes": [
                    record(
                        issues=[
                            {
                                "key": "position_fixed",
                                "severity": "high",
                                "label": "Texto descartado",
                            }
                        ]
                    )
                ],
            },
            [published()],
            generated_at=GENERATED_AT,
        )

        self.assertEqual(
            document["generated_at"],
            GENERATED_AT,
        )
        self.assertIs(
            document["analysis"]["available"],
            True,
        )
        self.assertEqual(
            document["analysis"]["updated_at"],
            "2026-07-27T23:04:17Z",
        )
        self.assertEqual(
            document["analysis"]["eligible_nodes"],
            1,
        )
        self.assertEqual(
            document["analysis"]["analyzed_nodes"],
            1,
        )
        self.assertEqual(
            document["analysis"]["nodes_with_warnings"],
            1,
        )
        self.assertEqual(
            document["nodes"],
            [
                {
                    "id": "meshtastic:!0123abcd",
                    "warnings": [
                        {
                            "key": "fixed_position_frequent",
                            "severity": "high",
                        }
                    ],
                }
            ],
        )

    def test_unavailable_analysis_is_explicit(self) -> None:
        document = (
            build_unavailable_configuration_warnings_document(
                [
                    published(),
                    published(
                        "meshtastic:!89abcdef",
                        sources=["malha_pt"],
                    ),
                ],
                generated_at=GENERATED_AT,
            )
        )

        self.assertIs(
            document["analysis"]["available"],
            False,
        )
        self.assertIsNone(
            document["analysis"]["updated_at"]
        )
        self.assertEqual(
            document["analysis"]["eligible_nodes"],
            1,
        )
        self.assertEqual(
            document["analysis"]["analyzed_nodes"],
            0,
        )
        self.assertEqual(document["nodes"], [])

    def test_only_ozulo_meshtastic_is_eligible(self) -> None:
        document = build_configuration_warnings_document(
            {
                "updated": UPDATED,
                "nodes": [
                    record("!0123abcd"),
                    record("!89abcdef"),
                    record("!11111111"),
                ],
            },
            [
                published(),
                published(
                    "meshtastic:!89abcdef",
                    sources=["malha_pt"],
                ),
                published(
                    "meshcore:" + "11" * 32,
                    network="meshcore",
                    sources=["meshcore_map"],
                ),
            ],
            generated_at=GENERATED_AT,
        )

        self.assertEqual(
            document["analysis"]["eligible_nodes"],
            1,
        )
        self.assertEqual(
            [node["id"] for node in document["nodes"]],
            ["meshtastic:!0123abcd"],
        )

    def test_analyzed_node_without_warnings_is_kept(
        self,
    ) -> None:
        document = build_configuration_warnings_document(
            {
                "updated": UPDATED,
                "nodes": [record()],
            },
            [published()],
            generated_at=GENERATED_AT,
        )

        self.assertEqual(
            document["analysis"]["analyzed_nodes"],
            1,
        )
        self.assertEqual(
            document["analysis"]["nodes_with_warnings"],
            0,
        )
        self.assertEqual(
            document["nodes"][0]["warnings"],
            [],
        )

    def test_unknown_warning_is_ignored(self) -> None:
        document = build_configuration_warnings_document(
            {
                "updated": UPDATED,
                "nodes": [
                    record(
                        issues=[
                            {
                                "key": "future_rule",
                                "severity": "medium",
                            }
                        ]
                    )
                ],
            },
            [published()],
            generated_at=GENERATED_AT,
        )

        self.assertEqual(
            document["nodes"][0]["warnings"],
            [],
        )

    def test_duplicate_analysis_id_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ConfigurationWarningsError,
            "id duplicado",
        ):
            build_configuration_warnings_document(
                {
                    "updated": UPDATED,
                    "nodes": [record(), record()],
                },
                [published()],
                generated_at=GENERATED_AT,
            )

    def test_invalid_severity_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ConfigurationWarningsError,
            "severidad no admitida",
        ):
            build_configuration_warnings_document(
                {
                    "updated": UPDATED,
                    "nodes": [
                        record(
                            issues=[
                                {
                                    "key": "position_fixed",
                                    "severity": "low",
                                }
                            ]
                        )
                    ],
                },
                [published()],
                generated_at=GENERATED_AT,
            )

    def test_duplicate_published_node_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ConfigurationWarningsError,
            "Nodo publicado duplicado",
        ):
            build_configuration_warnings_document(
                {
                    "updated": UPDATED,
                    "nodes": [record()],
                },
                [published(), published()],
                generated_at=GENERATED_AT,
            )

    def test_invalid_updated_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ConfigurationWarningsError,
            "updated no es un timestamp válido",
        ):
            build_configuration_warnings_document(
                {
                    "updated": True,
                    "nodes": [],
                },
                [],
                generated_at=GENERATED_AT,
            )

    def test_invalid_root_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ConfigurationWarningsError,
            "raíz.*objeto",
        ):
            build_configuration_warnings_document(
                [],
                [published()],
                generated_at=GENERATED_AT,
            )


if __name__ == "__main__":
    unittest.main()
