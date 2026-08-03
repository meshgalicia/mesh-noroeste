"""Pruebas de la definición geográfica regional."""

from __future__ import annotations

import unittest

from mesh_noroeste.region import (
    DEFAULT_REGION_AREAS,
    DEFAULT_REGION_NAME,
    default_region_bounds,
    point_in_default_region,
)


class RegionTests(unittest.TestCase):
    def test_default_definition(self) -> None:
        self.assertEqual(
            DEFAULT_REGION_NAME,
            (
                "Galicia, Asturias, oeste de "
                "Castilla y León y Portugal"
            ),
        )
        self.assertEqual(len(DEFAULT_REGION_AREAS), 9)
        self.assertEqual(
            default_region_bounds(),
            {
                "south": 36.75,
                "west": -9.75,
                "north": 43.95,
                "east": -4.25,
            },
        )

    def test_midpoint_of_every_area_is_included(
        self,
    ) -> None:
        for area in DEFAULT_REGION_AREAS:
            with self.subTest(area=area.name):
                latitude = (
                    area.south + area.north
                ) / 2
                longitude = (
                    area.west + area.east
                ) / 2

                self.assertTrue(
                    point_in_default_region(
                        latitude,
                        longitude,
                    )
                )

    def test_area_edges_are_inclusive(self) -> None:
        galicia = DEFAULT_REGION_AREAS[0]

        self.assertTrue(
            point_in_default_region(
                galicia.south,
                galicia.west,
            )
        )
        self.assertTrue(
            point_in_default_region(
                galicia.north,
                galicia.east,
            )
        )

    def test_missing_outside_and_gap_are_rejected(
        self,
    ) -> None:
        self.assertFalse(
            point_in_default_region(None, -8.0)
        )
        self.assertFalse(
            point_in_default_region(43.0, None)
        )
        self.assertFalse(
            point_in_default_region(45.0, -8.0)
        )

        # Está dentro del rectángulo envolvente, pero no
        # pertenece a ninguna de las nueve áreas.
        self.assertFalse(
            point_in_default_region(40.0, -6.0)
        )


if __name__ == "__main__":
    unittest.main()
