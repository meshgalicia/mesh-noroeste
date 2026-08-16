"""Unha iteración do colector Meshtastic en directo de O Zulo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from urllib.parse import quote

from mesh_noroeste.domain import (
    MeshtasticLivePacket,
    MeshtasticLiveReception,
)
from mesh_noroeste.http_client import (
    DEFAULT_MAX_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
    fetch_json,
)
from mesh_noroeste.ozulo_live import (
    parse_ozulo_live_receptions,
)
from mesh_noroeste.ozulo_live_http import (
    OZULO_LIVE_PACKETS_URL,
    OZULO_LIVE_PAGE_SIZE,
    OzuloLivePage,
    fetch_ozulo_live_page,
)


OZULO_LIVE_PACKETS_SEEN_BASE_URL = (
    "https://meshview.mesh.comunidadeozulo.org/"
    "api/packets_seen"
)


@dataclass(frozen=True, slots=True)
class OzuloLivePacketObservation:
    """Paquete live xunto coas recepcións atribuídas a gateways."""

    packet: MeshtasticLivePacket
    receptions: tuple[MeshtasticLiveReception, ...]


@dataclass(frozen=True, slots=True)
class OzuloLiveBatch:
    """Resultado completo dunha iteración do colector live."""

    observations: tuple[OzuloLivePacketObservation, ...]
    previous_cursor: int | None
    next_cursor: int | None
    saturated: bool
    bytes_received: int

    @property
    def possible_gap(self) -> bool:
        """Indica que a API puido truncar paquetes intermedios."""

        return self.saturated


def build_ozulo_packets_seen_url(
    packet_id: int,
    *,
    base_url: str = OZULO_LIVE_PACKETS_SEEN_BASE_URL,
) -> str:
    """Constrúe a URL de recepcións dun paquete."""

    if isinstance(packet_id, bool) or not isinstance(packet_id, int):
        raise TypeError("packet_id debe ser un enteiro")

    if not 0 <= packet_id <= 0xFFFFFFFF:
        raise ValueError(
            "packet_id debe ser un enteiro de 32 bits"
        )

    return (
        base_url.rstrip("/")
        + "/"
        + quote(str(packet_id), safe="")
    )


def fetch_ozulo_packet_receptions(
    packet: MeshtasticLivePacket,
    *,
    base_url: str = OZULO_LIVE_PACKETS_SEEN_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> tuple[
    tuple[MeshtasticLiveReception, ...],
    int,
]:
    """Obtén e normaliza ``packets_seen`` para un paquete."""

    if not isinstance(packet, MeshtasticLivePacket):
        raise TypeError(
            "packet debe ser MeshtasticLivePacket"
        )

    fetched = fetch_json(
        build_ozulo_packets_seen_url(
            packet.packet_id,
            base_url=base_url,
        ),
        timeout=timeout,
        max_bytes=max_bytes,
    )

    receptions = parse_ozulo_live_receptions(
        fetched.document,
        packet_id=packet.packet_id,
        from_source_id=packet.from_source_id,
        source="ozulo_map",
    )

    return receptions, fetched.bytes_received


def poll_ozulo_live_once(
    *,
    cursor: int | None = None,
    limit: int = OZULO_LIVE_PAGE_SIZE,
    packets_url: str = OZULO_LIVE_PACKETS_URL,
    packets_seen_base_url: str = (
        OZULO_LIVE_PACKETS_SEEN_BASE_URL
    ),
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    page_fetcher: Callable[..., OzuloLivePage] = (
        fetch_ozulo_live_page
    ),
    reception_fetcher: Callable[..., tuple[
        tuple[MeshtasticLiveReception, ...],
        int,
    ]] = fetch_ozulo_packet_receptions,
) -> OzuloLiveBatch:
    """Executa unha única lectura incremental completa."""

    page = page_fetcher(
        cursor=cursor,
        limit=limit,
        url=packets_url,
        timeout=timeout,
        max_bytes=max_bytes,
    )

    observations: list[OzuloLivePacketObservation] = []
    bytes_received = page.bytes_received

    for packet in page.packets:
        receptions, reception_bytes = reception_fetcher(
            packet,
            base_url=packets_seen_base_url,
            timeout=timeout,
            max_bytes=max_bytes,
        )

        bytes_received += reception_bytes

        observations.append(
            OzuloLivePacketObservation(
                packet=packet,
                receptions=receptions,
            )
        )

    return OzuloLiveBatch(
        observations=tuple(observations),
        previous_cursor=cursor,
        next_cursor=page.next_cursor,
        saturated=page.saturated,
        bytes_received=bytes_received,
    )
