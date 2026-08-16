"""Interpretación conservadora do tránsito Meshtastic observado."""

from __future__ import annotations

from dataclasses import dataclass

from mesh_noroeste.domain import (
    MeshtasticLivePacket,
    MeshtasticLiveReception,
)


@dataclass(frozen=True, slots=True)
class LiveObservedGateway:
    """Gateway que observou unha etapa dun paquete."""

    gateway_source_id: str
    rx_time: int
    snr_db: float | None
    rssi_dbm: float | None
    imported_at_us: int


@dataclass(frozen=True, slots=True)
class LiveObservedStage:
    """Etapa observada dun paquete, agrupada por hop_limit."""

    hop_limit: int
    hop_start: int | None
    hops_used: int | None
    gateways: tuple[LiveObservedGateway, ...]


@dataclass(frozen=True, slots=True)
class LiveObservedPath:
    """Percorrido observado sen afirmar relays non coñecidos."""

    packet: MeshtasticLivePacket
    stages: tuple[LiveObservedStage, ...]

    @property
    def observed_gateway_count(self) -> int:
        return sum(
            len(stage.gateways)
            for stage in self.stages
        )

    @property
    def observed_stage_count(self) -> int:
        return len(self.stages)


def build_observed_path(
    packet: MeshtasticLivePacket,
    receptions: tuple[MeshtasticLiveReception, ...],
) -> LiveObservedPath:
    """Agrupa recepcións por etapa sen inventar unha ruta física."""

    if not isinstance(packet, MeshtasticLivePacket):
        raise TypeError(
            "packet debe ser MeshtasticLivePacket"
        )

    grouped: dict[int, list[MeshtasticLiveReception]] = {}

    for reception in receptions:
        if not isinstance(
            reception,
            MeshtasticLiveReception,
        ):
            raise TypeError(
                "receptions debe conter "
                "MeshtasticLiveReception"
            )

        if reception.packet_id != packet.packet_id:
            raise ValueError(
                "A recepción pertence a outro packet_id"
            )

        if reception.from_source_id != packet.from_source_id:
            raise ValueError(
                "A recepción pertence a outro nodo de orixe"
            )

        grouped.setdefault(
            reception.hop_limit,
            [],
        ).append(reception)

    stages: list[LiveObservedStage] = []

    for hop_limit in sorted(grouped, reverse=True):
        records = sorted(
            grouped[hop_limit],
            key=lambda item: (
                item.rx_time,
                item.imported_at_us,
                item.gateway_source_id,
            ),
        )

        hop_start_candidates = {
            item.hop_start
            for item in records
            if item.hop_start is not None
        }

        hop_start = (
            max(hop_start_candidates)
            if hop_start_candidates
            else None
        )

        hops_used = (
            hop_start - hop_limit
            if hop_start is not None
            and hop_start >= hop_limit
            else None
        )

        gateways = tuple(
            LiveObservedGateway(
                gateway_source_id=item.gateway_source_id,
                rx_time=item.rx_time,
                snr_db=item.snr_db,
                rssi_dbm=item.rssi_dbm,
                imported_at_us=item.imported_at_us,
            )
            for item in records
        )

        stages.append(
            LiveObservedStage(
                hop_limit=hop_limit,
                hop_start=hop_start,
                hops_used=hops_used,
                gateways=gateways,
            )
        )

    return LiveObservedPath(
        packet=packet,
        stages=tuple(stages),
    )
