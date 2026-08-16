"""Construción e escritura do documento público live."""

from __future__ import annotations

from collections.abc import Mapping
import json
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

    views = tuple(
        build_live_packet_view(
            observation.packet,
            observation.receptions,
        )
        for observation in batch.observations
    )

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

    output_path = Path(
        output
    ).expanduser().resolve()

    if output_path.exists() and output_path.is_dir():
        document_path = (
            output_path
            / LIVE_FILENAME
        )
    elif output_path.name == LIVE_FILENAME:
        document_path = output_path
    elif output_path.suffix:
        document_path = output_path
    else:
        document_path = (
            output_path
            / LIVE_FILENAME
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
