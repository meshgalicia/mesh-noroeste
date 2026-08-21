"""Clasificación territorial de coordenadas mediante GeoJSON local.

Esta capa es independiente de ``region.py``:

- ``region.py`` decide si un punto pertenece al ámbito operativo publicado;
- este módulo describe administrativamente un punto ya conocido.

No realiza geocodificación remota ni modifica el filtro regional.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


Point = tuple[float, float]
Ring = tuple[Point, ...]
Polygon = tuple[Ring, ...]


@dataclass(frozen=True, slots=True)
class Territory:
    """Territorio administrativo cargado desde GeoJSON."""

    id: str
    name: str
    level: str
    country: str | None
    parent: str | None
    polygons: tuple[Polygon, ...]
    south: float
    west: float
    north: float
    east: float

    def contains(
        self,
        latitude: float,
        longitude: float,
    ) -> bool:
        """Indica si el punto pertenece al territorio."""

        if not (
            self.south <= latitude <= self.north
            and self.west <= longitude <= self.east
        ):
            return False

        point = (longitude, latitude)

        return any(
            _point_in_polygon(point, polygon)
            for polygon in self.polygons
        )


@dataclass(frozen=True, slots=True)
class TerritoryMatch:
    """Resultado normalizado de una clasificación territorial."""

    id: str
    name: str
    level: str
    country: str | None
    parent: str | None


class TerritoryDataError(ValueError):
    """Indica que un dataset territorial local no es válido."""


def _number(
    value: Any,
    *,
    field: str,
) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
    ):
        raise TerritoryDataError(
            f"{field} debe ser numérico"
        )

    normalized = float(value)

    if not math.isfinite(normalized):
        raise TerritoryDataError(
            f"{field} debe ser finito"
        )

    return normalized


def _coordinate(
    value: Any,
) -> Point:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or len(value) < 2
    ):
        raise TerritoryDataError(
            "Coordenada GeoJSON inválida"
        )

    longitude = _number(
        value[0],
        field="longitude",
    )
    latitude = _number(
        value[1],
        field="latitude",
    )

    if not -180 <= longitude <= 180:
        raise TerritoryDataError(
            "longitude está fuera de rango"
        )

    if not -90 <= latitude <= 90:
        raise TerritoryDataError(
            "latitude está fuera de rango"
        )

    return longitude, latitude


def _ring(
    value: Any,
) -> Ring:
    if not isinstance(value, list):
        raise TerritoryDataError(
            "Un anillo GeoJSON debe ser una lista"
        )

    points = tuple(
        _coordinate(coordinate)
        for coordinate in value
    )

    if len(points) < 4:
        raise TerritoryDataError(
            "Un anillo GeoJSON necesita al menos 4 puntos"
        )

    if points[0] != points[-1]:
        raise TerritoryDataError(
            "Un anillo GeoJSON debe estar cerrado"
        )

    return points


def _polygon(
    value: Any,
) -> Polygon:
    if not isinstance(value, list) or not value:
        raise TerritoryDataError(
            "Un polígono GeoJSON debe contener anillos"
        )

    return tuple(
        _ring(ring)
        for ring in value
    )


def _geometry_polygons(
    geometry: Any,
) -> tuple[Polygon, ...]:
    if not isinstance(geometry, Mapping):
        raise TerritoryDataError(
            "geometry debe ser un objeto"
        )

    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")

    if geometry_type == "Polygon":
        return (
            _polygon(coordinates),
        )

    if geometry_type == "MultiPolygon":
        if not isinstance(coordinates, list):
            raise TerritoryDataError(
                "MultiPolygon.coordinates debe ser una lista"
            )

        return tuple(
            _polygon(polygon)
            for polygon in coordinates
        )

    raise TerritoryDataError(
        "Solo se admiten Polygon y MultiPolygon"
    )


def _point_on_segment(
    point: Point,
    start: Point,
    end: Point,
) -> bool:
    px, py = point
    ax, ay = start
    bx, by = end

    cross = (
        (px - ax) * (by - ay)
        - (py - ay) * (bx - ax)
    )

    if abs(cross) > 1e-12:
        return False

    return (
        min(ax, bx) - 1e-12
        <= px
        <= max(ax, bx) + 1e-12
        and min(ay, by) - 1e-12
        <= py
        <= max(ay, by) + 1e-12
    )


def _point_in_ring(
    point: Point,
    ring: Ring,
) -> bool:
    """Ray casting; los puntos sobre el borde cuentan como dentro."""

    px, py = point
    inside = False

    for index in range(len(ring) - 1):
        start = ring[index]
        end = ring[index + 1]

        if _point_on_segment(
            point,
            start,
            end,
        ):
            return True

        ax, ay = start
        bx, by = end

        intersects = (
            (ay > py) != (by > py)
        )

        if not intersects:
            continue

        intersection_x = (
            (bx - ax)
            * (py - ay)
            / (by - ay)
            + ax
        )

        if px < intersection_x:
            inside = not inside

    return inside


def _point_in_polygon(
    point: Point,
    polygon: Polygon,
) -> bool:
    if not polygon:
        return False

    if not _point_in_ring(
        point,
        polygon[0],
    ):
        return False

    for hole in polygon[1:]:
        if _point_in_ring(
            point,
            hole,
        ):
            return False

    return True


def _bounds(
    polygons: tuple[Polygon, ...],
) -> tuple[
    float,
    float,
    float,
    float,
]:
    points = [
        point
        for polygon in polygons
        for ring in polygon
        for point in ring
    ]

    if not points:
        raise TerritoryDataError(
            "Territorio sin coordenadas"
        )

    longitudes = [
        point[0]
        for point in points
    ]
    latitudes = [
        point[1]
        for point in points
    ]

    return (
        min(latitudes),
        min(longitudes),
        max(latitudes),
        max(longitudes),
    )


def _required_text(
    properties: Mapping[str, Any],
    key: str,
) -> str:
    value = properties.get(key)

    if not isinstance(value, str):
        raise TerritoryDataError(
            f"properties.{key} debe ser texto"
        )

    normalized = value.strip()

    if not normalized:
        raise TerritoryDataError(
            f"properties.{key} no puede estar vacío"
        )

    return normalized


def _optional_text(
    properties: Mapping[str, Any],
    key: str,
) -> str | None:
    value = properties.get(key)

    if value is None:
        return None

    if not isinstance(value, str):
        raise TerritoryDataError(
            f"properties.{key} debe ser texto o null"
        )

    normalized = value.strip()

    return normalized or None


def territory_from_feature(
    feature: Any,
) -> Territory:
    """Normaliza una feature del contrato territorial local."""

    if not isinstance(feature, Mapping):
        raise TerritoryDataError(
            "Cada feature debe ser un objeto"
        )

    if feature.get("type") != "Feature":
        raise TerritoryDataError(
            "Cada entrada debe usar type=Feature"
        )

    properties = feature.get("properties")

    if not isinstance(properties, Mapping):
        raise TerritoryDataError(
            "Feature.properties debe ser un objeto"
        )

    polygons = _geometry_polygons(
        feature.get("geometry")
    )

    south, west, north, east = _bounds(
        polygons
    )

    return Territory(
        id=_required_text(
            properties,
            "id",
        ),
        name=_required_text(
            properties,
            "name",
        ),
        level=_required_text(
            properties,
            "level",
        ),
        country=_optional_text(
            properties,
            "country",
        ),
        parent=_optional_text(
            properties,
            "parent",
        ),
        polygons=polygons,
        south=south,
        west=west,
        north=north,
        east=east,
    )


@dataclass(frozen=True, slots=True)
class PrecisionCell:
    """Área aproximada compatible cunha posición Meshtastic."""

    south: float
    west: float
    north: float
    east: float

    def contains(
        self,
        latitude: float,
        longitude: float,
    ) -> bool:
        return (
            self.south <= latitude <= self.north
            and self.west <= longitude <= self.east
        )


@dataclass(frozen=True, slots=True)
class TerritoryClassification:
    """Resultado territorial tendo en conta a precisión da posición."""

    status: str
    exact: TerritoryMatch | None
    compatible: tuple[TerritoryMatch, ...]
    cell: PrecisionCell | None


def precision_cell(
    latitude: float,
    longitude: float,
    precision_bits: int,
) -> PrecisionCell:
    """Calcula a cela aproximada representada por Meshtastic.

    Meshtastic publica as coordenadas como enteiros en graos
    multiplicados por 10.000.000. Ao reducir os bits de precisión,
    os bits menos significativos deixan de representar unha
    coordenada exacta.

    A anchura empregada aquí é:

        2 ** (32 - precision_bits) / 10_000_000 graos

    A posición publicada úsase como centro aproximado da cela.
    """

    latitude_value = _number(
        latitude,
        field="latitude",
    )
    longitude_value = _number(
        longitude,
        field="longitude",
    )

    if not -90 <= latitude_value <= 90:
        raise ValueError(
            "latitude está fuera de rango"
        )

    if not -180 <= longitude_value <= 180:
        raise ValueError(
            "longitude está fuera de rango"
        )

    if (
        isinstance(precision_bits, bool)
        or not isinstance(precision_bits, int)
    ):
        raise TypeError(
            "precision_bits debe ser un entero"
        )

    if not 0 <= precision_bits <= 32:
        raise ValueError(
            "precision_bits debe estar entre 0 y 32"
        )

    size_degrees = (
        2 ** (32 - precision_bits)
        / 10_000_000
    )

    half = size_degrees / 2

    return PrecisionCell(
        south=max(
            -90.0,
            latitude_value - half,
        ),
        west=max(
            -180.0,
            longitude_value - half,
        ),
        north=min(
            90.0,
            latitude_value + half,
        ),
        east=min(
            180.0,
            longitude_value + half,
        ),
    )


def _point_in_rectangle(
    point: Point,
    cell: PrecisionCell,
) -> bool:
    longitude, latitude = point

    return cell.contains(
        latitude,
        longitude,
    )


def _orientation(
    start: Point,
    middle: Point,
    end: Point,
) -> float:
    return (
        (middle[1] - start[1])
        * (end[0] - middle[0])
        - (middle[0] - start[0])
        * (end[1] - middle[1])
    )


def _segments_intersect(
    first_start: Point,
    first_end: Point,
    second_start: Point,
    second_end: Point,
) -> bool:
    """Intersección de segmentos incluíndo contacto cos bordes."""

    if _point_on_segment(
        first_start,
        second_start,
        second_end,
    ):
        return True

    if _point_on_segment(
        first_end,
        second_start,
        second_end,
    ):
        return True

    if _point_on_segment(
        second_start,
        first_start,
        first_end,
    ):
        return True

    if _point_on_segment(
        second_end,
        first_start,
        first_end,
    ):
        return True

    o1 = _orientation(
        first_start,
        first_end,
        second_start,
    )
    o2 = _orientation(
        first_start,
        first_end,
        second_end,
    )
    o3 = _orientation(
        second_start,
        second_end,
        first_start,
    )
    o4 = _orientation(
        second_start,
        second_end,
        first_end,
    )

    return (
        (
            o1 > 0
            and o2 < 0
            or o1 < 0
            and o2 > 0
        )
        and (
            o3 > 0
            and o4 < 0
            or o3 < 0
            and o4 > 0
        )
    )


def _rectangle_corners(
    cell: PrecisionCell,
) -> tuple[Point, Point, Point, Point]:
    return (
        (cell.west, cell.south),
        (cell.east, cell.south),
        (cell.east, cell.north),
        (cell.west, cell.north),
    )


def _rectangle_edges(
    cell: PrecisionCell,
) -> tuple[
    tuple[Point, Point],
    ...,
]:
    corners = _rectangle_corners(
        cell
    )

    return (
        (
            corners[0],
            corners[1],
        ),
        (
            corners[1],
            corners[2],
        ),
        (
            corners[2],
            corners[3],
        ),
        (
            corners[3],
            corners[0],
        ),
    )


def _ring_intersects_rectangle(
    ring: Ring,
    cell: PrecisionCell,
) -> bool:
    rectangle_edges = _rectangle_edges(
        cell
    )

    for index in range(
        len(ring) - 1
    ):
        ring_start = ring[index]
        ring_end = ring[index + 1]

        for rectangle_start, rectangle_end in (
            rectangle_edges
        ):
            if _segments_intersect(
                ring_start,
                ring_end,
                rectangle_start,
                rectangle_end,
            ):
                return True

    return False


def _polygon_intersects_rectangle(
    polygon: Polygon,
    cell: PrecisionCell,
) -> bool:
    """Comproba se hai área ou bordo común entre polígono e cela."""

    if not polygon:
        return False

    # Se algunha esquina da cela pertence á superficie real
    # do polígono, existe intersección. ``_point_in_polygon``
    # xa respecta os ocos interiores.
    for corner in _rectangle_corners(
        cell
    ):
        if _point_in_polygon(
            corner,
            polygon,
        ):
            return True

    # Se o rectángulo contén un vértice do anel exterior,
    # tamén existe intersección. Non usamos aquí vértices
    # dos ocos: un rectángulo situado completamente dentro
    # dun oco non debe considerarse parte do territorio.
    outer_ring = polygon[0]

    if any(
        _point_in_rectangle(
            point,
            cell,
        )
        for point in outer_ring
    ):
        return True

    # Finalmente comprobamos cruces cos bordes. Inclúense
    # os aneis interiores porque tocar o bordo dun oco é
    # tamén contacto co límite administrativo.
    return any(
        _ring_intersects_rectangle(
            ring,
            cell,
        )
        for ring in polygon
    )


def territory_intersects_cell(
    territory: Territory,
    cell: PrecisionCell,
) -> bool:
    """Indica se unha cela de precisión intersecta un territorio."""

    if (
        cell.north < territory.south
        or cell.south > territory.north
        or cell.east < territory.west
        or cell.west > territory.east
    ):
        return False

    return any(
        _polygon_intersects_rectangle(
            polygon,
            cell,
        )
        for polygon in territory.polygons
    )


class TerritoryIndex:
    """Índice local para clasificación punto-en-polígono."""

    def __init__(
        self,
        territories: Iterable[Territory],
    ) -> None:
        values = tuple(territories)

        ids = [
            territory.id
            for territory in values
        ]

        if len(ids) != len(set(ids)):
            raise TerritoryDataError(
                "Hay identificadores territoriales duplicados"
            )

        self._territories = values

    @classmethod
    def from_geojson(
        cls,
        document: Any,
    ) -> "TerritoryIndex":
        if not isinstance(document, Mapping):
            raise TerritoryDataError(
                "La raíz GeoJSON debe ser un objeto"
            )

        if document.get("type") != "FeatureCollection":
            raise TerritoryDataError(
                "La raíz debe usar type=FeatureCollection"
            )

        features = document.get("features")

        if not isinstance(features, list):
            raise TerritoryDataError(
                "FeatureCollection.features debe ser una lista"
            )

        return cls(
            territory_from_feature(feature)
            for feature in features
        )

    @classmethod
    def from_path(
        cls,
        path: str | Path,
    ) -> "TerritoryIndex":
        source = Path(path)

        try:
            document = json.loads(
                source.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
        ) as exc:
            raise TerritoryDataError(
                f"No se pudo leer {source}"
            ) from exc

        return cls.from_geojson(
            document
        )

    @property
    def territories(
        self,
    ) -> tuple[Territory, ...]:
        return self._territories

    def find(
        self,
        latitude: float | None,
        longitude: float | None,
        *,
        level: str | None = None,
    ) -> tuple[TerritoryMatch, ...]:
        """Devuelve todos los territorios que contienen el punto."""

        if latitude is None or longitude is None:
            return ()

        latitude_value = _number(
            latitude,
            field="latitude",
        )
        longitude_value = _number(
            longitude,
            field="longitude",
        )

        if not -90 <= latitude_value <= 90:
            raise ValueError(
                "latitude está fuera de rango"
            )

        if not -180 <= longitude_value <= 180:
            raise ValueError(
                "longitude está fuera de rango"
            )

        normalized_level = (
            level.strip()
            if isinstance(level, str)
            else None
        )

        matches = []

        for territory in self._territories:
            if (
                normalized_level
                and territory.level != normalized_level
            ):
                continue

            if territory.contains(
                latitude_value,
                longitude_value,
            ):
                matches.append(
                    TerritoryMatch(
                        id=territory.id,
                        name=territory.name,
                        level=territory.level,
                        country=territory.country,
                        parent=territory.parent,
                    )
                )

        return tuple(matches)

    def classify(
        self,
        latitude: float | None,
        longitude: float | None,
        *,
        level: str,
        precision_bits: int | None = None,
    ) -> TerritoryClassification:
        """Clasifica un punto conservando a súa incerteza espacial.

        Estados:

        ``exact``
            O punto publicado cae dentro dun territorio.

        ``compatible``
            O punto publicado non cae dentro do polígono, pero a
            cela derivada da precisión só é compatible cun territorio.

        ``ambiguous``
            A cela é compatible con máis dun territorio.

        ``outside``
            Nin o punto nin a súa cela poden atribuírse a ningún
            territorio dese nivel.

        Se ``precision_bits`` é ``None`` non se inventa unha área
        de incerteza: só se realiza a clasificación exacta.
        """

        if latitude is None or longitude is None:
            return TerritoryClassification(
                status="outside",
                exact=None,
                compatible=(),
                cell=None,
            )

        exact_matches = self.find(
            latitude,
            longitude,
            level=level,
        )

        if len(exact_matches) > 1:
            raise TerritoryDataError(
                "El punto pertenece a más de un territorio "
                f"del nivel {level!r}"
            )

        exact = (
            exact_matches[0]
            if exact_matches
            else None
        )

        if exact is not None:
            return TerritoryClassification(
                status="exact",
                exact=exact,
                compatible=(
                    exact,
                ),
                cell=(
                    precision_cell(
                        latitude,
                        longitude,
                        precision_bits,
                    )
                    if precision_bits is not None
                    else None
                ),
            )

        if precision_bits is None:
            return TerritoryClassification(
                status="outside",
                exact=None,
                compatible=(),
                cell=None,
            )

        cell = precision_cell(
            latitude,
            longitude,
            precision_bits,
        )

        normalized_level = level.strip()

        compatible = tuple(
            TerritoryMatch(
                id=territory.id,
                name=territory.name,
                level=territory.level,
                country=territory.country,
                parent=territory.parent,
            )
            for territory in self._territories
            if (
                territory.level
                == normalized_level
                and territory_intersects_cell(
                    territory,
                    cell,
                )
            )
        )

        if len(compatible) == 1:
            status = "compatible"
        elif len(compatible) > 1:
            status = "ambiguous"
        else:
            status = "outside"

        return TerritoryClassification(
            status=status,
            exact=None,
            compatible=compatible,
            cell=cell,
        )

    def find_one(
        self,
        latitude: float | None,
        longitude: float | None,
        *,
        level: str,
    ) -> TerritoryMatch | None:
        """Busca un único territorio de un nivel administrativo."""

        matches = self.find(
            latitude,
            longitude,
            level=level,
        )

        if not matches:
            return None

        if len(matches) > 1:
            raise TerritoryDataError(
                "El punto pertenece a más de un territorio "
                f"del nivel {level!r}"
            )

        return matches[0]
