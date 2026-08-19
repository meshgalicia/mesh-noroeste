"""Vista unificada dun paquete Meshtastic en directo."""

from __future__ import annotations

from dataclasses import dataclass

from mesh_noroeste.domain import (
    MeshtasticLivePacket,
    MeshtasticLiveReception,
)
from mesh_noroeste.live_path import (
    LiveObservedPath,
    build_observed_path,
)
from mesh_noroeste.live_telemetry import (
    TELEMETRY_PORTNUM,
    LiveTelemetry,
    parse_live_telemetry_payload,
)
from mesh_noroeste.live_traceroute import (
    LiveTraceroutePath,
    build_live_traceroute_path,
    parse_live_traceroute_payload,
)


TRACEROUTE_PORTNUM = 70


@dataclass(frozen=True, slots=True)
class LivePacketView:
    """Evidencias dispoñibles para un paquete Meshtastic.

    ``observed_path`` describe unicamente onde foi visto o paquete
    segundo as recepcións atribuídas a gateways.

    ``traceroute`` describe unicamente a información RouteDiscovery
    publicada polo propio paquete.

    As dúas evidencias mantéñense separadas deliberadamente.
    """

    packet: MeshtasticLivePacket
    observed_path: LiveObservedPath
    telemetry: LiveTelemetry | None
    traceroute: LiveTraceroutePath | None

    @property
    def has_gateway_observations(self) -> bool:
        return self.observed_path.observed_gateway_count > 0

    @property
    def has_traceroute(self) -> bool:
        return (
            self.traceroute is not None
            and (
                self.traceroute.has_towards
                or self.traceroute.has_back
            )
        )

    @property
    def evidence_types(self) -> tuple[str, ...]:
        """Tipos de evidencia realmente presentes na vista."""

        result: list[str] = []

        if self.has_gateway_observations:
            result.append("gateway_observation")

        if self.has_traceroute:
            result.append("traceroute")

        return tuple(result)


def build_live_packet_view(
    packet: MeshtasticLivePacket,
    receptions: tuple[MeshtasticLiveReception, ...],
) -> LivePacketView:
    """Constrúe unha vista sen fusionar evidencias incompatibles."""

    if not isinstance(packet, MeshtasticLivePacket):
        raise TypeError(
            "packet debe ser MeshtasticLivePacket"
        )

    observed_path = build_observed_path(
        packet,
        receptions,
    )

    telemetry: LiveTelemetry | None = None

    if packet.portnum == TELEMETRY_PORTNUM:
        telemetry = parse_live_telemetry_payload(
            packet.payload
        )

    traceroute: LiveTraceroutePath | None = None

    if packet.portnum == TRACEROUTE_PORTNUM:
        payload = parse_live_traceroute_payload(
            packet.payload
        )

        traceroute = build_live_traceroute_path(
            from_source_id=packet.from_source_id,
            to_source_id=packet.to_source_id,
            payload=payload,
        )

    return LivePacketView(
        packet=packet,
        observed_path=observed_path,
        telemetry=telemetry,
        traceroute=traceroute,
    )
