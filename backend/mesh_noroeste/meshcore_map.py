"""Adaptador clean-room para MeshCore Map."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import re
from typing import Any

import msgpack

from mesh_noroeste.domain import (
    NodeObservation,
    make_observation,
)


MESHCORE_NODE_TYPES = {
    1: "client",
    2: "repeater",
    3: "room_server",
    4: "sensor",
}

_PUBLIC_KEY = re.compile(r"^[0-9a-f]{64}$")


class MeshCoreMapError(ValueError):
    """Indica que un documento de MeshCore Map no es válido."""


def _required(
    record: Mapping[Any, Any],
    key: str,
    index: int,
) -> Any:
    if key not in record:
        raise MeshCoreMapError(
            f"Registro {index}: falta el campo {key!r}"
        )

    return record[key]


def _public_key(value: Any, index: int) -> str:
    if isinstance(value, bytes):
        if len(value) != 32:
            raise MeshCoreMapError(
                f"Registro {index}: pk debe contener "
                "32 bytes"
            )

        normalized = value.hex()

    elif isinstance(value, str):
        normalized = value.strip().lower()

    else:
        raise MeshCoreMapError(
            f"Registro {index}: pk debe ser binario "
            "o texto hexadecimal"
        )

    if _PUBLIC_KEY.fullmatch(normalized) is None:
        raise MeshCoreMapError(
            f"Registro {index}: pk debe contener "
            "64 caracteres hexadecimales"
        )

    return normalized


def _timestamp(value: Any, field: str, index: int) -> Any:
    if isinstance(value, msgpack.Timestamp):
        try:
            result = datetime.fromtimestamp(
                value.seconds,
                tz=timezone.utc,
            )
        except (
            OverflowError,
            OSError,
            ValueError,
        ) as exc:
            raise MeshCoreMapError(
                f"Registro {index}: {field} está "
                "fuera de rango"
            ) from exc

        return result.replace(
            microsecond=value.nanoseconds // 1_000
        )

    if isinstance(
        value,
        (datetime, str, int, float),
    ) and not isinstance(value, bool):
        return value

    raise MeshCoreMapError(
        f"Registro {index}: {field} no es "
        "un timestamp válido"
    )


def _name(value: Any, index: int) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise MeshCoreMapError(
            f"Registro {index}: n debe ser texto "
            "o null"
        )

    return value


def _node_type(value: Any, index: int) -> str:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise MeshCoreMapError(
            f"Registro {index}: t debe ser entero"
        )

    return MESHCORE_NODE_TYPES.get(
        value,
        "unknown",
    )


def _radio(
    value: Any,
    index: int,
) -> dict[str, Any]:
    if value is None:
        source: Mapping[Any, Any] = {}
    elif isinstance(value, Mapping):
        source = value
    else:
        raise MeshCoreMapError(
            f"Registro {index}: p debe ser "
            "un objeto o null"
        )

    return {
        "frequency_mhz": source.get("freq"),
        "bandwidth_khz": source.get("bw"),
        "spreading_factor": source.get("sf"),
        "coding_rate": source.get("cr"),
    }


def parse_meshcore_map(
    payload: bytes,
) -> tuple[NodeObservation, ...]:
    """Decodifica el documento compacto de MeshCore Map."""

    if not isinstance(payload, bytes):
        raise TypeError(
            "El documento MessagePack debe ser bytes"
        )

    if not payload:
        raise MeshCoreMapError(
            "El documento MessagePack está vacío"
        )

    try:
        document = msgpack.unpackb(
            payload,
            raw=False,
            strict_map_key=False,
            timestamp=0,
        )
    except Exception as exc:
        raise MeshCoreMapError(
            "El documento no contiene MessagePack válido"
        ) from exc

    if not isinstance(document, list):
        raise MeshCoreMapError(
            "La raíz de MeshCore Map debe ser una lista"
        )

    observations: list[NodeObservation] = []

    for index, record in enumerate(document):
        if not isinstance(record, Mapping):
            raise MeshCoreMapError(
                f"Registro {index}: debe ser un objeto"
            )

        source_id = _public_key(
            _required(record, "pk", index),
            index,
        )
        inserted_at = _timestamp(
            _required(record, "id", index),
            "id",
            index,
        )
        updated_at = _timestamp(
            _required(record, "ud", index),
            "ud",
            index,
        )

        try:
            observation = make_observation(
                source="meshcore_map",
                network="meshcore",
                source_id=source_id,
                observed_at=updated_at,
                first_seen=inserted_at,
                short_name=_name(
                    record.get("n"),
                    index,
                ),
                node_type=_node_type(
                    _required(record, "t", index),
                    index,
                ),
                latitude=_required(
                    record,
                    "lat",
                    index,
                ),
                longitude=_required(
                    record,
                    "lon",
                    index,
                ),
                position_updated_at=updated_at,
                radio=_radio(
                    record.get("p"),
                    index,
                ),
            )
        except MeshCoreMapError:
            raise
        except (TypeError, ValueError) as exc:
            raise MeshCoreMapError(
                f"Registro {index}: {exc}"
            ) from exc

        observations.append(observation)

    return tuple(observations)
