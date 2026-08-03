"""Adaptador clean-room para Meshview España."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any

from mesh_noroeste.domain import (
    EdgeObservation,
    NodeObservation,
    make_edge_observation,
    make_observation,
)


_PUBLIC_ID = re.compile(r"^![0-9a-f]{8}$")


class MeshviewEsError(ValueError):
    """Indica que un documento de Meshview no es válido."""


@dataclass(frozen=True, slots=True)
class MeshviewPositionPrecision:
    """Precisión asociada a una posición publicada."""

    latitude_i: int
    longitude_i: int
    precision_bits: int
    import_time_us: int


def _required(
    record: Mapping[Any, Any],
    key: str,
    index: int,
) -> Any:
    if key not in record:
        raise MeshviewEsError(
            f"Registro {index}: falta el campo {key!r}"
        )

    return record[key]


def _public_id(
    value: Any,
    node_id: Any,
    index: int,
) -> str:
    if not isinstance(value, str):
        raise MeshviewEsError(
            f"Registro {index}: id debe ser texto"
        )

    normalized = value.strip().lower()

    if _PUBLIC_ID.fullmatch(normalized) is None:
        raise MeshviewEsError(
            f"Registro {index}: id debe usar !xxxxxxxx"
        )

    if (
        isinstance(node_id, bool)
        or not isinstance(node_id, int)
        or not 0 <= node_id <= 0xFFFFFFFF
    ):
        raise MeshviewEsError(
            f"Registro {index}: node_id debe ser "
            "un entero de 32 bits"
        )

    expected = f"!{node_id:08x}"

    if normalized != expected:
        raise MeshviewEsError(
            f"Registro {index}: id y node_id "
            "no representan el mismo nodo"
        )

    return normalized


def _microsecond_timestamp(
    value: Any,
    field: str,
    index: int,
) -> datetime:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
    ):
        raise MeshviewEsError(
            f"Registro {index}: {field} debe ser "
            "un entero positivo en microsegundos"
        )

    seconds, microseconds = divmod(value, 1_000_000)

    try:
        return datetime.fromtimestamp(
            seconds,
            tz=timezone.utc,
        ).replace(microsecond=microseconds)
    except (
        OverflowError,
        OSError,
        ValueError,
    ) as exc:
        raise MeshviewEsError(
            f"Registro {index}: {field} está fuera de rango"
        ) from exc


def _text(
    value: Any,
    field: str,
    index: int,
    *,
    nullable: bool = False,
) -> str | None:
    if value is None and nullable:
        return None

    if not isinstance(value, str):
        suffix = " o null" if nullable else ""

        raise MeshviewEsError(
            f"Registro {index}: {field} debe ser "
            f"texto{suffix}"
        )

    return value


def _optional_boolean(
    value: Any,
    field: str,
    index: int,
) -> bool | None:
    if value is None:
        return None

    if not isinstance(value, bool):
        raise MeshviewEsError(
            f"Registro {index}: {field} debe ser "
            "booleano o null"
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
        raise MeshviewEsError(
            f"Registro {index}: last_lat y last_long "
            "deben aparecer juntos"
        )

    if (
        isinstance(latitude, bool)
        or isinstance(longitude, bool)
        or not isinstance(latitude, int)
        or not isinstance(longitude, int)
    ):
        raise MeshviewEsError(
            f"Registro {index}: last_lat y last_long "
            "deben ser enteros o null"
        )

    return (
        latitude / 10_000_000,
        longitude / 10_000_000,
    )



def _edge_required(
    record: Mapping[Any, Any],
    key: str,
    index: int,
) -> Any:
    if key not in record:
        raise MeshviewEsError(
            f"Conexión {index}: falta el campo {key!r}"
        )

    return record[key]


def _edge_endpoint(
    value: Any,
    field: str,
    index: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value <= 0xFFFFFFFF
    ):
        raise MeshviewEsError(
            f"Conexión {index}: {field} debe ser "
            "un entero de 32 bits"
        )

    return value


def parse_meshview_es_edges(
    document: Any,
    *,
    edge_type: str,
    observed_at: datetime | str | int | float,
    source: str = "meshview_es",
) -> tuple[EdgeObservation, ...]:
    """Normaliza conexiones públicas compatibles con Meshview."""

    if not isinstance(source, str):
        raise TypeError("source debe ser texto")

    normalized_source = source.strip().lower()

    if not isinstance(edge_type, str):
        raise TypeError("edge_type debe ser texto")

    normalized_type = edge_type.strip().lower()

    if normalized_type not in {
        "neighbor",
        "traceroute",
    }:
        raise MeshviewEsError(
            "edge_type debe ser neighbor o traceroute"
        )

    if not isinstance(document, Mapping):
        raise MeshviewEsError(
            "La raíz de conexiones de Meshview "
            "debe ser un objeto"
        )

    if "edges" not in document:
        raise MeshviewEsError(
            "La raíz de conexiones de Meshview "
            "no contiene 'edges'"
        )

    records = document["edges"]

    if not isinstance(records, list):
        raise MeshviewEsError(
            "El campo 'edges' debe ser una lista"
        )

    directed = normalized_type == "traceroute"
    observations: list[EdgeObservation] = []
    seen_ids: set[str] = set()

    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise MeshviewEsError(
                f"Conexión {index}: debe ser un objeto"
            )

        source_id = _edge_endpoint(
            _edge_required(record, "from", index),
            "from",
            index,
        )
        target_id = _edge_endpoint(
            _edge_required(record, "to", index),
            "to",
            index,
        )
        published_type = _edge_required(
            record,
            "type",
            index,
        )

        if not isinstance(published_type, str):
            raise MeshviewEsError(
                f"Conexión {index}: type debe ser texto"
            )

        published_type = published_type.strip().lower()

        if published_type != normalized_type:
            raise MeshviewEsError(
                f"Conexión {index}: type debe ser "
                f"{normalized_type!r}"
            )

        if source_id == target_id:
            continue

        try:
            observation = make_edge_observation(
                source=normalized_source,
                network="meshtastic",
                from_source_id=source_id,
                to_source_id=target_id,
                edge_type=normalized_type,
                directed=directed,
                observed_at=observed_at,
            )
        except (TypeError, ValueError) as exc:
            raise MeshviewEsError(
                f"Conexión {index}: {exc}"
            ) from exc

        if observation.id in seen_ids:
            continue

        seen_ids.add(observation.id)
        observations.append(observation)

    return tuple(observations)


def parse_meshview_es_position_precisions(
    document: Any,
) -> dict[str, MeshviewPositionPrecision]:
    """Extrae la precisión más reciente por nodo."""

    if not isinstance(document, Mapping):
        raise MeshviewEsError(
            "La raíz de paquetes de Meshview debe ser un objeto"
        )

    if "packets" not in document:
        raise MeshviewEsError(
            "La raíz de paquetes de Meshview no contiene "
            "'packets'"
        )

    records = document["packets"]

    if not isinstance(records, list):
        raise MeshviewEsError(
            "El campo 'packets' debe ser una lista"
        )

    latest: dict[str, MeshviewPositionPrecision] = {}

    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise MeshviewEsError(
                f"Paquete {index}: debe ser un objeto"
            )

        node_id = record.get("from_node_id")
        imported_at = record.get("import_time_us")
        payload = record.get("payload")

        if (
            isinstance(node_id, bool)
            or not isinstance(node_id, int)
            or not 0 <= node_id <= 0xFFFFFFFF
        ):
            raise MeshviewEsError(
                f"Paquete {index}: from_node_id debe ser "
                "un entero de 32 bits"
            )

        _microsecond_timestamp(
            imported_at,
            "import_time_us",
            index,
        )

        if not isinstance(payload, str):
            raise MeshviewEsError(
                f"Paquete {index}: payload debe ser texto"
            )

        fields = {
            key: int(value)
            for key, value in re.findall(
                r"^(latitude_i|longitude_i|precision_bits):"
                r"\s*(-?\d+)\s*$",
                payload,
                flags=re.MULTILINE,
            )
        }

        if not {
            "latitude_i",
            "longitude_i",
            "precision_bits",
        }.issubset(fields):
            continue

        latitude_i = fields["latitude_i"]
        longitude_i = fields["longitude_i"]
        precision_bits = fields["precision_bits"]

        if not -900_000_000 <= latitude_i <= 900_000_000:
            continue

        if not -1_800_000_000 <= longitude_i <= 1_800_000_000:
            continue

        if not 0 <= precision_bits <= 32:
            continue

        source_id = f"!{node_id:08x}"
        candidate = MeshviewPositionPrecision(
            latitude_i=latitude_i,
            longitude_i=longitude_i,
            precision_bits=precision_bits,
            import_time_us=imported_at,
        )
        previous = latest.get(source_id)

        if (
            previous is None
            or candidate.import_time_us
            > previous.import_time_us
        ):
            latest[source_id] = candidate

    return latest

def parse_meshview_es(
    document: Any,
    *,
    position_precisions: Mapping[
        str,
        MeshviewPositionPrecision,
    ] | None = None,
    source: str = "meshview_es",
) -> tuple[NodeObservation, ...]:
    """Normaliza un documento JSON público compatible con Meshview."""

    if not isinstance(source, str):
        raise TypeError("source debe ser texto")

    normalized_source = source.strip().lower()

    if not isinstance(document, Mapping):
        raise MeshviewEsError(
            "La raíz de Meshview debe ser un objeto"
        )

    if "nodes" not in document:
        raise MeshviewEsError(
            "La raíz de Meshview no contiene 'nodes'"
        )

    records = document["nodes"]

    if not isinstance(records, list):
        raise MeshviewEsError(
            "El campo 'nodes' debe ser una lista"
        )

    if position_precisions is None:
        precision_by_id: Mapping[
            str,
            MeshviewPositionPrecision,
        ] = {}
    elif not isinstance(position_precisions, Mapping):
        raise TypeError(
            "position_precisions debe ser un objeto"
        )
    else:
        precision_by_id = position_precisions

        for source_id, precision in precision_by_id.items():
            if (
                not isinstance(source_id, str)
                or _PUBLIC_ID.fullmatch(source_id) is None
                or not isinstance(
                    precision,
                    MeshviewPositionPrecision,
                )
            ):
                raise TypeError(
                    "position_precisions contiene "
                    "una entrada inválida"
                )

    observations: list[NodeObservation] = []
    seen_ids: set[str] = set()

    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise MeshviewEsError(
                f"Registro {index}: debe ser un objeto"
            )

        source_id = _public_id(
            _required(record, "id", index),
            _required(record, "node_id", index),
            index,
        )

        if source_id in seen_ids:
            raise MeshviewEsError(
                f"Registro {index}: id duplicado {source_id}"
            )

        seen_ids.add(source_id)

        first_seen = _microsecond_timestamp(
            _required(record, "first_seen_us", index),
            "first_seen_us",
            index,
        )
        observed_at = _microsecond_timestamp(
            _required(record, "last_seen_us", index),
            "last_seen_us",
            index,
        )
        raw_latitude = _required(
            record,
            "last_lat",
            index,
        )
        raw_longitude = _required(
            record,
            "last_long",
            index,
        )
        latitude, longitude = _coordinates(
            raw_latitude,
            raw_longitude,
            index,
        )

        precision = precision_by_id.get(source_id)
        position_precision_bits = None

        if (
            latitude is not None
            and precision is not None
            and precision.latitude_i == raw_latitude
            and precision.longitude_i == raw_longitude
        ):
            position_precision_bits = (
                precision.precision_bits
            )

        try:
            observation = make_observation(
                source=normalized_source,
                network="meshtastic",
                source_id=source_id,
                observed_at=observed_at,
                first_seen=first_seen,
                short_name=_text(
                    _required(record, "short_name", index),
                    "short_name",
                    index,
                ),
                long_name=_text(
                    _required(record, "long_name", index),
                    "long_name",
                    index,
                ),
                hardware=_text(
                    _required(record, "hw_model", index),
                    "hw_model",
                    index,
                ),
                role=_text(
                    _required(record, "role", index),
                    "role",
                    index,
                ),
                latitude=latitude,
                longitude=longitude,
                position_precision_bits=(
                    position_precision_bits
                ),
                position_updated_at=(
                    observed_at
                    if latitude is not None
                    else None
                ),
                radio={
                    "channel": _text(
                        _required(record, "channel", index),
                        "channel",
                        index,
                    ),
                    "firmware": _text(
                        _required(record, "firmware", index),
                        "firmware",
                        index,
                        nullable=True,
                    ),
                    "mqtt_gateway": _optional_boolean(
                        _required(
                            record,
                            "is_mqtt_gateway",
                            index,
                        ),
                        "is_mqtt_gateway",
                        index,
                    ),
                },
            )
        except MeshviewEsError:
            raise
        except (TypeError, ValueError) as exc:
            raise MeshviewEsError(
                f"Registro {index}: {exc}"
            ) from exc

        observations.append(observation)

    return tuple(observations)
