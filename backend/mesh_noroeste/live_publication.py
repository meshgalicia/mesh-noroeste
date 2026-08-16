"""Contrato público do tráfico Meshtastic en directo."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from mesh_noroeste.domain import normalize_timestamp
from mesh_noroeste.live_view import LivePacketView


LIVE_SCHEMA_ID = "mesh-noroeste.live/v1"


@dataclass(frozen=True, slots=True)
class LiveSourceState:
    """Estado incremental dunha fonte do tráfico en directo."""

    previous_cursor: int | None
    next_cursor: int | None
    possible_gap: bool


def _cursor(
    value: int | None,
    field: str,
) -> int | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(
            f"{field} debe ser un enteiro ou None"
        )

    if value < 0:
        raise ValueError(
            f"{field} non pode ser negativo"
        )

    return value


def _source_state_document(
    state: LiveSourceState,
) -> dict[str, Any]:
    if not isinstance(state, LiveSourceState):
        raise TypeError(
            "O estado dunha fonte debe ser LiveSourceState"
        )

    if not isinstance(state.possible_gap, bool):
        raise TypeError(
            "possible_gap debe ser booleano"
        )

    previous_cursor = _cursor(
        state.previous_cursor,
        "previous_cursor",
    )
    next_cursor = _cursor(
        state.next_cursor,
        "next_cursor",
    )

    if (
        previous_cursor is not None
        and next_cursor is not None
        and next_cursor < previous_cursor
    ):
        raise ValueError(
            "next_cursor non pode retroceder "
            "respecto de previous_cursor"
        )

    return {
        "previous_cursor": previous_cursor,
        "next_cursor": next_cursor,
        "possible_gap": state.possible_gap,
    }


def _gateway_document(
    gateway,
) -> dict[str, Any]:
    return {
        "gateway_id": (
            "meshtastic:"
            f"{gateway.gateway_source_id}"
        ),
        "rx_time": gateway.rx_time,
        "snr_db": gateway.snr_db,
        "rssi_dbm": gateway.rssi_dbm,
        "imported_at_us": gateway.imported_at_us,
    }


def _stage_document(
    stage,
) -> dict[str, Any]:
    return {
        "hop_limit": stage.hop_limit,
        "hop_start": stage.hop_start,
        "hops_used": stage.hops_used,
        "gateways": [
            _gateway_document(gateway)
            for gateway in stage.gateways
        ],
    }


def _traceroute_document(
    view: LivePacketView,
) -> dict[str, Any] | None:
    traceroute = view.traceroute

    if traceroute is None:
        return None

    return {
        "towards": [
            f"meshtastic:{source_id}"
            for source_id in traceroute.towards
        ],
        "back": [
            f"meshtastic:{source_id}"
            for source_id in traceroute.back
        ],
        "snr_towards": list(
            traceroute.snr_towards
        ),
        "snr_back": list(
            traceroute.snr_back
        ),
    }


def live_event_document(
    view: LivePacketView,
) -> dict[str, Any]:
    """Serializa unha vista live sen publicar o payload bruto."""

    if not isinstance(view, LivePacketView):
        raise TypeError(
            "view debe ser LivePacketView"
        )

    packet = view.packet

    return {
        "id": packet.id,
        "network": "meshtastic",
        "source": packet.source,
        "packet_id": packet.packet_id,
        "from_id": packet.from_id,
        "to_id": packet.to_id,
        "portnum": packet.portnum,
        "channel": packet.channel,
        "imported_at_us": packet.imported_at_us,
        "long_name": packet.long_name,
        "to_long_name": packet.to_long_name,
        "evidence": list(view.evidence_types),
        "observed": {
            "gateway_count": (
                view.observed_path.observed_gateway_count
            ),
            "stage_count": (
                view.observed_path.observed_stage_count
            ),
            "stages": [
                _stage_document(stage)
                for stage in view.observed_path.stages
            ],
        },
        "traceroute": _traceroute_document(view),
    }


def build_live_document(
    views: Iterable[LivePacketView],
    *,
    generated_at: Any,
    source_states: Mapping[str, LiveSourceState],
) -> dict[str, Any]:
    """Constrúe o documento público do tráfico en directo."""

    if not isinstance(source_states, Mapping):
        raise TypeError(
            "source_states debe ser un mapping"
        )

    normalized_sources: dict[str, dict[str, Any]] = {}

    for source, state in source_states.items():
        if not isinstance(source, str):
            raise TypeError(
                "O nome dunha fonte debe ser texto"
            )

        normalized_source = source.strip().lower()

        if not normalized_source:
            raise ValueError(
                "O nome dunha fonte non pode estar baleiro"
            )

        if normalized_source in normalized_sources:
            raise ValueError(
                "Hai fontes duplicadas tras normalizar"
            )

        normalized_sources[normalized_source] = (
            _source_state_document(state)
        )

    events: list[dict[str, Any]] = []

    seen_ids: set[str] = set()

    for view in views:
        event = live_event_document(view)

        if event["id"] in seen_ids:
            raise ValueError(
                "Hai eventos live duplicados: "
                f"{event['id']}"
            )

        seen_ids.add(event["id"])
        events.append(event)

    events.sort(
        key=lambda event: (
            event["imported_at_us"],
            event["packet_id"],
            event["from_id"],
        )
    )

    return {
        "schema": LIVE_SCHEMA_ID,
        "generated_at": normalize_timestamp(
            generated_at
        ),
        "sources": normalized_sources,
        "events": events,
    }
