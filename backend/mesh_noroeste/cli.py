"""Interfaz de línea de comandos de Mesh Noroeste."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Sequence

from mesh_noroeste.application import (
    MALHA_PT_URL,
    MESHCORE_HUB_NODES_URL,
    MESHCORE_HUB_PAGE_SIZE,
    MESHCORE_MAP_URL,
    MESHVIEW_ES_URL,
    OZULO_MAP_EDGES_URL,
    OZULO_MAP_NODES_URL,
    collect_malha_pt,
    collect_meshcore_hub,
    collect_meshcore_map,
    collect_meshview_es,
    collect_ozulo_map,
    publish_from_store,
)
from mesh_noroeste.config import Settings
from mesh_noroeste.http_client import (
    DEFAULT_MAX_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
)
from mesh_noroeste.malha_http import (
    MALHA_TIMEOUT_SECONDS,
)
from mesh_noroeste.live_runner import (
    run_ozulo_live_once,
)
from mesh_noroeste.region import DEFAULT_REGION_NAME
from mesh_noroeste.storage import ObservationStore
from mesh_noroeste.exclusions import load_exclusions
from mesh_noroeste.normalization import canonical_node_id


def _current_utc_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _print_response(
    response: dict[str, object],
    *,
    compact: bool,
) -> None:
    print(
        json.dumps(
            response,
            ensure_ascii=False,
            indent=None if compact else 2,
            separators=(",", ":") if compact else None,
            sort_keys=True,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mesh-noroeste",
        description=(
            "Backend independiente del mapa "
            "Meshtastic y MeshCore."
        ),
    )

    parser.add_argument(
        "--compact",
        action="store_true",
        help="Escribe cada resultado JSON en una sola línea.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    publish_parser = subparsers.add_parser(
        "publish",
        help=(
            "Genera nodes.json, edges.json, "
            "stats.json y meta.json desde SQLite."
        ),
    )

    publish_parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help=(
            "Ruta de la base SQLite. "
            "Por defecto: MESH_STATE_DIR/mesh-noroeste.db"
        ),
    )

    publish_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Directorio de salida de los JSON. "
            "Por defecto: MESH_DATA_DIR"
        ),
    )

    publish_parser.add_argument(
        "--generated-at",
        default=None,
        help=(
            "Fecha de generación ISO 8601 o timestamp Unix. "
            "Por defecto: fecha UTC actual."
        ),
    )

    publish_parser.add_argument(
        "--region-name",
        default=DEFAULT_REGION_NAME,
        help="Nombre público de la región.",
    )

    publish_parser.add_argument(
        "--bounds",
        nargs=4,
        type=float,
        metavar=(
            "SOUTH",
            "WEST",
            "NORTH",
            "EAST",
        ),
        help=(
            "Sustituye la región predeterminada por un "
            "rectángulo en grados decimales."
        ),
    )

    meshview_parser = subparsers.add_parser(
        "collect-meshview",
        help=(
            "Descarga y almacena los nodos publicados "
            "por Meshview España."
        ),
    )

    meshview_parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help=(
            "Ruta de la base SQLite. "
            "Por defecto: MESH_STATE_DIR/mesh-noroeste.db"
        ),
    )

    meshview_parser.add_argument(
        "--url",
        default=MESHVIEW_ES_URL,
        help="URL HTTPS del documento JSON de nodos.",
    )

    meshview_parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=(
            "Tiempo máximo de espera HTTP en segundos. "
            f"Por defecto: {DEFAULT_TIMEOUT_SECONDS:g}"
        ),
    )

    meshview_parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=(
            "Tamaño máximo permitido para la descarga. "
            f"Por defecto: {DEFAULT_MAX_BYTES} bytes."
        ),
    )

    malha_parser = subparsers.add_parser(
        "collect-malha",
        help=(
            "Descarga y almacena los nodos y traceroutes "
            "publicados por Malha Portugal."
        ),
    )

    malha_parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help=(
            "Ruta de la base SQLite. "
            "Por defecto: MESH_STATE_DIR/mesh-noroeste.db"
        ),
    )

    malha_parser.add_argument(
        "--cookie-file",
        type=Path,
        default=None,
        help=(
            "Archivo persistente de cookies. "
            "Por defecto: cache/malha-pt.cookies"
        ),
    )

    malha_parser.add_argument(
        "--cache-file",
        type=Path,
        default=None,
        help=(
            "Archivo de la última respuesta JSON válida. "
            "Por defecto: cache/malha-pt.json"
        ),
    )

    malha_parser.add_argument(
        "--url",
        default=MALHA_PT_URL,
        help="URL HTTPS del documento JSON de Malha.",
    )

    malha_parser.add_argument(
        "--timeout",
        type=float,
        default=MALHA_TIMEOUT_SECONDS,
        help=(
            "Tiempo máximo de espera HTTP en segundos. "
            f"Por defecto: {MALHA_TIMEOUT_SECONDS:g}"
        ),
    )

    malha_parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=(
            "Tamaño máximo permitido para la descarga. "
            f"Por defecto: {DEFAULT_MAX_BYTES} bytes."
        ),
    )

    ozulo_parser = subparsers.add_parser(
        "collect-ozulo",
        help=(
            "Descarga e almacena os nodos e conexións "
            "consolidados publicados por O Zulo."
        ),
    )

    ozulo_parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help=(
            "Ruta de la base SQLite. "
            "Por defecto: MESH_STATE_DIR/mesh-noroeste.db"
        ),
    )

    ozulo_parser.add_argument(
        "--nodes-url",
        default=OZULO_MAP_NODES_URL,
        help="URL HTTPS do documento JSON de nodos.",
    )

    ozulo_parser.add_argument(
        "--edges-url",
        default=OZULO_MAP_EDGES_URL,
        help="URL HTTPS do documento JSON de conexións.",
    )

    ozulo_parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=(
            "Tempo máximo de espera HTTP en segundos. "
            f"Por defecto: {DEFAULT_TIMEOUT_SECONDS:g}"
        ),
    )

    ozulo_parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=(
            "Tamaño máximo permitido por descarga. "
            f"Por defecto: {DEFAULT_MAX_BYTES} bytes."
        ),
    )

    ozulo_live_parser = subparsers.add_parser(
        "collect-ozulo-live",
        help=(
            "Recolle e publica unha iteración incremental "
            "do tráfico Meshtastic en directo de O Zulo."
        ),
    )

    ozulo_live_parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help=(
            "Ruta da base SQLite. "
            "Por defecto: MESH_STATE_DIR/mesh-noroeste.db"
        ),
    )

    ozulo_live_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Directorio de saída para live.json. "
            "Por defecto: MESH_DATA_DIR"
        ),
    )

    ozulo_live_parser.add_argument(
        "--generated-at",
        default=None,
        help=(
            "Data de xeración ISO 8601 ou timestamp Unix. "
            "Por defecto: data UTC actual."
        ),
    )

    collect_parser = subparsers.add_parser(
        "collect-meshcore",
        help=(
            "Descarga y almacena los nodos publicados "
            "por MeshCore Map."
        ),
    )

    collect_parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help=(
            "Ruta de la base SQLite. "
            "Por defecto: MESH_STATE_DIR/mesh-noroeste.db"
        ),
    )

    collect_parser.add_argument(
        "--url",
        default=MESHCORE_MAP_URL,
        help="URL HTTPS del documento compacto.",
    )

    collect_parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=(
            "Tiempo máximo de espera HTTP en segundos. "
            f"Por defecto: {DEFAULT_TIMEOUT_SECONDS:g}"
        ),
    )

    collect_parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=(
            "Tamaño máximo permitido para la descarga. "
            f"Por defecto: {DEFAULT_MAX_BYTES} bytes."
        ),
    )

    hub_parser = subparsers.add_parser(
        "collect-meshcore-hub",
        help=(
            "Descarga e almacena os nodos publicados "
            "polo MeshCore Hub propio."
        ),
    )

    hub_parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help=(
            "Ruta da base SQLite. "
            "Por defecto: MESH_STATE_DIR/mesh-noroeste.db"
        ),
    )

    hub_parser.add_argument(
        "--url",
        default=MESHCORE_HUB_NODES_URL,
        help="URL HTTPS da API de nodos do Hub.",
    )

    hub_parser.add_argument(
        "--page-size",
        type=int,
        default=MESHCORE_HUB_PAGE_SIZE,
        help=(
            "Número de nodos solicitado por páxina. "
            f"Por defecto: {MESHCORE_HUB_PAGE_SIZE}."
        ),
    )

    hub_parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=(
            "Tempo máximo de espera HTTP en segundos. "
            f"Por defecto: {DEFAULT_TIMEOUT_SECONDS:g}"
        ),
    )

    hub_parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=(
            "Tamaño máximo permitido por páxina. "
            f"Por defecto: {DEFAULT_MAX_BYTES} bytes."
        ),
    )

    purge_node_parser = subparsers.add_parser(
        "purge-node",
        help=(
            "Elimina de SQLite un nodo excluído e "
            "volve publicar os documentos públicos."
        ),
    )
    purge_node_parser.add_argument(
        "canonical_id",
        help=(
            "Identificador canónico completo, por exemplo "
            "meshtastic:!a35b4144."
        ),
    )
    purge_node_parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help=(
            "Ruta de la base SQLite. Por defecto: "
            "MESH_STATE_DIR/mesh-noroeste.db"
        ),
    )
    purge_node_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Directorio de salida de los JSON. "
            "Por defecto: MESH_DATA_DIR"
        ),
    )
    purge_node_parser.add_argument(
        "--generated-at",
        default=None,
        help=(
            "Fecha de generación ISO 8601 o timestamp Unix. "
            "Por defecto: fecha UTC actual."
        ),
    )
    purge_node_parser.add_argument(
        "--region-name",
        default=DEFAULT_REGION_NAME,
        help="Nombre público de la región.",
    )
    purge_node_parser.add_argument(
        "--bounds",
        nargs=4,
        type=float,
        metavar=(
            "SOUTH",
            "WEST",
            "NORTH",
            "EAST",
        ),
        help=(
            "Sustituye la región predeterminada por "
            "un rectángulo en grados decimales."
        ),
    )

    prune_parser = subparsers.add_parser(
        "prune",
        help=(
            "Retira observaciones caducadas "
            "sin alterar el estado publicable."
        ),
    )

    prune_parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help=(
            "Ruta de la base SQLite. "
            "Por defecto: MESH_STATE_DIR/mesh-noroeste.db"
        ),
    )

    prune_parser.add_argument(
        "--before",
        default=None,
        help=(
            "Fecha límite ISO 8601. "
            "Por defecto: ahora menos "
            "HISTORICAL_NODE_DAYS."
        ),
    )

    check_parser = subparsers.add_parser(
        "check",
        help="Comprueba la salud de la base SQLite.",
    )

    check_parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help=(
            "Ruta de la base SQLite. "
            "Por defecto: MESH_STATE_DIR/mesh-noroeste.db"
        ),
    )

    return parser


def _database_path(
    settings: Settings,
    configured_path: Path | None,
) -> Path:
    if configured_path is not None:
        return configured_path.expanduser().resolve()

    return (
        settings.state_dir
        / "mesh-noroeste.db"
    ).resolve()


def _bounds_document(
    values: list[float] | None,
) -> dict[str, float] | None:
    if values is None:
        return None

    south, west, north, east = values

    return {
        "south": south,
        "west": west,
        "north": north,
        "east": east,
    }


def _collect_meshview(
    args: argparse.Namespace,
    settings: Settings,
) -> int:
    result = collect_meshview_es(
        settings=settings,
        database_path=args.database,
        url=args.url,
        timeout=args.timeout,
        max_bytes=args.max_bytes,
    )

    response = {
        "status": "ok",
        "source": result.source,
        "database": str(result.database_path),
        "requested_url": result.requested_url,
        "final_url": result.final_url,
        "bytes_received": result.bytes_received,
        "records_received": result.records_received,
        "records_inserted": result.records_inserted,
    }

    _print_response(response, compact=args.compact)

    return 0


def _collect_malha(
    args: argparse.Namespace,
    settings: Settings,
) -> int:
    result = collect_malha_pt(
        settings=settings,
        database_path=args.database,
        cookie_path=args.cookie_file,
        cache_path=args.cache_file,
        url=args.url,
        timeout=args.timeout,
        max_bytes=args.max_bytes,
    )

    response = {
        "status": "ok",
        "source": result.source,
        "database": str(result.database_path),
        "requested_url": result.requested_url,
        "final_url": result.final_url,
        "bytes_received": result.bytes_received,
        "records_received": result.records_received,
        "records_inserted": result.records_inserted,
    }

    _print_response(response, compact=args.compact)

    return 0


def _collect_ozulo(
    args: argparse.Namespace,
    settings: Settings,
) -> int:
    result = collect_ozulo_map(
        settings=settings,
        database_path=args.database,
        nodes_url=args.nodes_url,
        edges_url=args.edges_url,
        timeout=args.timeout,
        max_bytes=args.max_bytes,
    )

    response = {
        "status": "ok",
        "source": result.source,
        "database": str(result.database_path),
        "requested_url": result.requested_url,
        "final_url": result.final_url,
        "bytes_received": result.bytes_received,
        "records_received": result.records_received,
        "records_inserted": result.records_inserted,
    }

    _print_response(response, compact=args.compact)

    return 0


def _collect_ozulo_live(
    args: argparse.Namespace,
    settings: Settings,
) -> int:
    database_path = _database_path(
        settings,
        args.database,
    )

    output = (
        args.output.expanduser().resolve()
        if args.output is not None
        else settings.data_dir
    )

    generated_at = (
        args.generated_at
        if args.generated_at is not None
        else _current_utc_timestamp()
    )

    store = ObservationStore(database_path)

    result = run_ozulo_live_once(
        store,
        output,
        generated_at=generated_at,
    )

    response = {
        "status": "ok",
        "source": result.source,
        "database": str(database_path),
        "previous_cursor": result.previous_cursor,
        "next_cursor": result.next_cursor,
        "events": result.events,
        "possible_gap": result.possible_gap,
        "bytes_received": result.bytes_received,
        "output_path": str(result.output_path),
    }

    _print_response(
        response,
        compact=args.compact,
    )

    return 0


def _collect_meshcore(
    args: argparse.Namespace,
    settings: Settings,
) -> int:
    result = collect_meshcore_map(
        settings=settings,
        database_path=args.database,
        url=args.url,
        timeout=args.timeout,
        max_bytes=args.max_bytes,
    )

    response = {
        "status": "ok",
        "source": result.source,
        "database": str(result.database_path),
        "requested_url": result.requested_url,
        "final_url": result.final_url,
        "bytes_received": result.bytes_received,
        "records_received": result.records_received,
        "records_inserted": result.records_inserted,
    }

    _print_response(response, compact=args.compact)

    return 0


def _collect_meshcore_hub(
    args: argparse.Namespace,
    settings: Settings,
) -> int:
    api_read_key = os.environ.get(
        "MESHCORE_HUB_API_READ_KEY",
        "",
    ).strip()

    if not api_read_key:
        raise ValueError(
            "MESHCORE_HUB_API_READ_KEY non está configurada"
        )

    result = collect_meshcore_hub(
        settings=settings,
        api_read_key=api_read_key,
        database_path=args.database,
        url=args.url,
        page_size=args.page_size,
        timeout=args.timeout,
        max_bytes=args.max_bytes,
    )

    response = {
        "status": "ok",
        "source": result.source,
        "database": str(result.database_path),
        "requested_url": result.requested_url,
        "final_url": result.final_url,
        "bytes_received": result.bytes_received,
        "records_received": result.records_received,
        "records_inserted": result.records_inserted,
        "receptions_received": result.receptions_received,
        "receptions_inserted": result.receptions_inserted,
    }

    _print_response(response, compact=args.compact)

    return 0


def _publish(
    args: argparse.Namespace,
    settings: Settings,
) -> int:
    generated_at = (
        args.generated_at
        if args.generated_at is not None
        else _current_utc_timestamp()
    )

    result = publish_from_store(
        settings=settings,
        generated_at=generated_at,
        database_path=args.database,
        output_directory=args.output,
        region_name=args.region_name,
        region_bounds=_bounds_document(
            args.bounds
        ),
    )

    response = {
        "status": "ok",
        "database": str(result.database_path),
        "output_directory": str(
            result.output_directory
        ),
        "observations": result.observation_count,
        "nodes": result.node_count,
        "edges": result.edge_count,
        "written_files": [
            str(path)
            for path in result.written_files
        ],
    }

    _print_response(response, compact=args.compact)

    return 0


def _purge_node(
    args: argparse.Namespace,
    settings: Settings,
) -> int:
    candidate = args.canonical_id.strip()

    if ":" not in candidate:
        raise ValueError(
            "canonical_id debe incluir el prefijo de red"
        )

    network, source_id = candidate.split(":", 1)
    canonical_id = canonical_node_id(
        network,
        source_id,
    )

    excluded_node_ids = load_exclusions(
        settings.exclusions_path
    )

    if canonical_id not in excluded_node_ids:
        raise ValueError(
            f"{canonical_id} no figura en la lista "
            "privada de exclusiones"
        )

    database_path = _database_path(
        settings,
        args.database,
    )
    store = ObservationStore(database_path)

    deleted = store.purge_node(canonical_id)

    generated_at = (
        args.generated_at
        if args.generated_at is not None
        else _current_utc_timestamp()
    )

    publication = publish_from_store(
        settings=settings,
        generated_at=generated_at,
        database_path=database_path,
        output_directory=args.output,
        region_name=args.region_name,
        region_bounds=_bounds_document(args.bounds),
    )

    quick_check = store.quick_check()

    response = {
        "status": (
            "ok"
            if quick_check == "ok"
            else "error"
        ),
        "canonical_id": canonical_id,
        "database": str(database_path),
        "deleted": {
            "node_observations": (
                deleted.node_observations_deleted
            ),
            "edge_observations": (
                deleted.edge_observations_deleted
            ),
        },
        "published": {
            "output_directory": str(
                publication.output_directory
            ),
            "observations": (
                publication.observation_count
            ),
            "nodes": publication.node_count,
            "edges": publication.edge_count,
            "written_files": [
                str(path)
                for path in publication.written_files
            ],
        },
        "quick_check": quick_check,
    }

    _print_response(
        response,
        compact=args.compact,
    )

    return 0 if response["status"] == "ok" else 1


def _prune(
    args: argparse.Namespace,
    settings: Settings,
) -> int:
    database_path = _database_path(
        settings,
        args.database,
    )

    before = args.before

    if before is None:
        before = (
            datetime.now(timezone.utc)
            - timedelta(
                days=settings.historical_node_days
            )
        ).replace(
            microsecond=0
        ).isoformat().replace(
            "+00:00",
            "Z",
        )

    store = ObservationStore(database_path)
    deleted = store.prune(before)

    response = {
        "status": "ok",
        "database": str(database_path),
        "before": before,
        "deleted": deleted,
        "quick_check": store.quick_check(),
    }

    if response["quick_check"] != "ok":
        response["status"] = "error"

    _print_response(response, compact=args.compact)

    return (
        0
        if response["status"] == "ok"
        else 1
    )


def _check(
    args: argparse.Namespace,
    settings: Settings,
) -> int:
    database_path = _database_path(
        settings,
        args.database,
    )

    store = ObservationStore(database_path)

    response = {
        "status": "ok",
        "database": str(database_path),
        "schema_version": store.schema_version(),
        "quick_check": store.quick_check(),
        "journal_mode": store.journal_mode(),
        "observations": store.count(),
    }

    if response["quick_check"] != "ok":
        response["status"] = "error"

    _print_response(response, compact=args.compact)

    return (
        0
        if response["status"] == "ok"
        else 1
    )


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        settings = Settings.from_env()

        if args.command == "collect-meshview":
            return _collect_meshview(args, settings)

        if args.command == "collect-malha":
            return _collect_malha(args, settings)

        if args.command == "collect-ozulo":
            return _collect_ozulo(args, settings)

        if args.command == "collect-ozulo-live":
            return _collect_ozulo_live(args, settings)

        if args.command == "collect-meshcore":
            return _collect_meshcore(args, settings)

        if args.command == "collect-meshcore-hub":
            return _collect_meshcore_hub(args, settings)

        if args.command == "publish":
            return _publish(args, settings)

        if args.command == "check":
            return _check(args, settings)

        if args.command == "purge-node":
            return _purge_node(args, settings)
        if args.command == "prune":
            return _prune(args, settings)

        parser.error(
            f"Comando desconocido: {args.command}"
        )

    except (
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        sqlite3.Error,
    ) as exc:
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
