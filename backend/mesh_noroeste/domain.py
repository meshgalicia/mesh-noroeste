"""Modelo interno de observaciones de nodos y conexiones."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from typing import Any, Iterable, Mapping

from mesh_noroeste.normalization import (
    canonical_node_id,
    normalize_coordinates,
    normalize_meshcore_id,
    normalize_meshtastic_id,
    normalize_timestamp,
)


SOURCE_ORDER = {
    "meshview_es": 0,
    "malha_pt": 1,
    "ozulo_map": 2,
    "meshcore_map": 3,
    "meshcore_hub": 4,
}

MESHCORE_SOURCES = frozenset({
    "meshcore_map",
    "meshcore_hub",
})

METRIC_KEYS = (
    "battery_percent",
    "voltage_v",
    "channel_utilization_percent",
    "air_util_tx_percent",
    "snr_db",
    "rssi_dbm",
)

RADIO_KEYS = (
    "channel",
    "firmware",
    "hops_away",
    "mqtt_gateway",
    "frequency_mhz",
    "bandwidth_khz",
    "spreading_factor",
    "coding_rate",
)

MESHCORE_NODE_TYPES = {
    "client",
    "repeater",
    "room_server",
    "sensor",
    "unknown",
}

EDGE_TYPES = {
    "neighbor",
    "traceroute",
    "observed",
    "unknown",
}


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def _optional_text(
    value: Any,
    field_name: str,
    maximum_length: int,
) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} debe ser texto o null"
        )

    normalized = value.strip()

    if not normalized:
        return None

    if len(normalized) > maximum_length:
        raise ValueError(
            f"{field_name} supera {maximum_length} caracteres"
        )

    return normalized


def _optional_number(
    value: Any,
    field_name: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} no puede ser booleano"
        )

    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} debe ser numérico o null"
        ) from exc

    if not math.isfinite(normalized):
        raise ValueError(
            f"{field_name} debe ser finito"
        )

    if minimum is not None and normalized < minimum:
        raise ValueError(
            f"{field_name} no puede ser menor que {minimum}"
        )

    if maximum is not None and normalized > maximum:
        raise ValueError(
            f"{field_name} no puede superar {maximum}"
        )

    return normalized


def _optional_integer(
    value: Any,
    field_name: str,
    minimum: int | None = None,
) -> int | None:
    if value is None:
        return None

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} no puede ser booleano"
        )

    if isinstance(value, float) and not value.is_integer():
        raise ValueError(
            f"{field_name} debe ser un entero"
        )

    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} debe ser un entero o null"
        ) from exc

    if minimum is not None and normalized < minimum:
        raise ValueError(
            f"{field_name} no puede ser menor que {minimum}"
        )

    return normalized


def _optional_boolean(
    value: Any,
    field_name: str,
) -> bool | None:
    if value is None:
        return None

    if not isinstance(value, bool):
        raise TypeError(
            f"{field_name} debe ser booleano o null"
        )

    return value


def _normalize_metrics(
    values: Mapping[str, Any] | None,
) -> dict[str, float | None]:
    source = values or {}

    return {
        "battery_percent": _optional_number(
            source.get("battery_percent"),
            "battery_percent",
            minimum=0,
            maximum=100,
        ),
        "voltage_v": _optional_number(
            source.get("voltage_v"),
            "voltage_v",
            minimum=0,
        ),
        "channel_utilization_percent": _optional_number(
            source.get("channel_utilization_percent"),
            "channel_utilization_percent",
            minimum=0,
            maximum=100,
        ),
        "air_util_tx_percent": _optional_number(
            source.get("air_util_tx_percent"),
            "air_util_tx_percent",
            minimum=0,
            maximum=100,
        ),
        "snr_db": _optional_number(
            source.get("snr_db"),
            "snr_db",
        ),
        "rssi_dbm": _optional_number(
            source.get("rssi_dbm"),
            "rssi_dbm",
        ),
    }


def _normalize_radio(
    values: Mapping[str, Any] | None,
) -> dict[str, Any]:
    source = values or {}

    return {
        "channel": _optional_text(
            source.get("channel"),
            "channel",
            200,
        ),
        "firmware": _optional_text(
            source.get("firmware"),
            "firmware",
            200,
        ),
        "hops_away": _optional_integer(
            source.get("hops_away"),
            "hops_away",
            minimum=0,
        ),
        "mqtt_gateway": _optional_boolean(
            source.get("mqtt_gateway"),
            "mqtt_gateway",
        ),
        "frequency_mhz": _optional_number(
            source.get("frequency_mhz"),
            "frequency_mhz",
            minimum=0,
        ),
        "bandwidth_khz": _optional_number(
            source.get("bandwidth_khz"),
            "bandwidth_khz",
            minimum=0,
        ),
        "spreading_factor": _optional_integer(
            source.get("spreading_factor"),
            "spreading_factor",
            minimum=1,
        ),
        "coding_rate": _optional_integer(
            source.get("coding_rate"),
            "coding_rate",
            minimum=1,
        ),
    }


@dataclass(frozen=True, slots=True)
class NodeObservation:
    """Observación normalizada obtenida desde una fuente."""

    source: str
    network: str
    source_id: str
    observed_at: str
    first_seen: str | None
    short_name: str | None
    long_name: str | None
    hardware: str | None
    role: str | None
    node_type: str | None
    is_observer: bool | None
    latitude: float | None
    longitude: float | None
    altitude_m: float | None
    position_precision_bits: int | None
    position_updated_at: str | None
    metrics: dict[str, float | None]
    radio: dict[str, Any]

    @property
    def id(self) -> str:
        return f"{self.network}:{self.source_id}"


@dataclass(frozen=True, slots=True)
class NeighborObservation:
    """Anuncio NeighborInfo emitido por un nodo Meshtastic."""

    source: str
    from_source_id: str
    to_source_id: str
    observed_at: str
    snr_db: float

    @property
    def network(self) -> str:
        return "meshtastic"

    @property
    def from_id(self) -> str:
        return f"meshtastic:{self.from_source_id}"

    @property
    def to_id(self) -> str:
        return f"meshtastic:{self.to_source_id}"

    @property
    def id(self) -> str:
        return (
            "meshtastic:neighbor_info:"
            f"{self.from_source_id}:{self.to_source_id}"
        )


@dataclass(frozen=True, slots=True)
class EdgeObservation:
    """Observación normalizada de una conexión entre nodos."""

    source: str
    network: str
    from_source_id: str
    to_source_id: str
    edge_type: str
    directed: bool
    observed_at: str
    metrics: dict[str, float | None]

    @property
    def from_id(self) -> str:
        return f"{self.network}:{self.from_source_id}"

    @property
    def to_id(self) -> str:
        return f"{self.network}:{self.to_source_id}"

    @property
    def id(self) -> str:
        return (
            f"{self.network}:{self.edge_type}:"
            f"{self.from_source_id}:{self.to_source_id}"
        )


def make_neighbor_observation(
    *,
    source: str,
    from_source_id: str | int,
    to_source_id: str | int,
    observed_at: datetime | str | int | float,
    snr_db: Any,
) -> NeighborObservation:
    """Crea unha observación normalizada dun anuncio NeighborInfo."""

    if not isinstance(source, str):
        raise TypeError("source debe ser texto")

    normalized_source = source.strip().lower()

    if normalized_source not in SOURCE_ORDER:
        raise ValueError(
            f"Fuente no admitida: {source!r}"
        )

    if normalized_source in MESHCORE_SOURCES:
        raise ValueError(
            "As fontes MeshCore non poden producir NeighborInfo"
        )

    normalized_from = normalize_meshtastic_id(
        from_source_id
    )
    normalized_to = normalize_meshtastic_id(
        to_source_id
    )

    if normalized_from == normalized_to:
        raise ValueError(
            "NeighborInfo non pode observar "
            "o propio nodo emisor"
        )

    normalized_snr = _optional_number(
        snr_db,
        "snr_db",
    )

    if normalized_snr is None:
        raise ValueError(
            "snr_db é obrigatorio en NeighborInfo"
        )

    return NeighborObservation(
        source=normalized_source,
        from_source_id=normalized_from,
        to_source_id=normalized_to,
        observed_at=normalize_timestamp(observed_at),
        snr_db=normalized_snr,
    )


def make_edge_observation(
    *,
    source: str,
    network: str,
    from_source_id: str | int,
    to_source_id: str | int,
    edge_type: str,
    directed: bool,
    observed_at: datetime | str | int | float,
    metrics: Mapping[str, Any] | None = None,
) -> EdgeObservation:
    """Crea una observación normalizada de una conexión."""

    if not isinstance(source, str):
        raise TypeError("source debe ser texto")

    if not isinstance(network, str):
        raise TypeError("network debe ser texto")

    if not isinstance(edge_type, str):
        raise TypeError("edge_type debe ser texto")

    if not isinstance(directed, bool):
        raise TypeError("directed debe ser booleano")

    normalized_source = source.strip().lower()
    normalized_network = network.strip().lower()
    normalized_edge_type = edge_type.strip().lower()

    if normalized_source not in SOURCE_ORDER:
        raise ValueError(
            f"Fuente no admitida: {source!r}"
        )

    if normalized_network not in {
        "meshtastic",
        "meshcore",
    }:
        raise ValueError(
            f"Red no admitida: {network!r}"
        )

    if (
        normalized_network == "meshtastic"
        and normalized_source in MESHCORE_SOURCES
    ):
        raise ValueError(
            f"{normalized_source} no es una fuente Meshtastic"
        )

    if (
        normalized_network == "meshcore"
        and normalized_source not in MESHCORE_SOURCES
    ):
        raise ValueError(
            f"{normalized_source} no es una fuente MeshCore"
        )

    if normalized_edge_type not in EDGE_TYPES:
        raise ValueError(
            "Tipo de conexión no admitido: "
            f"{normalized_edge_type!r}"
        )

    if (
        normalized_edge_type == "neighbor"
        and directed
    ):
        raise ValueError(
            "Una conexión neighbor no puede ser dirigida"
        )

    if (
        normalized_edge_type == "traceroute"
        and not directed
    ):
        raise ValueError(
            "Una conexión traceroute debe ser dirigida"
        )

    if normalized_network == "meshtastic":
        normalized_from = normalize_meshtastic_id(
            from_source_id
        )
        normalized_to = normalize_meshtastic_id(
            to_source_id
        )
    else:
        if not isinstance(from_source_id, str):
            raise TypeError(
                "El origen MeshCore debe ser texto"
            )

        if not isinstance(to_source_id, str):
            raise TypeError(
                "El destino MeshCore debe ser texto"
            )

        normalized_from = normalize_meshcore_id(
            from_source_id
        )
        normalized_to = normalize_meshcore_id(
            to_source_id
        )

    if normalized_from == normalized_to:
        raise ValueError(
            "Una conexión no puede enlazar "
            "un nodo consigo mismo"
        )

    if not directed and normalized_from > normalized_to:
        normalized_from, normalized_to = (
            normalized_to,
            normalized_from,
        )

    if metrics is None:
        metric_values: Mapping[str, Any] = {}
    elif not isinstance(metrics, Mapping):
        raise TypeError("metrics debe ser un objeto")
    else:
        metric_values = metrics

    return EdgeObservation(
        source=normalized_source,
        network=normalized_network,
        from_source_id=normalized_from,
        to_source_id=normalized_to,
        edge_type=normalized_edge_type,
        directed=directed,
        observed_at=normalize_timestamp(observed_at),
        metrics={
            "snr_db": _optional_number(
                metric_values.get("snr_db"),
                "snr_db",
            ),
            "rssi_dbm": _optional_number(
                metric_values.get("rssi_dbm"),
                "rssi_dbm",
            ),
        },
    )


def make_observation(
    *,
    source: str,
    network: str,
    source_id: str | int,
    observed_at: datetime | str | int | float,
    first_seen: datetime | str | int | float | None = None,
    short_name: str | None = None,
    long_name: str | None = None,
    hardware: str | None = None,
    role: str | None = None,
    node_type: str | None = None,
    is_observer: bool | None = None,
    latitude: Any = None,
    longitude: Any = None,
    altitude_m: Any = None,
    position_precision_bits: Any = None,
    position_updated_at:
        datetime | str | int | float | None = None,
    metrics: Mapping[str, Any] | None = None,
    radio: Mapping[str, Any] | None = None,
) -> NodeObservation:
    """Crea una observación normalizada y validada."""

    normalized_source = source.strip().lower()
    normalized_network = network.strip().lower()

    if normalized_source not in SOURCE_ORDER:
        raise ValueError(
            f"Fuente no admitida: {source!r}"
        )

    if normalized_network not in {
        "meshtastic",
        "meshcore",
    }:
        raise ValueError(
            f"Red no admitida: {network!r}"
        )

    if (
        normalized_network == "meshtastic"
        and normalized_source in MESHCORE_SOURCES
    ):
        raise ValueError(
            f"{normalized_source} no es una fuente Meshtastic"
        )

    if (
        normalized_network == "meshcore"
        and normalized_source not in MESHCORE_SOURCES
    ):
        raise ValueError(
            f"{normalized_source} no es una fuente MeshCore"
        )

    if normalized_network == "meshtastic":
        normalized_source_id = normalize_meshtastic_id(
            source_id
        )
    else:
        if not isinstance(source_id, str):
            raise TypeError(
                "El identificador MeshCore debe ser texto"
            )

        normalized_source_id = normalize_meshcore_id(
            source_id
        )

    normalized_observed_at = normalize_timestamp(
        observed_at
    )

    normalized_first_seen = (
        normalize_timestamp(first_seen)
        if first_seen is not None
        else None
    )

    if (
        normalized_first_seen is not None
        and _parse_timestamp(normalized_first_seen)
        > _parse_timestamp(normalized_observed_at)
    ):
        raise ValueError(
            "first_seen no puede ser posterior a observed_at"
        )

    normalized_latitude, normalized_longitude = (
        normalize_coordinates(
            latitude,
            longitude,
        )
    )

    has_position = normalized_latitude is not None

    if has_position and position_updated_at is None:
        raise ValueError(
            "Una posición debe incluir position_updated_at"
        )

    if not has_position and position_updated_at is not None:
        raise ValueError(
            "position_updated_at requiere coordenadas"
        )

    normalized_position_time = (
        normalize_timestamp(position_updated_at)
        if position_updated_at is not None
        else None
    )

    normalized_altitude = _optional_number(
        altitude_m,
        "altitude_m",
    )

    normalized_position_precision = _optional_integer(
        position_precision_bits,
        "position_precision_bits",
        minimum=0,
    )

    if (
        normalized_position_precision is not None
        and normalized_position_precision > 32
    ):
        raise ValueError(
            "position_precision_bits no puede superar 32"
        )

    if (
        not has_position
        and normalized_position_precision is not None
    ):
        raise ValueError(
            "position_precision_bits requiere coordenadas"
        )

    if not has_position and normalized_altitude is not None:
        raise ValueError(
            "altitude_m requiere coordenadas"
        )

    normalized_role = _optional_text(
        role,
        "role",
        200,
    )

    normalized_node_type = _optional_text(
        node_type,
        "node_type",
        200,
    )
    normalized_is_observer = _optional_boolean(
        is_observer,
        "is_observer",
    )

    if normalized_network == "meshtastic":
        if normalized_node_type is not None:
            raise ValueError(
                "Un nodo Meshtastic no puede tener node_type"
            )

        if normalized_is_observer is not None:
            raise ValueError(
                "Un nodo Meshtastic no puede tener is_observer"
            )
    else:
        if normalized_role is not None:
            raise ValueError(
                "Un nodo MeshCore no puede tener role"
            )

        if normalized_node_type is None:
            normalized_node_type = "unknown"
        else:
            normalized_node_type = (
                normalized_node_type.lower()
            )

        if normalized_node_type not in MESHCORE_NODE_TYPES:
            raise ValueError(
                "Tipo MeshCore no admitido: "
                f"{normalized_node_type!r}"
            )

    return NodeObservation(
        source=normalized_source,
        network=normalized_network,
        source_id=normalized_source_id,
        observed_at=normalized_observed_at,
        first_seen=normalized_first_seen,
        short_name=_optional_text(
            short_name,
            "short_name",
            200,
        ),
        long_name=_optional_text(
            long_name,
            "long_name",
            500,
        ),
        hardware=_optional_text(
            hardware,
            "hardware",
            200,
        ),
        role=normalized_role,
        node_type=normalized_node_type,
        is_observer=normalized_is_observer,
        latitude=normalized_latitude,
        longitude=normalized_longitude,
        altitude_m=normalized_altitude,
        position_precision_bits=(
            normalized_position_precision
        ),
        position_updated_at=normalized_position_time,
        metrics=_normalize_metrics(metrics),
        radio=_normalize_radio(radio),
    )


def classify_temporal_status(
    last_seen: datetime | str | int | float,
    *,
    now: datetime | str | int | float,
    active_hours: int,
    recent_days: int,
    historical_days: int,
) -> str | None:
    """Clasifica un nodo o devuelve None si ha caducado."""

    if active_hours < 1:
        raise ValueError(
            "active_hours debe ser mayor que cero"
        )

    if recent_days < 1:
        raise ValueError(
            "recent_days debe ser mayor que cero"
        )

    if historical_days < recent_days:
        raise ValueError(
            "historical_days debe ser mayor o igual "
            "que recent_days"
        )

    normalized_last_seen = normalize_timestamp(last_seen)
    normalized_now = normalize_timestamp(now)

    last_seen_dt = _parse_timestamp(
        normalized_last_seen
    )
    now_dt = _parse_timestamp(normalized_now)

    age = now_dt - last_seen_dt

    if age < timedelta(0):
        age = timedelta(0)

    if age <= timedelta(hours=active_hours):
        return "active"

    if age <= timedelta(days=recent_days):
        return "recent"

    if age <= timedelta(days=historical_days):
        return "historical"

    return None


def _latest_non_null(
    observations: tuple[NodeObservation, ...],
    attribute: str,
) -> Any:
    for observation in reversed(observations):
        value = getattr(observation, attribute)

        if value is not None:
            return value

    return None


def merge_observations(
    observations: Iterable[NodeObservation],
    *,
    now: datetime | str | int | float,
    active_hours: int,
    recent_days: int,
    historical_days: int,
) -> dict[str, Any] | None:
    """Consolida observaciones de un mismo nodo."""

    received = tuple(observations)

    if not received:
        raise ValueError(
            "Se necesita al menos una observación"
        )

    node_ids = {
        observation.id
        for observation in received
    }

    if len(node_ids) != 1:
        raise ValueError(
            "No se pueden fusionar nodos diferentes"
        )

    networks = {
        observation.network
        for observation in received
    }

    if len(networks) != 1:
        raise ValueError(
            "No se pueden fusionar redes diferentes"
        )

    ordered = tuple(
        sorted(
            received,
            key=lambda observation: (
                _parse_timestamp(
                    observation.observed_at
                ),
                SOURCE_ORDER[observation.source],
            ),
        )
    )

    node_id = ordered[0].id
    network = ordered[0].network
    last_seen = ordered[-1].observed_at

    temporal_status = classify_temporal_status(
        last_seen,
        now=now,
        active_hours=active_hours,
        recent_days=recent_days,
        historical_days=historical_days,
    )

    if temporal_status is None:
        return None

    first_seen_candidates = [
        observation.first_seen
        or observation.observed_at
        for observation in ordered
    ]

    first_seen = min(
        first_seen_candidates,
        key=_parse_timestamp,
    )

    latest_by_source: dict[str, NodeObservation] = {}

    for observation in ordered:
        latest_by_source[observation.source] = observation

    sources = sorted(
        latest_by_source,
        key=lambda value: SOURCE_ORDER[value],
    )

    source_ids = {
        source: latest_by_source[source].source_id
        for source in sources
    }

    source_last_seen = {
        source: latest_by_source[source].observed_at
        for source in sources
    }

    position_candidates = [
        observation
        for observation in ordered
        if observation.latitude is not None
        and observation.longitude is not None
        and observation.position_updated_at is not None
    ]

    if position_candidates:
        position = max(
            position_candidates,
            key=lambda observation: (
                _parse_timestamp(
                    observation.position_updated_at
                    or observation.observed_at
                ),
                _parse_timestamp(
                    observation.observed_at
                ),
            ),
        )

        latitude = position.latitude
        longitude = position.longitude
        altitude_m = position.altitude_m
        position_precision_bits = (
            position.position_precision_bits
        )
        position_updated_at = (
            position.position_updated_at
        )
    else:
        latitude = None
        longitude = None
        altitude_m = None
        position_precision_bits = None
        position_updated_at = None

    metrics: dict[str, float | None] = {}

    for key in METRIC_KEYS:
        metrics[key] = next(
            (
                observation.metrics[key]
                for observation in reversed(ordered)
                if observation.metrics[key] is not None
            ),
            None,
        )

    radio: dict[str, Any] = {}

    for key in RADIO_KEYS:
        radio[key] = next(
            (
                observation.radio[key]
                for observation in reversed(ordered)
                if observation.radio[key] is not None
            ),
            None,
        )

    return {
        "id": node_id,
        "network": network,
        "source_ids": source_ids,
        "source_last_seen": source_last_seen,
        "sources": sources,
        "short_name": _latest_non_null(
            ordered,
            "short_name",
        ),
        "long_name": _latest_non_null(
            ordered,
            "long_name",
        ),
        "hardware": _latest_non_null(
            ordered,
            "hardware",
        ),
        "role": _latest_non_null(
            ordered,
            "role",
        ),
        "node_type": _latest_non_null(
            ordered,
            "node_type",
        ),
        "is_observer": _latest_non_null(
            ordered,
            "is_observer",
        ),
        "latitude": latitude,
        "longitude": longitude,
        "altitude_m": altitude_m,
        "position_precision_bits": position_precision_bits,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "position_updated_at": position_updated_at,
        "metrics": metrics,
        "radio": radio,
        "status": {
            "active": temporal_status == "active",
            "recent": temporal_status == "recent",
            "historical": (
                temporal_status == "historical"
            ),
            "has_position": latitude is not None,
        },
    }
