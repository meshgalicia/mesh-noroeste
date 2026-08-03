"""Pruebas de las funciones de normalización."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest

from mesh_noroeste.normalization import (
    canonical_node_id,
    normalize_coordinates,
    normalize_meshcore_id,
    normalize_meshtastic_id,
    normalize_timestamp,
)


class MeshtasticIdentifierTests(unittest.TestCase):
    def test_text_identifier_is_normalized(self) -> None:
        self.assertEqual(
            normalize_meshtastic_id(" !A35B4144 "),
            "!a35b4144",
        )

    def test_integer_identifier_preserves_zeroes(self) -> None:
        self.assertEqual(
            normalize_meshtastic_id(0x00AB12CD),
            "!00ab12cd",
        )

    def test_invalid_identifier_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "ocho caracteres hexadecimales",
        ):
            normalize_meshtastic_id("a35b414")


class MeshCoreIdentifierTests(unittest.TestCase):
    def test_hexadecimal_identifier_is_lowercase(self) -> None:
        self.assertEqual(
            normalize_meshcore_id(" 02AB34CD "),
            "02ab34cd",
        )

    def test_non_hexadecimal_identifier_is_preserved(self) -> None:
        self.assertEqual(
            normalize_meshcore_id("Nodo-Galicia_01"),
            "Nodo-Galicia_01",
        )

    def test_whitespace_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "no puede contener espacios",
        ):
            normalize_meshcore_id("nodo galicia")


class CanonicalIdentifierTests(unittest.TestCase):
    def test_meshtastic_canonical_identifier(self) -> None:
        self.assertEqual(
            canonical_node_id(
                "Meshtastic",
                "A35B4144",
            ),
            "meshtastic:!a35b4144",
        )

    def test_meshcore_canonical_identifier(self) -> None:
        self.assertEqual(
            canonical_node_id(
                "meshcore",
                "02AB34CD",
            ),
            "meshcore:02ab34cd",
        )

    def test_unknown_network_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Red no admitida",
        ):
            canonical_node_id("otra", "1234")


class TimestampTests(unittest.TestCase):
    def test_iso_offset_is_converted_to_utc(self) -> None:
        self.assertEqual(
            normalize_timestamp(
                "2026-07-25T14:00:00+02:00"
            ),
            "2026-07-25T12:00:00Z",
        )

    def test_aware_datetime_is_converted(self) -> None:
        value = datetime(
            2026,
            7,
            25,
            12,
            0,
            0,
            900000,
            tzinfo=timezone.utc,
        )

        self.assertEqual(
            normalize_timestamp(value),
            "2026-07-25T12:00:00Z",
        )

    def test_epoch_seconds_milliseconds_and_microseconds(
        self,
    ) -> None:
        expected = "2023-11-14T22:13:20Z"

        values = (
            1_700_000_000,
            1_700_000_000_000,
            1_700_000_000_000_000,
            "1700000000000",
        )

        for value in values:
            with self.subTest(value=value):
                self.assertEqual(
                    normalize_timestamp(value),
                    expected,
                )

    def test_naive_datetime_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "zona horaria",
        ):
            normalize_timestamp(
                datetime(2026, 7, 25, 12, 0, 0)
            )

    def test_naive_iso_string_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "zona horaria",
        ):
            normalize_timestamp(
                "2026-07-25T12:00:00"
            )


class CoordinateTests(unittest.TestCase):
    def test_numeric_strings_are_normalized(self) -> None:
        self.assertEqual(
            normalize_coordinates(
                "43.123456",
                "-8.123456",
            ),
            (43.123456, -8.123456),
        )

    def test_missing_position_is_allowed(self) -> None:
        self.assertEqual(
            normalize_coordinates(None, None),
            (None, None),
        )

    def test_partial_position_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "deben aparecer juntas",
        ):
            normalize_coordinates(43.0, None)

    def test_zero_position_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "0, 0",
        ):
            normalize_coordinates(0, 0)

    def test_out_of_range_position_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "latitude debe estar",
        ):
            normalize_coordinates(91, -8)


if __name__ == "__main__":
    unittest.main()
