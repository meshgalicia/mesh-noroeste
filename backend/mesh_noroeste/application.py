"""Operaciones completas de la aplicación."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any, Mapping
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
)

from mesh_noroeste import __version__
from mesh_noroeste.config import Settings
from mesh_noroeste.configuration_warnings import (
    ConfigurationWarningsError,
)
from mesh_noroeste.domain import (
    EdgeObservation,
    NeighborObservation,
    NodeObservation,
    ObserverReception,
)
from mesh_noroeste.exclusions import load_exclusions
from mesh_noroeste.http_client import (
    DEFAULT_MAX_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
    FetchError,
    JsonFetchResult,
    fetch_bytes,
    fetch_json,
)
from mesh_noroeste.malha_http import (
    MALHA_PT_URL,
    MALHA_TIMEOUT_SECONDS,
    fetch_malha_pt,
)
from mesh_noroeste.malha_pt import (
    parse_malha_pt,
    parse_malha_pt_traceroutes,
)
from mesh_noroeste.meshcore_hub import (
    MeshCoreHubError,
    parse_meshcore_hub_advertisements,
    parse_meshcore_hub_nodes,
    parse_meshcore_hub_packet_group_edges,
)
from mesh_noroeste.meshcore_map import (
    parse_meshcore_map,
)
from mesh_noroeste.meshview_es import (
    parse_meshview_es,
    parse_meshview_es_edges,
    parse_meshview_es_position_precisions,
)
from mesh_noroeste.ozulo_map import (
    parse_ozulo_map_edges,
    parse_ozulo_map_nodes,
    parse_ozulo_neighbor_packets,
)
from mesh_noroeste.publication import (
    build_public_documents,
    write_public_documents,
)
from mesh_noroeste.region import DEFAULT_REGION_NAME
from mesh_noroeste.storage import ObservationStore


MESHVIEW_ES_URL = (
    "https://meshview.meshtastic.es/api/nodes"
)
MESHVIEW_ES_POSITION_PACKETS_URL = (
    "https://meshview.meshtastic.es/api/packets"
    "?portnum=3&limit=1000"
)
MESHVIEW_ES_TRACEROUTE_EDGES_URL = (
    "https://meshview.meshtastic.es/api/edges?type=traceroute"
)
MESHVIEW_ES_NEIGHBOR_EDGES_URL = (
    "https://meshview.meshtastic.es/api/edges?type=neighbor"
)

OZULO_MAP_NODES_URL = (
    "https://mapa.mesh.comunidadeozulo.org/"
    "data/nodes.json"
)
OZULO_MAP_EDGES_URL = (
    "https://mapa.mesh.comunidadeozulo.org/"
    "data/edges.json"
)
OZULO_NEIGHBOR_PACKETS_URL = (
    "https://meshview.mesh.comunidadeozulo.org/"
    "api/packets?portnum=71&limit=500"
)

MESHCORE_MAP_URL = (
    "https://map.meshcore.io/api/v1/"
    "nodes?binary=1&short=1"
)
MESHCORE_MAP_ACCEPT = "application/msgpack"

MESHCORE_HUB_NODES_URL = (
    "https://hub.mesh.gal/api/v1/nodes"
)
MESHCORE_HUB_ADVERTISEMENTS_URL = (
    "https://hub.mesh.gal/api/v1/advertisements"
)
MESHCORE_HUB_PACKET_GROUPS_URL = (
    "https://hub.mesh.gal/api/v1/packet-groups"
    "?path_hash_bytes=2"
    "&include_receptions=true"
)
MESHCORE_HUB_PAGE_SIZE = 100

MESHVIEW_RETRY_DELAYS = (1.0, 3.0)
MESHVIEW_TRANSIENT_HTTP_CODES = (
    "500",
    "502",
    "503",
    "504",
)


def _meshview_fetch_error_is_transient(
    error: FetchError,
) -> bool:
    message = str(error)

    if (
        "Tiempo de espera agotado" in message
        or "Error de red" in message
    ):
        return True

    return any(
        f"Error HTTP {code}" in message
        for code in MESHVIEW_TRANSIENT_HTTP_CODES
    )


def _fetch_meshview_json(
    url: str,
    *,
    timeout: float,
    max_bytes: int,
    sleeper: Callable[[float], Any],
) -> JsonFetchResult:
    delays: tuple[float | None, ...] = (
        *MESHVIEW_RETRY_DELAYS,
        None,
    )

    for delay in delays:
        try:
            return fetch_json(
                url,
                timeout=timeout,
                max_bytes=max_bytes,
            )
        except FetchError as error:
            if (
                delay is None
                or not _meshview_fetch_error_is_transient(
                    error
                )
            ):
                raise

            sleeper(delay)

    raise AssertionError(
        "O bucle de reintentos de Meshview rematou "
        "sen resultado."
    )


def _meshcore_hub_api_key(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(
            "api_read_key debe ser texto"
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            "api_read_key non pode estar baleira"
        )

    if "\r" in normalized or "\n" in normalized:
        raise ValueError(
            "api_read_key non pode conter "
            "saltos de liña"
        )

    return normalized


def _meshcore_hub_page_url(
    url: str,
    *,
    limit: int,
    offset: int,
) -> str:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError(
            "page_size debe ser un enteiro"
        )

    if limit < 1:
        raise ValueError(
            "page_size debe ser maior que cero"
        )

    if isinstance(offset, bool) or not isinstance(offset, int):
        raise TypeError(
            "offset debe ser un enteiro"
        )

    if offset < 0:
        raise ValueError(
            "offset non pode ser negativo"
        )

    parsed = urlsplit(url)

    parameters = [
        (name, value)
        for name, value in parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )
        if name not in {"limit", "offset"}
    ]
    parameters.extend(
        (
            ("limit", str(limit)),
            ("offset", str(offset)),
        )
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


def _meshcore_hub_page_total(
    document: Any,
    *,
    expected_offset: int,
    records_received: int,
) -> int:
    if not isinstance(document, Mapping):
        raise MeshCoreHubError(
            "A raíz de MeshCore Hub debe ser un obxecto"
        )

    values: dict[str, int] = {}

    for field in ("limit", "offset", "total"):
        value = document.get(field)

        if isinstance(value, bool) or not isinstance(value, int):
            raise MeshCoreHubError(
                f"O campo {field!r} debe ser un enteiro"
            )

        values[field] = value

    if values["limit"] < 1:
        raise MeshCoreHubError(
            "O campo 'limit' debe ser maior que cero"
        )

    if values["offset"] < 0:
        raise MeshCoreHubError(
            "O campo 'offset' non pode ser negativo"
        )

    if values["total"] < 0:
        raise MeshCoreHubError(
            "O campo 'total' non pode ser negativo"
        )

    if values["offset"] != expected_offset:
        raise MeshCoreHubError(
            "A páxina de MeshCore Hub devolveu "
            "un offset inesperado"
        )

    if expected_offset + records_received > values["total"]:
        raise MeshCoreHubError(
            "A páxina de MeshCore Hub supera "
            "o total declarado"
        )

    return values["total"]


def _current_utc_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _allowed_node_observations(
    observations: Iterable[NodeObservation],
    excluded_node_ids: frozenset[str],
) -> tuple[NodeObservation, ...]:
    """Descarta nodos incluídos na lista privada."""

    return tuple(
        observation
        for observation in observations
        if observation.id not in excluded_node_ids
    )


def _allowed_edge_observations(
    observations: Iterable[EdgeObservation],
    excluded_node_ids: frozenset[str],
) -> tuple[EdgeObservation, ...]:
    """Descarta conexións con algún extremo excluído."""

    return tuple(
        observation
        for observation in observations
        if (
            observation.from_id not in excluded_node_ids
            and observation.to_id not in excluded_node_ids
        )
    )


def _allowed_neighbor_observations(
    observations: Iterable[NeighborObservation],
    excluded_node_ids: frozenset[str],
) -> tuple[NeighborObservation, ...]:
    """Descarta NeighborInfo con algún extremo excluído."""

    return tuple(
        observation
        for observation in observations
        if (
            observation.from_id not in excluded_node_ids
            and observation.to_id not in excluded_node_ids
        )
    )


def _allowed_observer_receptions(
    receptions: Iterable[ObserverReception],
    excluded_node_ids: frozenset[str],
) -> tuple[ObserverReception, ...]:
    """Descarta recepcións con algún nodo excluído."""

    return tuple(
        reception
        for reception in receptions
        if (
            reception.node_id not in excluded_node_ids
            and reception.observer_id not in excluded_node_ids
        )
    )


@dataclass(frozen=True, slots=True)
class CollectionResult:
    """Resultado de una recolección de fuente."""

    database_path: Path
    source: str
    requested_url: str
    final_url: str
    bytes_received: int
    records_received: int
    records_inserted: int
    receptions_received: int = 0
    receptions_inserted: int = 0


@dataclass(frozen=True, slots=True)
class PublicationResult:
    """Resultado de una publicación de datos."""

    database_path: Path
    output_directory: Path
    observation_count: int
    node_count: int
    edge_count: int
    written_files: tuple[Path, ...]


def collect_meshview_es(
    *,
    settings: Settings,
    database_path: Path | str | None = None,
    url: str = MESHVIEW_ES_URL,
    position_packets_url: str = (
        MESHVIEW_ES_POSITION_PACKETS_URL
    ),
    traceroute_url: str = MESHVIEW_ES_TRACEROUTE_EDGES_URL,
    neighbor_url: str = MESHVIEW_ES_NEIGHBOR_EDGES_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    clock: Callable[[], Any] = _current_utc_timestamp,
    sleeper: Callable[[float], Any] = time.sleep,
) -> CollectionResult:
    """Descarga, adapta y almacena Meshview España."""

    if not callable(clock):
        raise TypeError("clock debe ser invocable")

    resolved_database_path = (
        Path(database_path).expanduser().resolve()
        if database_path is not None
        else (
            settings.state_dir
            / "mesh-noroeste.db"
        ).resolve()
    )

    excluded_node_ids = load_exclusions(
        settings.exclusions_path
    )

    store = ObservationStore(
        resolved_database_path
    )

    run_id = store.begin_source_run(
        "meshview_es",
        clock(),
    )

    try:
        fetched_nodes = _fetch_meshview_json(
            url,
            timeout=timeout,
            max_bytes=max_bytes,
            sleeper=sleeper,
        )
        fetched_position_packets = _fetch_meshview_json(
            position_packets_url,
            timeout=timeout,
            max_bytes=max_bytes,
            sleeper=sleeper,
        )
        fetched_traceroutes = _fetch_meshview_json(
            traceroute_url,
            timeout=timeout,
            max_bytes=max_bytes,
            sleeper=sleeper,
        )
        fetched_neighbors = _fetch_meshview_json(
            neighbor_url,
            timeout=timeout,
            max_bytes=max_bytes,
            sleeper=sleeper,
        )

        collected_at = clock()

        position_precisions = (
            parse_meshview_es_position_precisions(
                fetched_position_packets.document
            )
        )
        observations = parse_meshview_es(
            fetched_nodes.document,
            position_precisions=position_precisions,
        )
        traceroute_edges = parse_meshview_es_edges(
            fetched_traceroutes.document,
            edge_type="traceroute",
            observed_at=collected_at,
        )
        neighbor_edges = parse_meshview_es_edges(
            fetched_neighbors.document,
            edge_type="neighbor",
            observed_at=collected_at,
        )

        allowed_observations = (
            _allowed_node_observations(
                observations,
                excluded_node_ids,
            )
        )
        allowed_edges = _allowed_edge_observations(
            traceroute_edges + neighbor_edges,
            excluded_node_ids,
        )

        inserted = store.save(
            allowed_observations
        )
        store.replace_edges(
            "meshview_es",
            allowed_edges,
        )

    except Exception as exc:
        description = str(exc).strip()

        error_message = (
            f"{type(exc).__name__}: {description}"
            if description
            else type(exc).__name__
        )

        store.finish_source_run(
            run_id,
            finished_at=clock(),
            success=False,
            records_received=0,
            error_message=error_message[:1000],
        )

        raise

    store.finish_source_run(
        run_id,
        finished_at=clock(),
        success=True,
        records_received=len(observations),
    )

    return CollectionResult(
        database_path=resolved_database_path,
        source="meshview_es",
        requested_url=fetched_nodes.requested_url,
        final_url=fetched_nodes.final_url,
        bytes_received=(
            fetched_nodes.bytes_received
            + fetched_position_packets.bytes_received
            + fetched_traceroutes.bytes_received
            + fetched_neighbors.bytes_received
        ),
        records_received=len(observations),
        records_inserted=inserted,
    )


def collect_malha_pt(
    *,
    settings: Settings,
    database_path: Path | str | None = None,
    cookie_path: Path | str | None = None,
    cache_path: Path | str | None = None,
    url: str = MALHA_PT_URL,
    timeout: float = MALHA_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    clock: Callable[[], Any] = _current_utc_timestamp,
) -> CollectionResult:
    """Descarga, adapta y almacena Malha Portugal."""

    if not callable(clock):
        raise TypeError("clock debe ser invocable")

    resolved_database_path = (
        Path(database_path).expanduser().resolve()
        if database_path is not None
        else (
            settings.state_dir
            / "mesh-noroeste.db"
        ).resolve()
    )
    resolved_cookie_path = (
        Path(cookie_path).expanduser().resolve()
        if cookie_path is not None
        else (
            settings.root_dir
            / "cache"
            / "malha-pt.cookies"
        ).resolve()
    )
    resolved_cache_path = (
        Path(cache_path).expanduser().resolve()
        if cache_path is not None
        else (
            settings.root_dir
            / "cache"
            / "malha-pt.json"
        ).resolve()
    )

    excluded_node_ids = load_exclusions(
        settings.exclusions_path
    )

    store = ObservationStore(
        resolved_database_path
    )

    run_id = store.begin_source_run(
        "malha_pt",
        clock(),
    )

    try:
        fetched = fetch_malha_pt(
            cookie_path=resolved_cookie_path,
            cache_path=resolved_cache_path,
            url=url,
            timeout=timeout,
            max_bytes=max_bytes,
        )
        node_observations = parse_malha_pt(
            fetched.document
        )
        edge_observations = (
            parse_malha_pt_traceroutes(
                fetched.document
            )
        )

        allowed_nodes = _allowed_node_observations(
            node_observations,
            excluded_node_ids,
        )
        allowed_edges = _allowed_edge_observations(
            edge_observations,
            excluded_node_ids,
        )

        inserted_nodes = store.save(
            allowed_nodes
        )
        inserted_edges = store.save_edges(
            allowed_edges
        )

    except Exception as exc:
        description = str(exc).strip()

        error_message = (
            f"{type(exc).__name__}: {description}"
            if description
            else type(exc).__name__
        )

        store.finish_source_run(
            run_id,
            finished_at=clock(),
            success=False,
            records_received=0,
            error_message=error_message[:1000],
        )

        raise

    records_received = (
        len(node_observations)
        + len(edge_observations)
    )
    records_inserted = (
        inserted_nodes
        + inserted_edges
    )

    store.finish_source_run(
        run_id,
        finished_at=clock(),
        success=True,
        records_received=records_received,
    )

    return CollectionResult(
        database_path=resolved_database_path,
        source="malha_pt",
        requested_url=fetched.requested_url,
        final_url=fetched.final_url,
        bytes_received=fetched.bytes_received,
        records_received=records_received,
        records_inserted=records_inserted,
    )


def collect_ozulo_map(
    *,
    settings: Settings,
    database_path: Path | str | None = None,
    nodes_url: str = OZULO_MAP_NODES_URL,
    edges_url: str = OZULO_MAP_EDGES_URL,
    neighbor_packets_url: str = OZULO_NEIGHBOR_PACKETS_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    clock: Callable[[], Any] = _current_utc_timestamp,
) -> CollectionResult:
    """Descarga, adapta e almacena o mapa consolidado de O Zulo."""

    if not callable(clock):
        raise TypeError("clock debe ser invocable")

    resolved_database_path = (
        Path(database_path).expanduser().resolve()
        if database_path is not None
        else (
            settings.state_dir
            / "mesh-noroeste.db"
        ).resolve()
    )

    excluded_node_ids = load_exclusions(
        settings.exclusions_path
    )

    store = ObservationStore(
        resolved_database_path
    )

    run_id = store.begin_source_run(
        "ozulo_map",
        clock(),
    )

    try:
        fetched_nodes = fetch_json(
            nodes_url,
            timeout=timeout,
            max_bytes=max_bytes,
        )
        fetched_edges = fetch_json(
            edges_url,
            timeout=timeout,
            max_bytes=max_bytes,
        )
        fetched_neighbor_packets = fetch_json(
            neighbor_packets_url,
            timeout=timeout,
            max_bytes=max_bytes,
        )

        node_observations = parse_ozulo_map_nodes(
            fetched_nodes.document,
            source="ozulo_map",
        )
        edge_observations = parse_ozulo_map_edges(
            fetched_edges.document,
            source="ozulo_map",
        )
        neighbor_observations = parse_ozulo_neighbor_packets(
            fetched_neighbor_packets.document,
            source="ozulo_map",
        )

        allowed_nodes = _allowed_node_observations(
            node_observations,
            excluded_node_ids,
        )
        allowed_edges = _allowed_edge_observations(
            edge_observations,
            excluded_node_ids,
        )
        allowed_neighbors = _allowed_neighbor_observations(
            neighbor_observations,
            excluded_node_ids,
        )

        inserted_nodes = store.save(
            allowed_nodes
        )
        inserted_edges = store.replace_edges(
            "ozulo_map",
            allowed_edges,
        )
        inserted_neighbors = store.save_neighbors(
            allowed_neighbors
        )

    except Exception as exc:
        description = str(exc).strip()

        error_message = (
            f"{type(exc).__name__}: {description}"
            if description
            else type(exc).__name__
        )

        store.finish_source_run(
            run_id,
            finished_at=clock(),
            success=False,
            records_received=0,
            error_message=error_message[:1000],
        )

        raise

    records_received = (
        len(node_observations)
        + len(edge_observations)
        + len(neighbor_observations)
    )
    records_inserted = (
        inserted_nodes
        + inserted_edges
        + inserted_neighbors
    )

    store.finish_source_run(
        run_id,
        finished_at=clock(),
        success=True,
        records_received=records_received,
    )

    return CollectionResult(
        database_path=resolved_database_path,
        source="ozulo_map",
        requested_url=fetched_nodes.requested_url,
        final_url=fetched_nodes.final_url,
        bytes_received=(
            fetched_nodes.bytes_received
            + fetched_edges.bytes_received
            + fetched_neighbor_packets.bytes_received
        ),
        records_received=records_received,
        records_inserted=records_inserted,
    )


def collect_meshcore_map(
    *,
    settings: Settings,
    database_path: Path | str | None = None,
    url: str = MESHCORE_MAP_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    clock: Callable[[], Any] = _current_utc_timestamp,
) -> CollectionResult:
    """Descarga, adapta y almacena MeshCore Map."""

    if not callable(clock):
        raise TypeError("clock debe ser invocable")

    resolved_database_path = (
        Path(database_path).expanduser().resolve()
        if database_path is not None
        else (
            settings.state_dir
            / "mesh-noroeste.db"
        ).resolve()
    )

    excluded_node_ids = load_exclusions(
        settings.exclusions_path
    )

    store = ObservationStore(
        resolved_database_path
    )

    run_id = store.begin_source_run(
        "meshcore_map",
        clock(),
    )

    try:
        fetched = fetch_bytes(
            url,
            timeout=timeout,
            max_bytes=max_bytes,
            accept=MESHCORE_MAP_ACCEPT,
        )

        observations = parse_meshcore_map(
            fetched.payload
        )
        allowed_observations = (
            _allowed_node_observations(
                observations,
                excluded_node_ids,
            )
        )

        inserted = store.save(
            allowed_observations
        )

    except Exception as exc:
        description = str(exc).strip()

        error_message = (
            f"{type(exc).__name__}: {description}"
            if description
            else type(exc).__name__
        )

        store.finish_source_run(
            run_id,
            finished_at=clock(),
            success=False,
            records_received=0,
            error_message=error_message[:1000],
        )

        raise

    store.finish_source_run(
        run_id,
        finished_at=clock(),
        success=True,
        records_received=len(observations),
    )

    return CollectionResult(
        database_path=resolved_database_path,
        source="meshcore_map",
        requested_url=fetched.requested_url,
        final_url=fetched.final_url,
        bytes_received=fetched.bytes_received,
        records_received=len(observations),
        records_inserted=inserted,
    )


def collect_meshcore_hub(
    *,
    settings: Settings,
    api_read_key: str,
    database_path: Path | str | None = None,
    url: str = MESHCORE_HUB_NODES_URL,
    advertisements_url: str = (
        MESHCORE_HUB_ADVERTISEMENTS_URL
    ),
    packet_groups_url: str = (
        MESHCORE_HUB_PACKET_GROUPS_URL
    ),
    page_size: int = MESHCORE_HUB_PAGE_SIZE,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    clock: Callable[[], Any] = _current_utc_timestamp,
) -> CollectionResult:
    """Descarga, adapta e almacena os nodos de MeshCore Hub."""

    if not callable(clock):
        raise TypeError("clock debe ser invocable")

    normalized_api_key = _meshcore_hub_api_key(
        api_read_key
    )

    first_page_url = _meshcore_hub_page_url(
        url,
        limit=page_size,
        offset=0,
    )

    resolved_database_path = (
        Path(database_path).expanduser().resolve()
        if database_path is not None
        else (
            settings.state_dir
            / "mesh-noroeste.db"
        ).resolve()
    )

    excluded_node_ids = load_exclusions(
        settings.exclusions_path
    )

    store = ObservationStore(
        resolved_database_path
    )

    run_id = store.begin_source_run(
        "meshcore_hub",
        clock(),
    )

    observations: list[NodeObservation] = []
    receptions: list[ObserverReception] = []
    edges: list[EdgeObservation] = []
    seen_ids: set[str] = set()
    seen_reception_ids: set[str] = set()
    bytes_received = 0
    offset = 0
    requested_url = first_page_url
    final_url = first_page_url

    try:
        while True:
            page_url = _meshcore_hub_page_url(
                url,
                limit=page_size,
                offset=offset,
            )

            fetched = fetch_json(
                page_url,
                timeout=timeout,
                max_bytes=max_bytes,
                headers={
                    "Authorization": (
                        f"Bearer {normalized_api_key}"
                    ),
                },
            )

            page_observations = (
                parse_meshcore_hub_nodes(
                    fetched.document,
                    source="meshcore_hub",
                )
            )
            total = _meshcore_hub_page_total(
                fetched.document,
                expected_offset=offset,
                records_received=len(
                    page_observations
                ),
            )

            if offset == 0:
                requested_url = fetched.requested_url

            final_url = fetched.final_url
            bytes_received += fetched.bytes_received

            for observation in page_observations:
                if observation.id in seen_ids:
                    raise MeshCoreHubError(
                        "MeshCore Hub devolveu un nodo "
                        "duplicado entre páxinas: "
                        f"{observation.source_id}"
                    )

                seen_ids.add(observation.id)
                observations.append(observation)

            next_offset = (
                offset + len(page_observations)
            )

            if next_offset >= total:
                break

            if not page_observations:
                raise MeshCoreHubError(
                    "A paxinación de MeshCore Hub "
                    "non avanzou"
                )

            offset = next_offset

        advertisement_offset = 0

        while True:
            advertisement_page_url = (
                _meshcore_hub_page_url(
                    advertisements_url,
                    limit=page_size,
                    offset=advertisement_offset,
                )
            )

            fetched = fetch_json(
                advertisement_page_url,
                timeout=timeout,
                max_bytes=max_bytes,
                headers={
                    "Authorization": (
                        f"Bearer {normalized_api_key}"
                    ),
                },
            )

            document = fetched.document

            if not isinstance(document, Mapping):
                raise MeshCoreHubError(
                    "A raíz de MeshCore Hub debe ser un obxecto"
                )

            records = document.get("items")

            if not isinstance(records, list):
                raise MeshCoreHubError(
                    "O campo 'items' de MeshCore Hub "
                    "debe ser unha lista"
                )

            page_receptions = (
                parse_meshcore_hub_advertisements(
                    document,
                    source="meshcore_hub",
                )
            )
            total = _meshcore_hub_page_total(
                document,
                expected_offset=advertisement_offset,
                records_received=len(records),
            )

            final_url = fetched.final_url
            bytes_received += fetched.bytes_received

            for reception in page_receptions:
                if reception.id in seen_reception_ids:
                    continue

                seen_reception_ids.add(reception.id)
                receptions.append(reception)

            next_offset = (
                advertisement_offset + len(records)
            )

            if next_offset >= total:
                break

            if not records:
                raise MeshCoreHubError(
                    "A paxinación dos anuncios de "
                    "MeshCore Hub non avanzou"
                )

            advertisement_offset = next_offset

        public_keys_by_path_hash_candidates: dict[
            str,
            list[str],
        ] = {}

        for observation in observations:
            public_key = observation.source_id.upper()
            path_hash = public_key[:4]

            public_keys_by_path_hash_candidates.setdefault(
                path_hash,
                [],
            ).append(public_key)

        public_keys_by_path_hash = {
            path_hash: candidates[0]
            for path_hash, candidates
            in public_keys_by_path_hash_candidates.items()
            if len(candidates) == 1
        }

        packet_group_offset = 0

        while True:
            packet_group_page_url = (
                _meshcore_hub_page_url(
                    packet_groups_url,
                    limit=page_size,
                    offset=packet_group_offset,
                )
            )

            fetched = fetch_json(
                packet_group_page_url,
                timeout=timeout,
                max_bytes=max_bytes,
                headers={
                    "Authorization": (
                        f"Bearer {normalized_api_key}"
                    ),
                },
            )

            document = fetched.document

            if not isinstance(document, Mapping):
                raise MeshCoreHubError(
                    "A raíz de MeshCore Hub debe ser un obxecto"
                )

            records = document.get("items")

            if not isinstance(records, list):
                raise MeshCoreHubError(
                    "O campo 'items' de MeshCore Hub "
                    "debe ser unha lista"
                )

            page_edges = (
                parse_meshcore_hub_packet_group_edges(
                    document,
                    source="meshcore_hub",
                    public_keys_by_path_hash=(
                        public_keys_by_path_hash
                    ),
                )
            )

            total = _meshcore_hub_page_total(
                document,
                expected_offset=packet_group_offset,
                records_received=len(records),
            )

            final_url = fetched.final_url
            bytes_received += fetched.bytes_received
            edges.extend(page_edges)

            next_offset = (
                packet_group_offset + len(records)
            )

            if next_offset >= total:
                break

            if not records:
                raise MeshCoreHubError(
                    "A paxinación dos packet-groups de "
                    "MeshCore Hub non avanzou"
                )

            packet_group_offset = next_offset

        allowed_observations = (
            _allowed_node_observations(
                observations,
                excluded_node_ids,
            )
        )
        allowed_receptions = (
            _allowed_observer_receptions(
                receptions,
                excluded_node_ids,
            )
        )
        allowed_edges = (
            _allowed_edge_observations(
                edges,
                excluded_node_ids,
            )
        )

        inserted = store.save(
            allowed_observations
        )
        receptions_inserted = (
            store.save_observer_receptions(
                allowed_receptions
            )
        )
        store.save_edges(
            allowed_edges
        )

    except Exception as exc:
        description = str(exc).strip()

        error_message = (
            f"{type(exc).__name__}: {description}"
            if description
            else type(exc).__name__
        )

        store.finish_source_run(
            run_id,
            finished_at=clock(),
            success=False,
            records_received=0,
            error_message=error_message[:1000],
        )

        raise

    store.finish_source_run(
        run_id,
        finished_at=clock(),
        success=True,
        records_received=len(observations),
    )

    return CollectionResult(
        database_path=resolved_database_path,
        source="meshcore_hub",
        requested_url=requested_url,
        final_url=final_url,
        bytes_received=bytes_received,
        records_received=len(observations),
        records_inserted=inserted,
        receptions_received=len(receptions),
        receptions_inserted=receptions_inserted,
    )


def _load_configuration_warnings_source(
    path: Path | None,
) -> Mapping[str, Any] | None:
    if path is None:
        return None

    try:
        document = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ):
        return None

    if not isinstance(document, Mapping):
        return None

    return document


def publish_from_store(
    *,
    settings: Settings,
    generated_at: Any,
    database_path: Path | str | None = None,
    output_directory: Path | str | None = None,
    application_version: str = __version__,
    region_name: str = DEFAULT_REGION_NAME,
    region_bounds: Mapping[str, Any] | None = None,
) -> PublicationResult:
    """Genera los documentos públicos desde SQLite."""

    resolved_database_path = (
        Path(database_path).expanduser().resolve()
        if database_path is not None
        else (
            settings.state_dir
            / "mesh-noroeste.db"
        ).resolve()
    )

    resolved_output_directory = (
        Path(output_directory).expanduser().resolve()
        if output_directory is not None
        else settings.data_dir.resolve()
    )

    store = ObservationStore(
        resolved_database_path
    )

    observation_count = store.count()
    observations = tuple(
        store.load_for_publication()
    )
    edge_observations = tuple(
        store.load_all_edges()
    )
    neighbor_observations = tuple(
        store.load_all_neighbors()
    )
    observer_receptions = tuple(
        store.load_all_observer_receptions()
    )
    source_statistics = store.source_statistics()
    excluded_node_ids = load_exclusions(
        settings.exclusions_path
    )

    warnings_source = _load_configuration_warnings_source(
        settings.configuration_warnings_path
    )

    try:
        documents = build_public_documents(
            observations,
            edge_observations=edge_observations,
            neighbor_observations=neighbor_observations,
            observer_receptions=observer_receptions,
            generated_at=generated_at,
            settings=settings,
            application_version=application_version,
            region_name=region_name,
            region_bounds=region_bounds,
            source_statistics=source_statistics,
            configuration_warnings_source=warnings_source,
            excluded_node_ids=excluded_node_ids,
        )
    except ConfigurationWarningsError:
        documents = build_public_documents(
            observations,
            edge_observations=edge_observations,
            neighbor_observations=neighbor_observations,
            observer_receptions=observer_receptions,
            generated_at=generated_at,
            settings=settings,
            application_version=application_version,
            region_name=region_name,
            region_bounds=region_bounds,
            source_statistics=source_statistics,
            excluded_node_ids=excluded_node_ids,
        )

    written_files = tuple(
        write_public_documents(
            resolved_output_directory,
            documents,
        )
    )

    return PublicationResult(
        database_path=resolved_database_path,
        output_directory=resolved_output_directory,
        observation_count=observation_count,
        node_count=len(
            documents["nodes.json"]["nodes"]
        ),
        edge_count=len(
            documents["edges.json"]["edges"]
        ),
        written_files=written_files,
    )
