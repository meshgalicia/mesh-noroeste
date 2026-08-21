"""Execución transaccional dunha iteración do tráfico live."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from mesh_noroeste.experiment_publication import (
    publish_experiment_report,
)
from mesh_noroeste.experiment_store import (
    connect_experiment_store,
    store_live_document,
)
from mesh_noroeste.live_history import (
    LiveHistoryStore,
)
from mesh_noroeste.live_history_publication import (
    HOUR_US,
    cleanup_history_publication,
    publish_history_hour,
    publish_history_manifest,
)
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


def _history_hours_for_events(
    events: Any,
) -> tuple[int, ...]:
    """Obtén as horas UTC afectadas polos eventos dun batch."""

    starts: set[int] = set()

    for event in events:
        if not isinstance(event, Mapping):
            continue

        imported_at_us = event.get(
            "imported_at_us"
        )

        if (
            isinstance(imported_at_us, bool)
            or not isinstance(imported_at_us, int)
            or imported_at_us < 0
        ):
            continue

        starts.add(
            (
                imported_at_us // HOUR_US
            ) * HOUR_US
        )

    return tuple(
        sorted(starts)
    )



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

    current_document = document_builder(
        batch,
        generated_at=generated_at,
    )

    history_store = LiveHistoryStore(
        store.database_path.with_name(
            "live-history.db"
        )
    )

    history_store.save_events(
        current_document.get("events", ())
    )

    pruned_events = history_store.prune(
        reference=current_document["generated_at"]
    )

    history_events = current_document.get(
        "events",
        ()
    )

    history_hours = set(
        _history_hours_for_events(
            history_events
        )
    )

    if pruned_events > 0:
        oldest_event_us, _ = (
            history_store.time_bounds()
        )

        if oldest_event_us is not None:
            history_hours.add(
                (
                    oldest_event_us // HOUR_US
                ) * HOUR_US
            )

    for hour_start_us in sorted(
        history_hours
    ):
        publish_history_hour(
            history_store,
            output,
            start_us=hour_start_us,
            generated_at=current_document["generated_at"],
        )

    publish_history_manifest(
        history_store,
        output,
        generated_at=current_document["generated_at"],
    )

    cleanup_history_publication(
        history_store,
        output,
    )

    previous_document = read_live_document(
        output
    )

    document = merge_live_documents(
        previous_document,
        current_document,
    )

    output_path = writer(
        output,
        document,
    )

    experiment_database_path = (
        store.database_path.with_name(
            "meshtastic-experiment.db"
        )
    )

    experiment_connection = (
        connect_experiment_store(
            experiment_database_path
        )
    )

    try:
        store_live_document(
            experiment_connection,
            current_document,
        )
    finally:
        experiment_connection.close()

    publish_experiment_report(
        experiment_database_path,
        output,
        generated_at=(
            current_document["generated_at"]
        ),
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
