"""Generación de los documentos JSON públicos."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid
from typing import Any

from mesh_noroeste import __version__
from mesh_noroeste.config import Settings
from mesh_noroeste.configuration_warnings import (
    build_configuration_warnings_document,
    build_unavailable_configuration_warnings_document,
)
from mesh_noroeste.domain import (
    EdgeObservation,
    NeighborObservation,
    NodeObservation,
    ObserverReception,
    SOURCE_ORDER,
    merge_observations,
)
from mesh_noroeste.normalization import (
    normalize_timestamp,
)
from mesh_noroeste.region import (
    DEFAULT_REGION_NAME,
    default_region_bounds,
    point_in_default_region,
)


SCHEMA_ID = "mesh-noroeste.data/v1"

PUBLIC_DOCUMENT_NAMES = (
    "nodes.json",
    "edges.json",
    "neighbor-info.json",
    "observer-receptions.json",
    "stats.json",
    "meta.json",
    "configuration-warnings.json",
)

PUBLIC_MANIFEST_NAME = "manifest.json"
PUBLIC_MANIFEST_SCHEMA = "mesh-noroeste.manifest/v1"
PUBLIC_GENERATIONS_DIRECTORY = "generations"
PUBLIC_GENERATIONS_TO_KEEP = 12

_SEMANTIC_VERSION = re.compile(
    r"^[0-9]+\.[0-9]+\.[0-9]+$"
)


def _normalize_bounds(
    bounds: Mapping[str, Any] | None,
) -> dict[str, float] | None:
    if bounds is None:
        return None

    expected_keys = {
        "south",
        "west",
        "north",
        "east",
    }

    if set(bounds) != expected_keys:
        raise ValueError(
            "bounds debe contener exactamente: "
            "south, west, north y east"
        )

    normalized: dict[str, float] = {}

    for key in expected_keys:
        value = bounds[key]

        if isinstance(value, bool):
            raise ValueError(
                f"bounds.{key} no puede ser booleano"
            )

        try:
            normalized[key] = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"bounds.{key} debe ser numérico"
            ) from exc

    if not -90 <= normalized["south"] <= 90:
        raise ValueError(
            "bounds.south debe estar entre -90 y 90"
        )

    if not -90 <= normalized["north"] <= 90:
        raise ValueError(
            "bounds.north debe estar entre -90 y 90"
        )

    if not -180 <= normalized["west"] <= 180:
        raise ValueError(
            "bounds.west debe estar entre -180 y 180"
        )

    if not -180 <= normalized["east"] <= 180:
        raise ValueError(
            "bounds.east debe estar entre -180 y 180"
        )

    if normalized["south"] >= normalized["north"]:
        raise ValueError(
            "bounds.south debe ser menor que bounds.north"
        )

    if normalized["west"] >= normalized["east"]:
        raise ValueError(
            "bounds.west debe ser menor que bounds.east"
        )

    return {
        "south": normalized["south"],
        "west": normalized["west"],
        "north": normalized["north"],
        "east": normalized["east"],
    }


def _node_inside_region(
    node: Mapping[str, Any],
    custom_bounds: Mapping[str, float] | None,
) -> bool:
    """Indica si un nodo pertenece a la región publicada."""

    latitude = node["latitude"]
    longitude = node["longitude"]

    if custom_bounds is None:
        return point_in_default_region(
            latitude,
            longitude,
        )

    if latitude is None or longitude is None:
        return False

    return (
        custom_bounds["south"]
        <= latitude
        <= custom_bounds["north"]
        and custom_bounds["west"]
        <= longitude
        <= custom_bounds["east"]
    )


def _source_statistics(
    observations: tuple[NodeObservation, ...],
    supplied: Mapping[
        str,
        Mapping[str, Any],
    ] | None = None,
) -> dict[str, dict[str, Any]]:
    if supplied is None:
        counts = {
            source: 0
            for source in SOURCE_ORDER
        }

        for observation in observations:
            counts[observation.source] += 1

        return {
            source: {
                "last_success": None,
                "last_error_at": None,
                "last_error": None,
                "records_received": counts[source],
            }
            for source in SOURCE_ORDER
        }

    if not isinstance(supplied, Mapping):
        raise TypeError(
            "source_statistics debe ser un objeto"
        )

    expected_sources = set(SOURCE_ORDER)

    if set(supplied) != expected_sources:
        raise ValueError(
            "source_statistics debe contener exactamente: "
            + ", ".join(SOURCE_ORDER)
        )

    expected_fields = {
        "last_success",
        "last_error_at",
        "last_error",
        "records_received",
    }

    normalized: dict[str, dict[str, Any]] = {}

    for source in SOURCE_ORDER:
        values = supplied[source]

        if not isinstance(values, Mapping):
            raise TypeError(
                f"source_statistics.{source} "
                "debe ser un objeto"
            )

        if set(values) != expected_fields:
            raise ValueError(
                f"source_statistics.{source} debe "
                "contener exactamente: "
                "last_success, last_error_at, "
                "last_error y records_received"
            )

        last_success = values["last_success"]
        last_error_at = values["last_error_at"]
        last_error = values["last_error"]
        records_received = values[
            "records_received"
        ]

        normalized_success = (
            None
            if last_success is None
            else normalize_timestamp(last_success)
        )

        normalized_error_at = (
            None
            if last_error_at is None
            else normalize_timestamp(last_error_at)
        )

        if last_error is None:
            normalized_error = None
        elif not isinstance(last_error, str):
            raise TypeError(
                f"source_statistics.{source}."
                "last_error debe ser texto o null"
            )
        else:
            normalized_error = last_error.strip()

            if not normalized_error:
                raise ValueError(
                    f"source_statistics.{source}."
                    "last_error no puede estar vacío"
                )

            if len(normalized_error) > 1000:
                raise ValueError(
                    f"source_statistics.{source}."
                    "last_error supera 1000 caracteres"
                )

        if (
            normalized_error_at is None
        ) != (
            normalized_error is None
        ):
            raise ValueError(
                f"source_statistics.{source}: "
                "last_error_at y last_error deben "
                "ser ambos null o ambos tener valor"
            )

        if (
            isinstance(records_received, bool)
            or not isinstance(records_received, int)
        ):
            raise TypeError(
                f"source_statistics.{source}."
                "records_received debe ser entero"
            )

        if records_received < 0:
            raise ValueError(
                f"source_statistics.{source}."
                "records_received no puede ser negativo"
            )

        normalized[source] = {
            "last_success": normalized_success,
            "last_error_at": normalized_error_at,
            "last_error": normalized_error,
            "records_received": records_received,
        }

    return normalized


def _network_statistics(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    network: str,
) -> dict[str, int]:
    selected_nodes = [
        node
        for node in nodes
        if node["network"] == network
    ]
    selected_edges = [
        edge
        for edge in edges
        if edge["network"] == network
    ]

    return {
        "nodes": len(selected_nodes),
        "active_nodes": sum(
            node["status"]["active"]
            for node in selected_nodes
        ),
        "recent_nodes": sum(
            node["status"]["recent"]
            for node in selected_nodes
        ),
        "historical_nodes": sum(
            node["status"]["historical"]
            for node in selected_nodes
        ),
        "positioned_nodes": sum(
            node["status"]["has_position"]
            for node in selected_nodes
        ),
        "edges": len(selected_edges),
    }


def _public_edge_documents(
    observations: tuple[EdgeObservation, ...],
    published_node_ids: set[str],
) -> list[dict[str, Any]]:
    """Consolida y filtra las conexiones publicables."""

    latest_by_id: dict[str, EdgeObservation] = {}
    source_rank = {
        source: index
        for index, source in enumerate(SOURCE_ORDER)
    }

    for observation in observations:
        if not isinstance(
            observation,
            EdgeObservation,
        ):
            raise TypeError(
                "Todas las conexiones deben ser "
                "EdgeObservation"
            )

        previous = latest_by_id.get(observation.id)

        if previous is None or (
            observation.observed_at,
            source_rank[observation.source],
        ) > (
            previous.observed_at,
            source_rank[previous.source],
        ):
            latest_by_id[observation.id] = observation

    published: list[dict[str, Any]] = []

    for canonical_id in sorted(latest_by_id):
        observation = latest_by_id[canonical_id]

        if (
            observation.from_id
            not in published_node_ids
            or observation.to_id
            not in published_node_ids
        ):
            continue

        published.append(
            {
                "id": observation.id,
                "network": observation.network,
                "source": observation.source,
                "from_id": observation.from_id,
                "to_id": observation.to_id,
                "edge_type": observation.edge_type,
                "directed": observation.directed,
                "last_seen": observation.observed_at,
                "metrics": observation.metrics,
            }
        )

    return published


def _public_neighbor_documents(
    observations: tuple[NeighborObservation, ...],
    excluded_node_ids: set[str],
) -> list[dict[str, Any]]:
    """Ordena e filtra o histórico público de NeighborInfo."""

    unique: dict[
        tuple[str, str, str, str],
        NeighborObservation,
    ] = {}

    for observation in observations:
        if not isinstance(
            observation,
            NeighborObservation,
        ):
            raise TypeError(
                "Todas as observacións NeighborInfo deben ser "
                "NeighborObservation"
            )

        if (
            observation.from_id in excluded_node_ids
            or observation.to_id in excluded_node_ids
        ):
            continue

        identity = (
            observation.source,
            observation.from_id,
            observation.to_id,
            observation.observed_at,
        )

        unique[identity] = observation

    return [
        {
            "source": observation.source,
            "network": observation.network,
            "from_id": observation.from_id,
            "to_id": observation.to_id,
            "observed_at": observation.observed_at,
            "snr_db": observation.snr_db,
        }
        for _, observation in sorted(
            unique.items(),
            key=lambda item: item[0],
        )
    ]


def _public_observer_reception_documents(
    receptions: tuple[ObserverReception, ...],
    excluded_node_ids: set[str],
) -> list[dict[str, Any]]:
    """Ordena e filtra as recepcións públicas dos observers."""

    unique: dict[str, ObserverReception] = {}

    for reception in receptions:
        if not isinstance(reception, ObserverReception):
            raise TypeError(
                "Todas as recepcións deben ser ObserverReception"
            )

        if (
            reception.node_id in excluded_node_ids
            or reception.observer_id in excluded_node_ids
        ):
            continue

        unique[reception.id] = reception

    return [
        {
            "source": reception.source,
            "network": "meshcore",
            "node_id": reception.node_id,
            "observer_id": reception.observer_id,
            "packet_hash": reception.packet_hash,
            "observed_at": reception.observed_at,
            "snr_db": reception.snr_db,
            "path_len": reception.path_len,
        }
        for _, reception in sorted(
            unique.items(),
            key=lambda item: item[0],
        )
    ]


def build_public_documents(
    observations: Iterable[NodeObservation],
    *,
    edge_observations: Iterable[
        EdgeObservation
    ] = (),
    neighbor_observations: Iterable[
        NeighborObservation
    ] = (),
    observer_receptions: Iterable[
        ObserverReception
    ] = (),
    generated_at: Any,
    settings: Settings,
    application_version: str = __version__,
    region_name: str = DEFAULT_REGION_NAME,
    region_bounds: Mapping[str, Any] | None = None,
    source_statistics: Mapping[
        str,
        Mapping[str, Any],
    ] | None = None,
    configuration_warnings_source: Mapping[
        str,
        Any,
    ] | None = None,
    excluded_node_ids: Iterable[str] = (),
) -> dict[str, dict[str, Any]]:
    """Construye nodes, edges, stats y meta."""

    received = tuple(observations)
    received_edges = tuple(edge_observations)
    received_neighbors = tuple(
        neighbor_observations
    )
    received_receptions = tuple(
        observer_receptions
    )

    if isinstance(
        excluded_node_ids,
        (str, bytes),
    ):
        raise TypeError(
            "excluded_node_ids debe ser un iterable "
            "de identificadores"
        )

    excluded_ids: set[str] = set()

    for index, excluded_id in enumerate(
        excluded_node_ids
    ):
        if not isinstance(excluded_id, str):
            raise TypeError(
                "Identificador excluido "
                f"{index}: debe ser texto"
            )

        normalized_excluded_id = (
            excluded_id.strip()
        )

        if not normalized_excluded_id:
            raise ValueError(
                "Identificador excluido "
                f"{index}: no puede estar vacío"
            )

        excluded_ids.add(
            normalized_excluded_id
        )

    normalized_generated_at = normalize_timestamp(
        generated_at
    )

    if not isinstance(application_version, str):
        raise TypeError(
            "application_version debe ser texto"
        )

    normalized_version = application_version.strip()

    if _SEMANTIC_VERSION.fullmatch(
        normalized_version
    ) is None:
        raise ValueError(
            "application_version debe usar el formato "
            "X.Y.Z"
        )

    if not isinstance(region_name, str):
        raise TypeError(
            "region_name debe ser texto"
        )

    normalized_region_name = region_name.strip()

    if not normalized_region_name:
        raise ValueError(
            "region_name no puede estar vacío"
        )

    if len(normalized_region_name) > 300:
        raise ValueError(
            "region_name supera 300 caracteres"
        )

    custom_bounds = _normalize_bounds(
        region_bounds
    )
    published_bounds = (
        custom_bounds
        if custom_bounds is not None
        else default_region_bounds()
    )

    grouped: dict[
        str,
        list[NodeObservation],
    ] = defaultdict(list)
    included_observations: list[
        NodeObservation
    ] = []

    for observation in received:
        if not isinstance(
            observation,
            NodeObservation,
        ):
            raise TypeError(
                "Todas las observaciones deben ser "
                "NodeObservation"
            )

        if observation.id in excluded_ids:
            continue

        included_observations.append(
            observation
        )
        grouped[observation.id].append(
            observation
        )

    nodes: list[dict[str, Any]] = []

    for canonical_id in sorted(grouped):
        node = merge_observations(
            grouped[canonical_id],
            now=normalized_generated_at,
            active_hours=(
                settings.active_node_hours
            ),
            recent_days=(
                settings.recent_node_days
            ),
            historical_days=(
                settings.historical_node_days
            ),
        )

        if (
            node is not None
            and _node_inside_region(
                node,
                custom_bounds,
            )
        ):
            nodes.append(node)

    nodes_document = {
        "schema": SCHEMA_ID,
        "generated_at": normalized_generated_at,
        "nodes": nodes,
    }

    published_node_ids = {
        node["id"]
        for node in nodes
    }

    edges = _public_edge_documents(
        received_edges,
        published_node_ids,
    )

    edges_document = {
        "schema": SCHEMA_ID,
        "generated_at": normalized_generated_at,
        "edges": edges,
    }

    neighbor_info = _public_neighbor_documents(
        received_neighbors,
        excluded_ids,
    )

    neighbor_info_document = {
        "schema": SCHEMA_ID,
        "generated_at": normalized_generated_at,
        "observations": neighbor_info,
    }

    observer_receptions = (
        _public_observer_reception_documents(
            received_receptions,
            excluded_ids,
        )
    )

    observer_receptions_document = {
        "schema": SCHEMA_ID,
        "generated_at": normalized_generated_at,
        "receptions": observer_receptions,
    }

    network_stats = {
        "meshtastic": _network_statistics(
            nodes,
            edges,
            "meshtastic",
        ),
        "meshcore": _network_statistics(
            nodes,
            edges,
            "meshcore",
        ),
    }

    totals = {
        field: sum(
            values[field]
            for values in network_stats.values()
        )
        for field in (
            "nodes",
            "active_nodes",
            "recent_nodes",
            "historical_nodes",
            "positioned_nodes",
            "edges",
        )
    }

    stats_document = {
        "schema": SCHEMA_ID,
        "generated_at": normalized_generated_at,
        "totals": totals,
        "networks": network_stats,
        "sources": _source_statistics(
            tuple(included_observations),
            source_statistics,
        ),
    }

    if configuration_warnings_source is None:
        warnings_document = (
            build_unavailable_configuration_warnings_document(
                nodes,
                generated_at=normalized_generated_at,
            )
        )
    else:
        warnings_document = (
            build_configuration_warnings_document(
                configuration_warnings_source,
                nodes,
                generated_at=normalized_generated_at,
            )
        )

    meta_document = {
        "schema": SCHEMA_ID,
        "generated_at": normalized_generated_at,
        "application": {
            "name": "Mesh Noroeste",
            "version": normalized_version,
        },
        "region": {
            "name": normalized_region_name,
            "bounds": published_bounds,
        },
        "retention": {
            "active_hours": (
                settings.active_node_hours
            ),
            "recent_days": (
                settings.recent_node_days
            ),
            "historical_days": (
                settings.historical_node_days
            ),
        },
    }

    return {
        "nodes.json": nodes_document,
        "edges.json": edges_document,
        "neighbor-info.json": neighbor_info_document,
        "observer-receptions.json": (
            observer_receptions_document
        ),
        "stats.json": stats_document,
        "meta.json": meta_document,
        "configuration-warnings.json": warnings_document,
    }


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY,
    )

    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _serialize_public_documents(
    documents: Mapping[
        str,
        Mapping[str, Any],
    ],
) -> tuple[
    dict[str, bytes],
    str,
]:
    expected = set(PUBLIC_DOCUMENT_NAMES)
    received = set(documents)

    if received != expected:
        missing = sorted(expected - received)
        unexpected = sorted(received - expected)

        details = []

        if missing:
            details.append(
                "faltan: " + ", ".join(missing)
            )

        if unexpected:
            details.append(
                "sobran: " + ", ".join(unexpected)
            )

        raise ValueError(
            "Conjunto de documentos incorrecto: "
            + "; ".join(details)
        )

    generated_values = {
        document.get("generated_at")
        for document in documents.values()
        if isinstance(document, Mapping)
    }

    if (
        len(generated_values) != 1
        or not all(
            isinstance(value, str) and value
            for value in generated_values
        )
    ):
        raise ValueError(
            "Todos los documentos deben compartir "
            "un generated_at válido"
        )

    generated_at = next(iter(generated_values))
    serialized: dict[str, bytes] = {}

    for filename in PUBLIC_DOCUMENT_NAMES:
        serialized[filename] = (
            json.dumps(
                documents[filename],
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")

    return serialized, generated_at


def _generation_identifier(
    generated_at: str,
) -> str:
    timestamp = re.sub(
        r"[^0-9A-Za-z]+",
        "",
        generated_at,
    )

    return (
        f"{timestamp}-"
        f"{uuid.uuid4().hex}"
    )


def _remove_stale_temporary_generations(
    generations_path: Path,
) -> None:
    for candidate in generations_path.glob(
        ".tmp-*"
    ):
        if candidate.is_dir():
            shutil.rmtree(candidate)
        else:
            candidate.unlink()


def _prune_public_generations(
    generations_path: Path,
    active_generation: Path,
) -> None:
    generations = sorted(
        (
            candidate
            for candidate in generations_path.iterdir()
            if (
                candidate.is_dir()
                and not candidate.name.startswith(".tmp-")
            )
        ),
        key=lambda candidate: (
            candidate.stat().st_mtime_ns
        ),
        reverse=True,
    )

    retained = {
        active_generation.resolve()
    }

    for candidate in generations:
        if len(retained) >= PUBLIC_GENERATIONS_TO_KEEP:
            break

        retained.add(candidate.resolve())

    for candidate in generations:
        if candidate.resolve() not in retained:
            shutil.rmtree(candidate)

    _fsync_directory(generations_path)


def _write_public_documents_locked(
    output_path: Path,
    generations_path: Path,
    serialized: Mapping[str, bytes],
    generated_at: str,
) -> list[Path]:
    _remove_stale_temporary_generations(
        generations_path
    )

    identifier = _generation_identifier(
        generated_at
    )
    temporary_generation = (
        generations_path
        / f".tmp-{identifier}"
    )
    final_generation = (
        generations_path
        / identifier
    )

    temporary_manifest: Path | None = None
    generation_installed = False
    manifest_installed = False

    try:
        temporary_generation.mkdir(
            mode=0o755,
        )

        for filename in PUBLIC_DOCUMENT_NAMES:
            document_path = (
                temporary_generation
                / filename
            )

            with document_path.open("xb") as document:
                document.write(
                    serialized[filename]
                )
                document.flush()

                os.fchmod(
                    document.fileno(),
                    0o644,
                )
                os.fsync(document.fileno())

        _fsync_directory(
            temporary_generation
        )

        os.replace(
            temporary_generation,
            final_generation,
        )
        generation_installed = True

        _fsync_directory(
            generations_path
        )

        manifest = {
            "schema": PUBLIC_MANIFEST_SCHEMA,
            "generation": identifier,
            "generated_at": generated_at,
            "documents": {
                filename: (
                    f"{PUBLIC_GENERATIONS_DIRECTORY}/"
                    f"{identifier}/{filename}"
                )
                for filename
                in PUBLIC_DOCUMENT_NAMES
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_path,
            prefix=f".{PUBLIC_MANIFEST_NAME}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_manifest = Path(
                temporary.name
            )

            json.dump(
                manifest,
                temporary,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            temporary.write("\n")
            temporary.flush()

            os.fchmod(
                temporary.fileno(),
                0o644,
            )
            os.fsync(temporary.fileno())

        os.replace(
            temporary_manifest,
            output_path / PUBLIC_MANIFEST_NAME,
        )
        manifest_installed = True
        temporary_manifest = None

        _fsync_directory(output_path)

        _prune_public_generations(
            generations_path,
            final_generation,
        )

    except Exception:
        if temporary_generation.exists():
            shutil.rmtree(
                temporary_generation
            )

        if (
            generation_installed
            and not manifest_installed
            and final_generation.exists()
        ):
            shutil.rmtree(
                final_generation
            )

        if (
            temporary_manifest is not None
            and temporary_manifest.exists()
        ):
            temporary_manifest.unlink()

        raise

    return [
        final_generation / filename
        for filename in PUBLIC_DOCUMENT_NAMES
    ]


def write_public_documents(
    output_directory: Path | str,
    documents: Mapping[
        str,
        Mapping[str, Any],
    ],
) -> list[Path]:
    """Publica una generación mediante un manifiesto atómico."""

    serialized, generated_at = (
        _serialize_public_documents(
            documents
        )
    )

    output_path = Path(
        output_directory
    ).expanduser().resolve()

    generations_path = (
        output_path
        / PUBLIC_GENERATIONS_DIRECTORY
    )

    output_path.mkdir(
        parents=True,
        exist_ok=True,
    )
    generations_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    lock_path = (
        generations_path
        / ".publication.lock"
    )

    with lock_path.open("a+b") as lock:
        os.fchmod(
            lock.fileno(),
            0o600,
        )

        fcntl.flock(
            lock.fileno(),
            fcntl.LOCK_EX,
        )

        try:
            return _write_public_documents_locked(
                output_path,
                generations_path,
                serialized,
                generated_at,
            )
        finally:
            fcntl.flock(
                lock.fileno(),
                fcntl.LOCK_UN,
            )
