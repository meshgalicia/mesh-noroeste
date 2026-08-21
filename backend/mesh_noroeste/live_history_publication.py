"""Publicación estática do histórico live por bloques horarios."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from mesh_noroeste.domain import normalize_timestamp
from mesh_noroeste.live_history import (
    LIVE_HISTORY_RETENTION_SECONDS,
    LiveHistoryHourBucket,
    LiveHistoryStore,
)


HISTORY_MANIFEST_SCHEMA_ID = (
    "mesh-noroeste.history-manifest/v1"
)

HISTORY_HOUR_SCHEMA_ID = (
    "mesh-noroeste.history-hour/v1"
)

HISTORY_DIRECTORY = "history"

HOUR_US = 60 * 60 * 1_000_000


def _hour_datetime(
    start_us: int,
) -> datetime:
    return datetime.fromtimestamp(
        start_us / 1_000_000,
        tz=timezone.utc,
    )


def history_hour_key(
    start_us: int,
) -> str:
    """Identificador estable dunha hora UTC."""

    return _hour_datetime(
        start_us
    ).strftime(
        "%Y-%m-%dT%H"
    )


def history_hour_path(
    start_us: int,
) -> str:
    """Ruta pública relativa do documento horario."""

    moment = _hour_datetime(
        start_us
    )

    return (
        moment.strftime("%Y-%m-%d")
        + "/"
        + moment.strftime("%H")
        + ".json"
    )


def _serialize_document(
    document: Mapping[str, Any],
) -> bytes:
    return (
        json.dumps(
            dict(document),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _fsync_directory(
    path: Path,
) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY,
    )

    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_json(
    path: Path | str,
    document: Mapping[str, Any],
) -> Path:
    """Escribe un JSON atomicamente."""

    destination = Path(
        path
    ).expanduser().resolve()

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    serialized = _serialize_document(
        document
    )

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(
                temporary.name
            )

            temporary.write(
                serialized
            )
            temporary.flush()

            os.fchmod(
                temporary.fileno(),
                0o644,
            )
            os.fsync(
                temporary.fileno()
            )

        os.replace(
            temporary_path,
            destination,
        )
        temporary_path = None

        _fsync_directory(
            destination.parent
        )

        return destination

    finally:
        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink()


def build_history_hour_document(
    store: LiveHistoryStore,
    *,
    start_us: int,
    generated_at: Any,
) -> dict[str, Any]:
    """Constrúe un documento dunha hora completa."""

    if (
        isinstance(start_us, bool)
        or not isinstance(start_us, int)
        or start_us < 0
    ):
        raise ValueError(
            "start_us debe ser un enteiro non negativo"
        )

    if start_us % HOUR_US != 0:
        raise ValueError(
            "start_us debe coincidir co inicio dunha hora UTC"
        )

    end_us = (
        start_us + HOUR_US
    )

    result = store.query_events(
        start_us=start_us,
        end_us=end_us,
        limit=5000,
        kind="all",
    )

    if result.truncated:
        raise ValueError(
            "A hora histórica supera o límite "
            "de 5000 eventos"
        )

    return {
        "schema": HISTORY_HOUR_SCHEMA_ID,
        "generated_at": normalize_timestamp(
            generated_at
        ),
        "key": history_hour_key(
            start_us
        ),
        "start_us": start_us,
        "end_us": end_us,
        "event_count": result.total,
        "events": list(
            result.events
        ),
    }


def _manifest_hour_document(
    bucket: LiveHistoryHourBucket,
) -> dict[str, Any]:
    return {
        "key": history_hour_key(
            bucket.start_us
        ),
        "path": history_hour_path(
            bucket.start_us
        ),
        "start_us": bucket.start_us,
        "end_us": bucket.end_us,
        "events": bucket.events,
        "traceroutes": bucket.traceroutes,
    }


def build_history_manifest(
    store: LiveHistoryStore,
    *,
    generated_at: Any,
) -> dict[str, Any]:
    """Constrúe o índice público das horas dispoñibles."""

    buckets = store.hour_buckets()
    oldest, newest = store.time_bounds()
    node_hours = store.node_hours()

    return {
        "schema": HISTORY_MANIFEST_SCHEMA_ID,
        "generated_at": normalize_timestamp(
            generated_at
        ),
        "retention_seconds": (
            LIVE_HISTORY_RETENTION_SECONDS
        ),
        "oldest_event_us": oldest,
        "newest_event_us": newest,
        "hour_count": len(
            buckets
        ),
        "event_count": sum(
            bucket.events
            for bucket in buckets
        ),
        "traceroute_count": sum(
            bucket.traceroutes
            for bucket in buckets
        ),
        "node_hours": {
            node_id: [
                history_hour_key(
                    start_us
                )
                for start_us in hours
            ]
            for node_id, hours in sorted(
                node_hours.items()
            )
        },
        "hours": [
            _manifest_hour_document(
                bucket
            )
            for bucket in buckets
        ],
    }


def publish_history_hour(
    store: LiveHistoryStore,
    output: Path | str,
    *,
    start_us: int,
    generated_at: Any,
) -> Path:
    """Publica atomicamente unha hora histórica."""

    document = build_history_hour_document(
        store,
        start_us=start_us,
        generated_at=generated_at,
    )

    destination = (
        Path(output)
        .expanduser()
        .resolve()
        / HISTORY_DIRECTORY
        / history_hour_path(start_us)
    )

    return atomic_write_json(
        destination,
        document,
    )


def cleanup_history_publication(
    store: LiveHistoryStore,
    output: Path | str,
) -> int:
    """Elimina documentos horarios que xa non están na retención.

    Só considera ficheiros coa estrutura pública
    ``history/YYYY-MM-DD/HH.json``. Outros ficheiros presentes no
    directorio histórico non se modifican.
    """

    if not isinstance(store, LiveHistoryStore):
        raise TypeError(
            "store debe ser LiveHistoryStore"
        )

    history_root = (
        Path(output)
        .expanduser()
        .resolve()
        / HISTORY_DIRECTORY
    )

    if not history_root.exists():
        return 0

    retained_paths = {
        history_hour_path(
            bucket.start_us
        )
        for bucket in store.hour_buckets()
    }

    removed = 0

    for day_directory in tuple(
        history_root.iterdir()
    ):
        if (
            not day_directory.is_dir()
            or len(day_directory.name) != 10
        ):
            continue

        try:
            datetime.strptime(
                day_directory.name,
                "%Y-%m-%d",
            )
        except ValueError:
            continue

        for candidate in tuple(
            day_directory.iterdir()
        ):
            if not candidate.is_file():
                continue

            if (
                len(candidate.name) != 7
                or not candidate.name.endswith(".json")
            ):
                continue

            hour_text = candidate.stem

            if (
                len(hour_text) != 2
                or not hour_text.isdigit()
                or not 0 <= int(hour_text) <= 23
            ):
                continue

            relative_path = (
                day_directory.name
                + "/"
                + candidate.name
            )

            if relative_path in retained_paths:
                continue

            candidate.unlink()
            removed += 1

        try:
            day_directory.rmdir()
        except OSError:
            pass

    return removed


def publish_history_manifest(
    store: LiveHistoryStore,
    output: Path | str,
    *,
    generated_at: Any,
) -> Path:
    """Publica atomicamente o manifesto histórico."""

    document = build_history_manifest(
        store,
        generated_at=generated_at,
    )

    destination = (
        Path(output)
        .expanduser()
        .resolve()
        / HISTORY_DIRECTORY
        / "manifest.json"
    )

    return atomic_write_json(
        destination,
        document,
    )
