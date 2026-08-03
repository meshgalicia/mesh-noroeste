"""Pruebas de la lista privada de exclusiones."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from mesh_noroeste.exclusions import (
    ExclusionsError,
    load_exclusions,
)


class ExclusionsTests(unittest.TestCase):
    def write_document(
        self,
        root: Path,
        document: object,
    ) -> Path:
        path = root / "exclusions.json"
        path.write_text(
            json.dumps(document),
            encoding="utf-8",
        )
        return path

    def test_missing_configuration_is_empty(self) -> None:
        self.assertEqual(
            load_exclusions(None),
            frozenset(),
        )

    def test_valid_document_normalizes_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = self.write_document(
                root,
                {
                    "exclusions": [
                        {
                            "canonical_id": (
                                "meshtastic:!A35B4144"
                            ),
                            "note": "Solicitud verificada",
                        },
                        {
                            "canonical_id": (
                                "meshcore:02AB34CD"
                            ),
                        },
                    ]
                },
            )

            exclusions = load_exclusions(path)

        self.assertEqual(
            exclusions,
            frozenset({
                "meshtastic:!a35b4144",
                "meshcore:02ab34cd",
            }),
        )

    def test_duplicate_normalized_id_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = self.write_document(
                root,
                {
                    "exclusions": [
                        {
                            "canonical_id": (
                                "meshtastic:!A35B4144"
                            ),
                        },
                        {
                            "canonical_id": (
                                "meshtastic:a35b4144"
                            ),
                        },
                    ]
                },
            )

            with self.assertRaisesRegex(
                ExclusionsError,
                "identificador duplicado",
            ):
                load_exclusions(path)

    def test_unknown_root_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = self.write_document(
                root,
                {
                    "exclusions": [],
                    "published": True,
                },
            )

            with self.assertRaisesRegex(
                ExclusionsError,
                "Campos raíz incorrectos",
            ):
                load_exclusions(path)

    def test_unknown_entry_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = self.write_document(
                root,
                {
                    "exclusions": [
                        {
                            "canonical_id": (
                                "meshtastic:!a35b4144"
                            ),
                            "owner": "dato no permitido",
                        }
                    ]
                },
            )

            with self.assertRaisesRegex(
                ExclusionsError,
                "campos no admitidos",
            ):
                load_exclusions(path)

    def test_invalid_canonical_id_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = self.write_document(
                root,
                {
                    "exclusions": [
                        {
                            "canonical_id": "!a35b4144",
                        }
                    ]
                },
            )

            with self.assertRaisesRegex(
                ExclusionsError,
                "prefijo de red",
            ):
                load_exclusions(path)

    def test_empty_note_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = self.write_document(
                root,
                {
                    "exclusions": [
                        {
                            "canonical_id": (
                                "meshtastic:!a35b4144"
                            ),
                            "note": "   ",
                        }
                    ]
                },
            )

            with self.assertRaisesRegex(
                ExclusionsError,
                "note no puede estar vacía",
            ):
                load_exclusions(path)

    def test_configured_missing_file_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = (
                Path(temporary)
                / "missing-exclusions.json"
            )

            with self.assertRaisesRegex(
                ExclusionsError,
                "No se pudo leer",
            ):
                load_exclusions(missing)

    def test_invalid_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "exclusions.json"
            path.write_text(
                '{"exclusions": [}',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ExclusionsError,
                "No se pudo leer",
            ):
                load_exclusions(path)


if __name__ == "__main__":
    unittest.main()
