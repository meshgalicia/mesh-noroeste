"""Construción e escritura do documento público live."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import tempfile
from typing import Any

from mesh_noroeste.live_publication import (
    LIVE_SCHEMA_ID,
    LiveSourceState,
    build_live_document,
)
from mesh_noroeste.live_view import (
    build_live_packet_view,
)
from mesh_noroeste.ozulo_live_poll import (
    OzuloLiveBatch,
)


LIVE_FILENAME = "live.json"
LIVE_RETENTION_SECONDS = 60 * 60

logger = logging.getLogger(__name__)


def build_live_document_from_ozulo_batch(
    batch: OzuloLiveBatch,
    *,
    generated_at: Any,
) -> dict[str, Any]:
    """Converte unha iteración de O Zulo no contrato live público."""

    if not isinstance(batch, OzuloLiveBatch):
        raise TypeError(
            "batch debe ser OzuloLiveBatch"
        )

    views = []
    seen_event_ids: set[str] = set()

    for observation in batch.observations:
        event_id = observation.packet.id

        if event_id in seen_event_ids:
            logger.warning(
                "Descartado paquete live duplicado "
                "source=%s packet_id=%s event_id=%s",
                observation.packet.source,
                observation.packet.packet_id,
                event_id,
            )
            continue

        try:
            view = build_live_packet_view(
                observation.packet,
                observation.receptions,
            )
        except ValueError as exc:
            logger.warning(
                "Descartado paquete live inválido "
                "source=%s packet_id=%s: %s",
                observation.packet.source,
                observation.packet.packet_id,
                exc,
            )
            continue

        seen_event_ids.add(event_id)
        views.append(view)

    return build_live_document(
        views,
        generated_at=generated_at,
        source_states={
            "ozulo_map": LiveSourceState(
                previous_cursor=batch.previous_cursor,
                next_cursor=batch.next_cursor,
                possible_gap=batch.possible_gap,
            )
        },
    )


def _live_document_path(
    output: Path | str,
) -> Path:
    output_path = Path(
        output
    ).expanduser().resolve()

    if output_path.exists() and output_path.is_dir():
        return output_path / LIVE_FILENAME

    if output_path.name == LIVE_FILENAME:
        return output_path

    if output_path.suffix:
        return output_path

    return output_path / LIVE_FILENAME


def read_live_document(
    output: Path | str,
) -> dict[str, Any] | None:
    """Le o documento live anterior, se existe."""

    path = _live_document_path(output)

    if not path.exists():
        return None

    document = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(document, dict):
        raise ValueError(
            "O documento live anterior non é un obxecto"
        )

    if document.get("schema") != LIVE_SCHEMA_ID:
        raise ValueError(
            "O documento live anterior non usa o schema esperado"
        )

    events = document.get("events")

    if not isinstance(events, list):
        raise ValueError(
            "O documento live anterior non contén events válidos"
        )

    # Compatibilidade dentro de live/v1:
    # eventos escritos antes de incorporar Telemetry estruturada
    # non incluían a propiedade ``telemetry``.
    #
    # Normalizámolos a ``null`` ao lelos para que poidan convivir
    # durante a xanela deslizante dunha hora cos eventos novos.
    normalized_events = []

    for event in events:
        if not isinstance(event, dict):
            raise ValueError(
                "Un evento live anterior non é un obxecto"
            )

        normalized_event = dict(event)

        normalized_event.setdefault(
            "telemetry",
            None,
        )

        normalized_events.append(
            normalized_event
        )

    normalized_document = dict(
        document
    )

    normalized_document["events"] = (
        normalized_events
    )

    return normalized_document


def _timestamp_to_microseconds(
    value: str,
) -> int:
    if not isinstance(value, str) or not value:
        raise ValueError(
            "generated_at debe ser unha data ISO 8601"
        )

    normalized = value

    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    moment = datetime.fromisoformat(normalized)

    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)

    return int(
        moment.timestamp() * 1_000_000
    )


def merge_live_documents(
    previous: Mapping[str, Any] | None,
    current: Mapping[str, Any],
    *,
    retention_seconds: int = LIVE_RETENTION_SECONDS,
) -> dict[str, Any]:
    """Fusiona batches live nunha xanela temporal deslizante."""

    if current.get("schema") != LIVE_SCHEMA_ID:
        raise ValueError(
            "O documento live actual non usa o schema esperado"
        )

    if (
        not isinstance(retention_seconds, int)
        or retention_seconds <= 0
    ):
        raise ValueError(
            "retention_seconds debe ser un enteiro positivo"
        )

    generated_at = current.get("generated_at")

    cutoff_us = (
        _timestamp_to_microseconds(generated_at)
        - retention_seconds * 1_000_000
    )

    documents = []

    if previous is not None:
        if previous.get("schema") != LIVE_SCHEMA_ID:
            raise ValueError(
                "O documento live anterior non usa o schema esperado"
            )

        documents.append(previous)

    documents.append(current)

    events_by_id: dict[str, dict[str, Any]] = {}

    for document in documents:
        events = document.get("events")

        if not isinstance(events, list):
            raise ValueError(
                "O documento live non contén events válidos"
            )

        for event in events:
            if not isinstance(event, dict):
                raise ValueError(
                    "Un evento live non é un obxecto"
                )

            event_id = event.get("id")
            imported_at_us = event.get("imported_at_us")

            if not isinstance(event_id, str) or not event_id:
                raise ValueError(
                    "Un evento live non ten id válido"
                )

            if (
                not isinstance(imported_at_us, int)
                or isinstance(imported_at_us, bool)
            ):
                raise ValueError(
                    "Un evento live non ten imported_at_us válido"
                )

            if imported_at_us < cutoff_us:
                continue

            # O batch actual, procesado por último, prevalece
            # se reaparece un mesmo evento.
            events_by_id[event_id] = dict(event)

    events = sorted(
        events_by_id.values(),
        key=lambda event: (
            event["imported_at_us"],
            event.get("packet_id", 0),
            event.get("from_id", ""),
        ),
    )

    return {
        "schema": LIVE_SCHEMA_ID,
        "generated_at": current["generated_at"],
        "sources": dict(current.get("sources", {})),
        "events": events,
    }


def _serialize_live_document(
    document: Mapping[str, Any],
) -> bytes:
    if not isinstance(document, Mapping):
        raise TypeError(
            "document debe ser un mapping"
        )

    if document.get("schema") != LIVE_SCHEMA_ID:
        raise ValueError(
            "O documento non usa o schema live esperado"
        )

    generated_at = document.get("generated_at")

    if (
        not isinstance(generated_at, str)
        or not generated_at
    ):
        raise ValueError(
            "O documento live necesita generated_at"
        )

    return (
        json.dumps(
            document,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY,
    )

    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_live_document(
    output: Path | str,
    document: Mapping[str, Any],
) -> Path:
    """Escribe live.json atomicamente sen tocar o manifesto principal."""

    serialized = _serialize_live_document(
        document
    )

    document_path = _live_document_path(
        output
    )

    parent = document_path.parent

    parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=parent,
            prefix=f".{document_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(
                temporary.name
            )

            temporary.write(serialized)
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
            document_path,
        )
        temporary_path = None

        _fsync_directory(parent)

    except Exception:
        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink()

        raise

    return document_path
