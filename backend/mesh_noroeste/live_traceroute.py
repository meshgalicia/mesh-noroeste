"""Interpretación do payload RouteDiscovery de Meshtastic."""

from __future__ import annotations

from dataclasses import dataclass
import re

from mesh_noroeste.domain import normalize_meshtastic_id


_VALUE_LINE = re.compile(
    r"^(?P<field>"
    r"route|route_back|snr_towards|snr_back"
    r"):\s*(?P<value>-?\d+)\s*$"
)


@dataclass(frozen=True, slots=True)
class LiveTraceroutePayload:
    """Campos RouteDiscovery publicados no payload dun paquete."""

    route: tuple[str, ...]
    route_back: tuple[str, ...]
    snr_towards: tuple[int, ...]
    snr_back: tuple[int, ...]

    @property
    def has_route(self) -> bool:
        return bool(self.route or self.route_back)


def parse_live_traceroute_payload(
    payload: str,
) -> LiveTraceroutePayload:
    """Extrae RouteDiscovery sen inventar a semántica do percorrido."""

    if not isinstance(payload, str):
        raise TypeError("payload debe ser texto")

    route: list[str] = []
    route_back: list[str] = []
    snr_towards: list[int] = []
    snr_back: list[int] = []

    for line_number, raw_line in enumerate(
        payload.splitlines(),
        start=1,
    ):
        line = raw_line.strip()

        if not line:
            continue

        match = _VALUE_LINE.fullmatch(line)

        if match is None:
            continue

        field = match.group("field")
        value = int(match.group("value"))

        if field in {"route", "route_back"}:
            if not 0 <= value <= 0xFFFFFFFF:
                raise ValueError(
                    f"Liña {line_number}: node_id fóra de rango"
                )

            normalized = normalize_meshtastic_id(value)

            if field == "route":
                route.append(normalized)
            else:
                route_back.append(normalized)

        elif field == "snr_towards":
            snr_towards.append(value)

        elif field == "snr_back":
            snr_back.append(value)

    return LiveTraceroutePayload(
        route=tuple(route),
        route_back=tuple(route_back),
        snr_towards=tuple(snr_towards),
        snr_back=tuple(snr_back),
    )
