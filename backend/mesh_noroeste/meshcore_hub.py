"""Adaptador clean-room para os nodos de MeshCore Hub."""

from __future__ import annotations

from collections.abc import Mapping
import math
import re
from typing import Any

from mesh_noroeste.domain import (
    NodeObservation,
    make_observation,
)


_PUBLIC_KEY = re.compile(r"^[0-9a-f]{64}$")

_NODE_TYPES = {
    "chat": "client",
    "client": "client",
    "repeater": "repeater",
    "room": "room_server",
    "room_server": "room_server",
    "sensor": "sensor",
    "unknown": "unknown",
}


class MeshCoreHubError(ValueError):
    """Indica que unha resposta de MeshCore Hub non é válida."""


def _required(
    record: Mapping[Any, Any],
    key: str,
    index: int,
) -> Any:
    if key not in record:
        raise MeshCoreHubError(
            f"Nodo {index}: falta o campo {key!r}"
        )

    return record[key]


def _public_key(value: Any, index: int) -> str:
    if not isinstance(value, str):
        raise MeshCoreHubError(
            f"Nodo {index}: public_key debe ser texto"
        )

    normalized = value.strip().lower()

    if _PUBLIC_KEY.fullmatch(normalized) is None:
        raise MeshCoreHubError(
            f"Nodo {index}: public_key debe conter "
            "64 caracteres hexadecimais"
        )

    return normalized


def _optional_text(
    value: Any,
    field: str,
    index: int,
) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise MeshCoreHubError(
            f"Nodo {index}: {field} debe ser texto ou null"
        )

    return value


def _timestamp(
    value: Any,
    field: str,
    index: int,
) -> str:
    if not isinstance(value, str):
        raise MeshCoreHubError(
            f"Nodo {index}: {field} debe ser texto"
        )

    normalized = value.strip()

    if not normalized:
        raise MeshCoreHubError(
            f"Nodo {index}: {field} non pode estar baleiro"
        )

    return normalized


def _node_type(value: Any, index: int) -> str:
    if value is None:
        return "unknown"

    if not isinstance(value, str):
        raise MeshCoreHubError(
            f"Nodo {index}: adv_type debe ser texto ou null"
        )

    normalized = value.strip().lower()

    if not normalized:
        return "unknown"

    return _NODE_TYPES.get(normalized, "unknown")


def _nullable_integer(
    value: Any,
    field: str,
    index: int,
) -> int | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, int):
        raise MeshCoreHubError(
            f"Nodo {index}: {field} debe ser un enteiro ou null"
        )

    return value


def _boolean(
    value: Any,
    field: str,
    index: int,
) -> bool:
    if not isinstance(value, bool):
        raise MeshCoreHubError(
            f"Nodo {index}: {field} debe ser booleano"
        )

    return value


def _coordinates(
    latitude: Any,
    longitude: Any,
    index: int,
) -> tuple[float | None, float | None]:
    if latitude is None and longitude is None:
        return None, None

    if latitude is None or longitude is None:
        raise MeshCoreHubError(
            f"Nodo {index}: lat e lon deben aparecer xuntas"
        )

    if (
        isinstance(latitude, bool)
        or not isinstance(latitude, (int, float))
        or isinstance(longitude, bool)
        or not isinstance(longitude, (int, float))
    ):
        raise MeshCoreHubError(
            f"Nodo {index}: lat e lon deben ser numéricas"
        )

    normalized_latitude = float(latitude)
    normalized_longitude = float(longitude)

    if (
        not math.isfinite(normalized_latitude)
        or not math.isfinite(normalized_longitude)
    ):
        raise MeshCoreHubError(
            f"Nodo {index}: lat e lon deben ser finitas"
        )

    if not -90 <= normalized_latitude <= 90:
        raise MeshCoreHubError(
            f"Nodo {index}: lat está fóra de rango"
        )

    if not -180 <= normalized_longitude <= 180:
        raise MeshCoreHubError(
            f"Nodo {index}: lon está fóra de rango"
        )

    if normalized_latitude == 0 and normalized_longitude == 0:
        return None, None

    return normalized_latitude, normalized_longitude


def _tags(value: Any, index: int) -> None:
    if not isinstance(value, list):
        raise MeshCoreHubError(
            f"Nodo {index}: tags debe ser unha lista"
        )

    for tag_index, tag in enumerate(value):
        if not isinstance(tag, Mapping):
            raise MeshCoreHubError(
                f"Nodo {index}: tag {tag_index} debe ser "
                "un obxecto"
            )


def parse_meshcore_hub_nodes(
    document: Any,
    *,
    source: str,
) -> tuple[NodeObservation, ...]:
    """Normaliza unha páxina de ``/api/v1/nodes`` do Hub."""

    if not isinstance(source, str):
        raise TypeError("source debe ser texto")

    if not isinstance(document, Mapping):
        raise MeshCoreHubError(
            "A raíz de MeshCore Hub debe ser un obxecto"
        )

    records = document.get("items")

    if not isinstance(records, list):
        raise MeshCoreHubError(
            "O campo 'items' de MeshCore Hub debe ser unha lista"
        )

    observations: list[NodeObservation] = []
    seen_ids: set[str] = set()

    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise MeshCoreHubError(
                f"Nodo {index}: debe ser un obxecto"
            )

        source_id = _public_key(
            _required(record, "public_key", index),
            index,
        )

        if source_id in seen_ids:
            raise MeshCoreHubError(
                f"Nodo {index}: public_key duplicada {source_id}"
            )

        seen_ids.add(source_id)

        first_seen = _timestamp(
            _required(record, "first_seen", index),
            "first_seen",
            index,
        )
        last_seen = _timestamp(
            _required(record, "last_seen", index),
            "last_seen",
            index,
        )

        latitude, longitude = _coordinates(
            _required(record, "lat", index),
            _required(record, "lon", index),
            index,
        )

        _nullable_integer(
            _required(record, "flags", index),
            "flags",
            index,
        )
        _boolean(
            _required(record, "is_observer", index),
            "is_observer",
            index,
        )
        _tags(
            _required(record, "tags", index),
            index,
        )

        try:
            observation = make_observation(
                source=source,
                network="meshcore",
                source_id=source_id,
                observed_at=last_seen,
                first_seen=first_seen,
                short_name=_optional_text(
                    _required(record, "name", index),
                    "name",
                    index,
                ),
                node_type=_node_type(
                    _required(record, "adv_type", index),
                    index,
                ),
                latitude=latitude,
                longitude=longitude,
                position_updated_at=(
                    last_seen
                    if latitude is not None
                    else None
                ),
            )
        except MeshCoreHubError:
            raise
        except (TypeError, ValueError) as exc:
            raise MeshCoreHubError(
                f"Nodo {index}: {exc}"
            ) from exc

        observations.append(observation)

    return tuple(observations)
