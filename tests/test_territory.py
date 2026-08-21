"""Pruebas de clasificación territorial local."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from mesh_noroeste.territory import (
    TerritoryDataError,
    TerritoryIndex,
)


def feature(
    identifier: str,
    name: str,
    level: str,
    coordinates: list,
    *,
    country: str | None = "ES",
    parent: str | None = None,
    geometry_type: str = "Polygon",
) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "id": identifier,
            "name": name,
            "level": level,
            "country": country,
            "parent": parent,
        },
        "geometry": {
            "type": geometry_type,
            "coordinates": coordinates,
        },
    }


def square(
    west: float,
    south: float,
    east: float,
    north: float,
) -> list:
    return [[
        [west, south],
        [east, south],
        [east, north],
        [west, north],
        [west, south],
    ]]


class TerritoryIndexTests(
    unittest.TestCase
):
    def test_point_inside_polygon(
        self,
    ) -> None:
        index = TerritoryIndex.from_geojson(
            {
                "type": "FeatureCollection",
                "features": [
                    feature(
                        "es-ga-cangas",
                        "Cangas",
                        "municipality",
                        square(
                            -8.9,
                            42.2,
                            -8.7,
                            42.4,
                        ),
                        parent="Pontevedra",
                    )
                ],
            }
        )

        result = index.find_one(
            42.27,
            -8.79,
            level="municipality",
        )

        self.assertIsNotNone(result)

        assert result is not None

        self.assertEqual(
            result.name,
            "Cangas",
        )
        self.assertEqual(
            result.parent,
            "Pontevedra",
        )

    def test_point_outside_polygon(
        self,
    ) -> None:
        index = TerritoryIndex.from_geojson(
            {
                "type": "FeatureCollection",
                "features": [
                    feature(
                        "test",
                        "Test",
                        "municipality",
                        square(
                            -9.0,
                            42.0,
                            -8.0,
                            43.0,
                        ),
                    )
                ],
            }
        )

        self.assertIsNone(
            index.find_one(
                41.0,
                -8.5,
                level="municipality",
            )
        )

    def test_boundary_counts_as_inside(
        self,
    ) -> None:
        index = TerritoryIndex.from_geojson(
            {
                "type": "FeatureCollection",
                "features": [
                    feature(
                        "test",
                        "Test",
                        "municipality",
                        square(
                            -9.0,
                            42.0,
                            -8.0,
                            43.0,
                        ),
                    )
                ],
            }
        )

        self.assertIsNotNone(
            index.find_one(
                42.0,
                -8.5,
                level="municipality",
            )
        )

    def test_polygon_hole_is_excluded(
        self,
    ) -> None:
        coordinates = square(
            -10.0,
            40.0,
            -5.0,
            45.0,
        )

        coordinates.append(
            square(
                -8.5,
                42.0,
                -7.5,
                43.0,
            )[0]
        )

        index = TerritoryIndex.from_geojson(
            {
                "type": "FeatureCollection",
                "features": [
                    feature(
                        "with-hole",
                        "Con oco",
                        "municipality",
                        coordinates,
                    )
                ],
            }
        )

        self.assertIsNone(
            index.find_one(
                42.5,
                -8.0,
                level="municipality",
            )
        )

        self.assertIsNotNone(
            index.find_one(
                41.0,
                -8.0,
                level="municipality",
            )
        )

    def test_multipolygon(
        self,
    ) -> None:
        coordinates = [
            square(
                -9.0,
                42.0,
                -8.5,
                42.5,
            ),
            square(
                -8.0,
                42.0,
                -7.5,
                42.5,
            ),
        ]

        index = TerritoryIndex.from_geojson(
            {
                "type": "FeatureCollection",
                "features": [
                    feature(
                        "multi",
                        "Illas",
                        "municipality",
                        coordinates,
                        geometry_type="MultiPolygon",
                    )
                ],
            }
        )

        self.assertIsNotNone(
            index.find_one(
                42.25,
                -7.75,
                level="municipality",
            )
        )

    def test_multiple_administrative_levels(
        self,
    ) -> None:
        index = TerritoryIndex.from_geojson(
            {
                "type": "FeatureCollection",
                "features": [
                    feature(
                        "es-ga-po",
                        "Pontevedra",
                        "province",
                        square(
                            -9.5,
                            41.5,
                            -7.5,
                            43.0,
                        ),
                    ),
                    feature(
                        "es-ga-cangas",
                        "Cangas",
                        "municipality",
                        square(
                            -8.9,
                            42.2,
                            -8.7,
                            42.4,
                        ),
                        parent="Pontevedra",
                    ),
                ],
            }
        )

        matches = index.find(
            42.27,
            -8.79,
        )

        self.assertEqual(
            [
                match.level
                for match in matches
            ],
            [
                "province",
                "municipality",
            ],
        )

    def test_none_position_has_no_matches(
        self,
    ) -> None:
        index = TerritoryIndex(())

        self.assertEqual(
            index.find(
                None,
                -8.0,
            ),
            (),
        )
        self.assertEqual(
            index.find(
                42.0,
                None,
            ),
            (),
        )

    def test_duplicate_ids_are_rejected(
        self,
    ) -> None:
        document = {
            "type": "FeatureCollection",
            "features": [
                feature(
                    "duplicate",
                    "A",
                    "province",
                    square(
                        -9,
                        42,
                        -8,
                        43,
                    ),
                ),
                feature(
                    "duplicate",
                    "B",
                    "province",
                    square(
                        -8,
                        42,
                        -7,
                        43,
                    ),
                ),
            ],
        }

        with self.assertRaisesRegex(
            TerritoryDataError,
            "duplicados",
        ):
            TerritoryIndex.from_geojson(
                document
            )

    def test_invalid_geometry_is_rejected(
        self,
    ) -> None:
        document = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "id": "point",
                        "name": "Point",
                        "level": "municipality",
                        "country": "ES",
                        "parent": None,
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            -8.0,
                            42.0,
                        ],
                    },
                }
            ],
        }

        with self.assertRaisesRegex(
            TerritoryDataError,
            "Polygon",
        ):
            TerritoryIndex.from_geojson(
                document
            )

    def test_load_from_path(
        self,
    ) -> None:
        document = {
            "type": "FeatureCollection",
            "features": [
                feature(
                    "es-ga-cangas",
                    "Cangas",
                    "municipality",
                    square(
                        -8.9,
                        42.2,
                        -8.7,
                        42.4,
                    ),
                )
            ],
        }

        with tempfile.TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / "territories.geojson"
            )

            path.write_text(
                json.dumps(document),
                encoding="utf-8",
            )

            index = TerritoryIndex.from_path(
                path
            )

            result = index.find_one(
                42.27,
                -8.79,
                level="municipality",
            )

            self.assertIsNotNone(result)


class TerritoryPrecisionTests(
    unittest.TestCase
):
    def test_precision_cell_size_for_13_bits(
        self,
    ) -> None:
        from mesh_noroeste.territory import (
            precision_cell,
        )

        cell = precision_cell(
            43.384832,
            -8.4148224,
            13,
        )

        self.assertAlmostEqual(
            cell.north - cell.south,
            0.0524288,
        )
        self.assertAlmostEqual(
            cell.east - cell.west,
            0.0524288,
        )

    def test_exact_match_keeps_exact_status(
        self,
    ) -> None:
        index = TerritoryIndex.from_geojson(
            {
                "type": "FeatureCollection",
                "features": [
                    feature(
                        "a",
                        "A",
                        "municipality",
                        square(
                            -9.0,
                            42.0,
                            -8.0,
                            43.0,
                        ),
                    )
                ],
            }
        )

        result = index.classify(
            42.5,
            -8.5,
            level="municipality",
            precision_bits=13,
        )

        self.assertEqual(
            result.status,
            "exact",
        )
        self.assertIsNotNone(
            result.exact
        )
        self.assertEqual(
            [
                item.name
                for item in result.compatible
            ],
            ["A"],
        )

    def test_single_cell_intersection_is_compatible(
        self,
    ) -> None:
        index = TerritoryIndex.from_geojson(
            {
                "type": "FeatureCollection",
                "features": [
                    feature(
                        "a",
                        "A",
                        "municipality",
                        square(
                            -8.44,
                            43.36,
                            -8.40,
                            43.40,
                        ),
                    )
                ],
            }
        )

        # O punto queda lixeiramente fóra do polígono,
        # pero unha cela de 13 bits chega a intersectalo.
        result = index.classify(
            43.384832,
            -8.39,
            level="municipality",
            precision_bits=13,
        )

        self.assertEqual(
            result.status,
            "compatible",
        )
        self.assertIsNone(
            result.exact
        )
        self.assertEqual(
            [
                item.name
                for item in result.compatible
            ],
            ["A"],
        )

    def test_multiple_cell_intersections_are_ambiguous(
        self,
    ) -> None:
        index = TerritoryIndex.from_geojson(
            {
                "type": "FeatureCollection",
                "features": [
                    feature(
                        "west",
                        "Oeste",
                        "municipality",
                        square(
                            -8.45,
                            43.35,
                            -8.405,
                            43.42,
                        ),
                    ),
                    feature(
                        "east",
                        "Leste",
                        "municipality",
                        square(
                            -8.395,
                            43.35,
                            -8.35,
                            43.42,
                        ),
                    ),
                ],
            }
        )

        result = index.classify(
            43.384832,
            -8.40,
            level="municipality",
            precision_bits=13,
        )

        self.assertEqual(
            result.status,
            "ambiguous",
        )
        self.assertEqual(
            {
                item.name
                for item in result.compatible
            },
            {
                "Oeste",
                "Leste",
            },
        )

    def test_cell_outside_all_territories(
        self,
    ) -> None:
        index = TerritoryIndex.from_geojson(
            {
                "type": "FeatureCollection",
                "features": [
                    feature(
                        "a",
                        "A",
                        "municipality",
                        square(
                            -9.0,
                            42.0,
                            -8.8,
                            42.2,
                        ),
                    )
                ],
            }
        )

        result = index.classify(
            43.5,
            -7.0,
            level="municipality",
            precision_bits=19,
        )

        self.assertEqual(
            result.status,
            "outside",
        )
        self.assertEqual(
            result.compatible,
            (),
        )

    def test_without_precision_does_not_invent_compatibility(
        self,
    ) -> None:
        index = TerritoryIndex.from_geojson(
            {
                "type": "FeatureCollection",
                "features": [
                    feature(
                        "a",
                        "A",
                        "municipality",
                        square(
                            -8.44,
                            43.36,
                            -8.40,
                            43.40,
                        ),
                    )
                ],
            }
        )

        result = index.classify(
            43.384832,
            -8.39,
            level="municipality",
            precision_bits=None,
        )

        self.assertEqual(
            result.status,
            "outside",
        )
        self.assertIsNone(
            result.cell
        )

    def test_rectangle_inside_polygon_hole_is_outside(
        self,
    ) -> None:
        coordinates = square(
            -10.0,
            40.0,
            -5.0,
            45.0,
        )

        coordinates.append(
            square(
                -8.5,
                42.0,
                -7.5,
                43.0,
            )[0]
        )

        index = TerritoryIndex.from_geojson(
            {
                "type": "FeatureCollection",
                "features": [
                    feature(
                        "with-hole",
                        "Con oco",
                        "municipality",
                        coordinates,
                    )
                ],
            }
        )

        result = index.classify(
            42.5,
            -8.0,
            level="municipality",
            precision_bits=19,
        )

        self.assertEqual(
            result.status,
            "outside",
        )



if __name__ == "__main__":
    unittest.main()
