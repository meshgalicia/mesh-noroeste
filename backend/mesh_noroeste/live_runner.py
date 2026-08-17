"""Execución transaccional dunha iteración do tráfico live."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from mesh_noroeste.live_pipeline import (
    build_live_document_from_ozulo_batch,
    merge_live_documents,
    read_live_document,
    write_live_document,
)
from mesh_noroeste.ozulo_live_poll import (
    OzuloLiveBatch,
    poll_ozulo_live_once,
)
from mesh_noroeste.storage import ObservationStore


OZULO_LIVE_SOURCE = "ozulo_map"


@dataclass(frozen=True, slots=True)
class LiveRunResult:
    """Resultado dunha iteración completa xa publicada."""

    source: str
    previous_cursor: int | None
    next_cursor: int | None
    events: int
    possible_gap: bool
    bytes_received: int
    output_path: Path


def run_ozulo_live_once(
    store: ObservationStore,
    output: Path | str,
    *,
    generated_at: Any,
    poller: Callable[..., OzuloLiveBatch] = poll_ozulo_live_once,
    document_builder: Callable[..., dict[str, Any]] = (
        build_live_document_from_ozulo_batch
    ),
    writer: Callable[
        [Path | str, Mapping[str, Any]],
        Path,
    ] = write_live_document,
) -> LiveRunResult:
    """Obtén, publica e confirma unha iteración live de O Zulo.

    O cursor persistente só avanza despois de completar con éxito
    a escritura do documento público. Deste xeito, un fallo anterior
    á confirmación pode provocar repetición na seguinte execución,
    pero non perda silenciosa de eventos.
    """

    if not isinstance(store, ObservationStore):
        raise TypeError(
            "store debe ser ObservationStore"
        )

    previous_cursor = store.load_live_cursor(
        OZULO_LIVE_SOURCE
    )

    batch = poller(
        cursor=previous_cursor,
    )

    if not isinstance(batch, OzuloLiveBatch):
        raise TypeError(
            "poller debe devolver OzuloLiveBatch"
        )

    if batch.previous_cursor != previous_cursor:
        raise ValueError(
            "O batch live non corresponde co cursor solicitado"
        )

    document = document_builder(
        batch,
        generated_at=generated_at,
    )

    previous_document = read_live_document(
        output
    )

    document = merge_live_documents(
        previous_document,
        document,
    )

    output_path = writer(
        output,
        document,
    )

    next_cursor = batch.next_cursor

    if next_cursor is not None:
        store.save_live_cursor(
            OZULO_LIVE_SOURCE,
            next_cursor,
            updated_at=generated_at,
        )

    return LiveRunResult(
        source=OZULO_LIVE_SOURCE,
        previous_cursor=previous_cursor,
        next_cursor=next_cursor,
        events=len(batch.observations),
        possible_gap=batch.possible_gap,
        bytes_received=batch.bytes_received,
        output_path=Path(output_path),
    )
