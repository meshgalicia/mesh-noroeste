"""Definición geográfica de la región publicada."""

from __future__ import annotations

from dataclasses import dataclass


DEFAULT_REGION_NAME = (
    "Galicia, Asturias, oeste de Castilla y León y Portugal"
)


@dataclass(frozen=True, slots=True)
class RegionArea:
    """Rectángulo geográfico incluido en la región."""

    name: str
    south: float
    west: float
    north: float
    east: float

    def contains(
        self,
        latitude: float,
        longitude: float,
    ) -> bool:
        """Comprueba un punto incluyendo los límites."""

        return (
            self.south <= latitude <= self.north
            and self.west <= longitude <= self.east
        )


DEFAULT_REGION_AREAS = (
    RegionArea(
        "Galicia",
        south=41.65,
        west=-9.75,
        north=43.95,
        east=-6.45,
    ),
    RegionArea(
        "Asturias",
        south=42.70,
        west=-7.40,
        north=43.85,
        east=-4.25,
    ),
    RegionArea(
        "León",
        south=41.80,
        west=-7.15,
        north=43.25,
        east=-4.55,
    ),
    RegionArea(
        "Zamora",
        south=41.05,
        west=-6.90,
        north=42.30,
        east=-5.00,
    ),
    RegionArea(
        "Portugal norte",
        south=40.60,
        west=-9.75,
        north=42.30,
        east=-6.00,
    ),
    RegionArea(
        "Portugal centro-norte",
        south=39.55,
        west=-9.75,
        north=40.75,
        east=-6.55,
    ),
    RegionArea(
        "Portugal centro",
        south=38.45,
        west=-9.75,
        north=39.70,
        east=-6.75,
    ),
    RegionArea(
        "Portugal sur",
        south=37.20,
        west=-9.75,
        north=38.60,
        east=-6.95,
    ),
    RegionArea(
        "Portugal Algarve",
        south=36.75,
        west=-9.75,
        north=37.45,
        east=-7.20,
    ),
)


def default_region_bounds() -> dict[str, float]:
    """Devuelve el rectángulo envolvente de todas las áreas."""

    return {
        "south": min(
            area.south
            for area in DEFAULT_REGION_AREAS
        ),
        "west": min(
            area.west
            for area in DEFAULT_REGION_AREAS
        ),
        "north": max(
            area.north
            for area in DEFAULT_REGION_AREAS
        ),
        "east": max(
            area.east
            for area in DEFAULT_REGION_AREAS
        ),
    }


def point_in_default_region(
    latitude: float | None,
    longitude: float | None,
) -> bool:
    """Indica si un punto pertenece a alguna área regional."""

    if latitude is None or longitude is None:
        return False

    return any(
        area.contains(latitude, longitude)
        for area in DEFAULT_REGION_AREAS
    )
