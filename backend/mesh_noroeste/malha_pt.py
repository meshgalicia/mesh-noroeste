"""Adaptador clean-room para los nodos de Malha Portugal."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import math
import re
from typing import Any

from mesh_noroeste.domain import (
    EdgeObservation,
    NodeObservation,
    make_edge_observation,
    make_observation,
)


_PUBLIC_ID = re.compile(r"^![0-9a-f]{8}$")


class MalhaPtError(ValueError):
    """Indica que un documento público de Malha no es válido."""


def _required(
    record: Mapping[Any, Any],
    key: str,
    index: int,
) -> Any:
    if key not in record:
        raise MalhaPtError(
            f"Registro {index}: falta el campo {key!r}"
        )

    return record[key]


def _public_id(
    value: Any,
    node_id: Any,
    index: int,
) -> str:
    if not isinstance(value, str):
        raise MalhaPtError(
            f"Registro {index}: hex_id debe ser texto"
        )

    normalized = value.strip().lower()

    if _PUBLIC_ID.fullmatch(normalized) is None:
        raise MalhaPtError(
            f"Registro {index}: hex_id debe usar !xxxxxxxx"
        )

    if (
        isinstance(node_id, bool)
        or not isinstance(node_id, int)
        or not 0 <= node_id <= 0xFFFFFFFF
    ):
        raise MalhaPtError(
            f"Registro {index}: node_id debe ser "
            "un entero de 32 bits"
        )

    expected = f"!{node_id:08x}"

    if normalized != expected:
        raise MalhaPtError(
            f"Registro {index}: hex_id y node_id "
            "no representan el mismo nodo"
        )

    return normalized


def _timestamp(
    value: Any,
    field: str,
    index: int,
) -> datetime:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
    ):
        raise MalhaPtError(
            f"Registro {index}: {field} debe ser numérico"
        )

    normalized = float(value)

    if not math.isfinite(normalized) or normalized < 0:
        raise MalhaPtError(
            f"Registro {index}: {field} debe ser "
            "finito y no negativo"
        )

    try:
        return datetime.fromtimestamp(
            normalized,
            tz=timezone.utc,
        )
    except (
        OverflowError,
        OSError,
        ValueError,
    ) as exc:
        raise MalhaPtError(
            f"Registro {index}: {field} está fuera de rango"
        ) from exc


def _nullable_text(
    value: Any,
    field: str,
    index: int,
) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise MalhaPtError(
            f"Registro {index}: {field} debe ser "
            "texto o null"
        )

    return value


def _nullable_number(
    value: Any,
    field: str,
    index: int,
) -> float | None:
    if value is None:
        return None

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
    ):
        raise MalhaPtError(
            f"Registro {index}: {field} debe ser "
            "numérico o null"
        )

    normalized = float(value)

    if not math.isfinite(normalized):
        raise MalhaPtError(
            f"Registro {index}: {field} debe ser finito"
        )

    return normalized


def _coordinates(
    latitude: Any,
    longitude: Any,
    index: int,
) -> tuple[float, float]:
    if (
        isinstance(latitude, bool)
        or not isinstance(latitude, (int, float))
        or isinstance(longitude, bool)
        or not isinstance(longitude, (int, float))
    ):
        raise MalhaPtError(
            f"Registro {index}: latitude y longitude "
            "deben ser numéricos"
        )

    normalized_latitude = float(latitude)
    normalized_longitude = float(longitude)

    if (
        not math.isfinite(normalized_latitude)
        or not math.isfinite(normalized_longitude)
    ):
        raise MalhaPtError(
            f"Registro {index}: latitude y longitude "
            "deben ser finitos"
        )

    if not -90 <= normalized_latitude <= 90:
        raise MalhaPtError(
            f"Registro {index}: latitude está fuera de rango"
        )

    if not -180 <= normalized_longitude <= 180:
        raise MalhaPtError(
            f"Registro {index}: longitude está fuera de rango"
        )

    if (
        normalized_latitude == 0
        and normalized_longitude == 0
    ):
        raise MalhaPtError(
            f"Registro {index}: la posición 0,0 no es válida"
        )

    return normalized_latitude, normalized_longitude


def parse_malha_pt(
    document: Any,
) -> tuple[NodeObservation, ...]:
    """Normaliza la lista pública de nodos de Malha Portugal."""

    if not isinstance(document, Mapping):
        raise MalhaPtError(
            "La raíz de Malha debe ser un objeto"
        )

    if "locations" not in document:
        raise MalhaPtError(
            "La raíz de Malha no contiene 'locations'"
        )

    records = document["locations"]

    if not isinstance(records, list):
        raise MalhaPtError(
            "El campo 'locations' debe ser una lista"
        )

    observations: list[NodeObservation] = []
    seen_ids: set[str] = set()

    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise MalhaPtError(
                f"Registro {index}: debe ser un objeto"
            )

        source_id = _public_id(
            _required(record, "hex_id", index),
            _required(record, "node_id", index),
            index,
        )

        if source_id in seen_ids:
            raise MalhaPtError(
                f"Registro {index}: id duplicado {source_id}"
            )

        seen_ids.add(source_id)

        observed_at = _timestamp(
            _required(record, "timestamp", index),
            "timestamp",
            index,
        )

        latitude, longitude = _coordinates(
            _required(record, "latitude", index),
            _required(record, "longitude", index),
            index,
        )

        try:
            observation = make_observation(
                source="malha_pt",
                network="meshtastic",
                source_id=source_id,
                observed_at=observed_at,
                short_name=_nullable_text(
                    _required(
                        record,
                        "short_name",
                        index,
                    ),
                    "short_name",
                    index,
                ),
                long_name=_nullable_text(
                    _required(
                        record,
                        "long_name",
                        index,
                    ),
                    "long_name",
                    index,
                ),
                hardware=_nullable_text(
                    _required(
                        record,
                        "hw_model",
                        index,
                    ),
                    "hw_model",
                    index,
                ),
                role=_nullable_text(
                    _required(record, "role", index),
                    "role",
                    index,
                ),
                latitude=latitude,
                longitude=longitude,
                altitude_m=_nullable_number(
                    _required(
                        record,
                        "altitude",
                        index,
                    ),
                    "altitude",
                    index,
                ),
                position_updated_at=observed_at,
                metrics={
                    "snr_db": _nullable_number(
                        _required(
                            record,
                            "avg_snr",
                            index,
                        ),
                        "avg_snr",
                        index,
                    ),
                },
                radio={
                    "channel": _nullable_text(
                        _required(
                            record,
                            "primary_channel",
                            index,
                        ),
                        "primary_channel",
                        index,
                    ),
                },
            )
        except MalhaPtError:
            raise
        except (TypeError, ValueError) as exc:
            raise MalhaPtError(
                f"Registro {index}: {exc}"
            ) from exc

        observations.append(observation)

    return tuple(observations)


def _node_id(
    value: Any,
    field: str,
    index: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value <= 0xFFFFFFFF
    ):
        raise MalhaPtError(
            f"Traceroute {index}: {field} debe ser "
            "un entero de 32 bits"
        )

    return value


def parse_malha_pt_traceroutes(
    document: Any,
) -> tuple[EdgeObservation, ...]:
    """Normaliza los traceroutes públicos de Malha Portugal."""

    if not isinstance(document, Mapping):
        raise MalhaPtError(
            "La raíz de Malha debe ser un objeto"
        )

    if "traceroute_links" not in document:
        raise MalhaPtError(
            "La raíz de Malha no contiene "
            "'traceroute_links'"
        )

    records = document["traceroute_links"]

    if not isinstance(records, list):
        raise MalhaPtError(
            "El campo 'traceroute_links' debe ser "
            "una lista"
        )

    observations: list[EdgeObservation] = []
    seen_ids: set[str] = set()

    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise MalhaPtError(
                f"Traceroute {index}: debe ser un objeto"
            )

        from_node_id = _node_id(
            _required(
                record,
                "from_node_id",
                index,
            ),
            "from_node_id",
            index,
        )
        to_node_id = _node_id(
            _required(
                record,
                "to_node_id",
                index,
            ),
            "to_node_id",
            index,
        )

        if from_node_id == to_node_id:
            continue

        observed_at = _timestamp(
            _required(record, "last_seen", index),
            "last_seen",
            index,
        )

        try:
            observation = make_edge_observation(
                source="malha_pt",
                network="meshtastic",
                from_source_id=from_node_id,
                to_source_id=to_node_id,
                edge_type="traceroute",
                directed=True,
                observed_at=observed_at,
                metrics={
                    "snr_db": _nullable_number(
                        _required(
                            record,
                            "avg_snr",
                            index,
                        ),
                        "avg_snr",
                        index,
                    ),
                },
            )
        except MalhaPtError:
            raise
        except (TypeError, ValueError) as exc:
            raise MalhaPtError(
                f"Traceroute {index}: {exc}"
            ) from exc

        if observation.id in seen_ids:
            raise MalhaPtError(
                f"Traceroute {index}: conexión duplicada "
                f"{observation.id}"
            )

        seen_ids.add(observation.id)
        observations.append(observation)

    return tuple(observations)
