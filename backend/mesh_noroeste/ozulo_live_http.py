"""Acceso incremental ao tráfico Meshtastic publicado por O Zulo."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
)

from mesh_noroeste.domain import MeshtasticLivePacket
from mesh_noroeste.http_client import (
    DEFAULT_MAX_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
    fetch_json,
)
from mesh_noroeste.ozulo_live import (
    parse_ozulo_live_packets,
)


OZULO_LIVE_PACKETS_URL = (
    "https://meshview.mesh.comunidadeozulo.org/api/packets"
)

OZULO_LIVE_PAGE_SIZE = 1000


@dataclass(frozen=True, slots=True)
class OzuloLivePage:
    """Páxina incremental xa normalizada do feed de O Zulo."""

    packets: tuple[MeshtasticLivePacket, ...]
    next_cursor: int | None
    saturated: bool
    requested_url: str
    final_url: str
    bytes_received: int


def _positive_limit(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("limit debe ser un enteiro")

    if not 1 <= value <= OZULO_LIVE_PAGE_SIZE:
        raise ValueError(
            "limit debe estar entre 1 e "
            f"{OZULO_LIVE_PAGE_SIZE}"
        )

    return value


def _optional_cursor(
    value: int | None,
) -> int | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("cursor debe ser un enteiro ou None")

    if value < 0:
        raise ValueError("cursor non pode ser negativo")

    return value


def build_ozulo_live_packets_url(
    url: str = OZULO_LIVE_PACKETS_URL,
    *,
    cursor: int | None = None,
    limit: int = OZULO_LIVE_PAGE_SIZE,
) -> str:
    """Constrúe unha consulta incremental reproducible."""

    normalized_cursor = _optional_cursor(cursor)
    normalized_limit = _positive_limit(limit)

    parsed = urlsplit(url)

    parameters = [
        (name, value)
        for name, value in parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )
        if name not in {"since", "limit"}
    ]

    if normalized_cursor is not None:
        parameters.append(
            ("since", str(normalized_cursor))
        )

    parameters.append(
        ("limit", str(normalized_limit))
    )

    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(parameters),
            parsed.fragment,
        )
    )


def fetch_ozulo_live_page(
    *,
    cursor: int | None = None,
    limit: int = OZULO_LIVE_PAGE_SIZE,
    url: str = OZULO_LIVE_PACKETS_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> OzuloLivePage:
    """Obtén unha páxina incremental do feed live de O Zulo."""

    normalized_cursor = _optional_cursor(cursor)

    page_url = build_ozulo_live_packets_url(
        url,
        cursor=normalized_cursor,
        limit=limit,
    )

    fetched = fetch_json(
        page_url,
        timeout=timeout,
        max_bytes=max_bytes,
    )

    packets = parse_ozulo_live_packets(
        fetched.document,
        source="ozulo_map",
    )

    ordered = tuple(
        sorted(
            packets,
            key=lambda packet: (
                packet.imported_at_us,
                packet.packet_id,
                packet.from_source_id,
            ),
        )
    )

    next_cursor = normalized_cursor

    if ordered:
        maximum_import_time = max(
            packet.imported_at_us
            for packet in ordered
        )

        if (
            normalized_cursor is not None
            and maximum_import_time <= normalized_cursor
        ):
            raise ValueError(
                "A consulta live non avanzou respecto do cursor"
            )

        next_cursor = maximum_import_time

    return OzuloLivePage(
        packets=ordered,
        next_cursor=next_cursor,
        saturated=len(ordered) >= limit,
        requested_url=fetched.requested_url,
        final_url=fetched.final_url,
        bytes_received=fetched.bytes_received,
    )
