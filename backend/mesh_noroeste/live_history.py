"""Persistencia SQLite independente do histórico do tráfico live."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator


LIVE_HISTORY_SCHEMA_VERSION = 1
LIVE_HISTORY_RETENTION_SECONDS = (
    30 * 24 * 60 * 60
)


@contextmanager
def _open_history_connection(
    database_path: Path,
) -> Iterator[sqlite3.Connection]:
    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        database_path,
        timeout=5.0,
    )

    try:
        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA busy_timeout = 5000"
        )
        connection.execute(
            "PRAGMA journal_mode = WAL"
        )
        connection.execute(
            "PRAGMA synchronous = NORMAL"
        )

        with connection:
            yield connection

    finally:
        connection.close()


def _timestamp_to_microseconds(
    value: Any,
) -> int:
    if isinstance(value, bool):
        raise TypeError(
            "reference debe ser unha data ou timestamp"
        )

    if isinstance(value, (int, float)):
        return int(float(value) * 1_000_000)

    if not isinstance(value, str) or not value:
        raise TypeError(
            "reference debe ser unha data ou timestamp"
        )

    normalized = value

    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    moment = datetime.fromisoformat(normalized)

    if moment.tzinfo is None:
        moment = moment.replace(
            tzinfo=timezone.utc
        )

    return int(
        moment.timestamp() * 1_000_000
    )



@dataclass(frozen=True, slots=True)
class LiveHistoryHourBucket:
    """Resumo dunha hora UTC dispoñible no histórico."""

    start_us: int
    end_us: int
    events: int
    traceroutes: int



@dataclass(frozen=True, slots=True)
class LiveHistoryQueryResult:
    """Resultado limitado dunha consulta temporal."""

    events: tuple[dict[str, Any], ...]
    total: int
    truncated: bool
    start_us: int
    end_us: int



def _history_microseconds(
    value: int,
    field: str,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
    ):
        raise TypeError(
            f"{field} debe ser un enteiro en microsegundos"
        )

    if value < 0:
        raise ValueError(
            f"{field} non pode ser negativo"
        )

    return value


def _history_limit(
    value: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
    ):
        raise TypeError(
            "limit debe ser un enteiro"
        )

    if not 1 <= value <= 5000:
        raise ValueError(
            "limit debe estar entre 1 e 5000"
        )

    return value


def _history_kind(
    value: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            "kind debe ser texto"
        )

    normalized = value.strip().lower()

    if normalized not in {
        "all",
        "traceroute",
        "packet",
    }:
        raise ValueError(
            "kind debe ser all, traceroute ou packet"
        )

    return normalized



class LiveHistoryStore:
    """Almacena eventos live xa normalizados para consulta histórica."""

    def __init__(
        self,
        database_path: Path | str,
    ) -> None:
        self.database_path = Path(
            database_path
        ).expanduser().resolve()


    def initialize(self) -> None:
        with _open_history_connection(
            self.database_path
        ) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                WITHOUT ROWID;

                CREATE TABLE IF NOT EXISTS live_events (
                    event_id TEXT PRIMARY KEY,

                    imported_at_us INTEGER NOT NULL
                        CHECK (imported_at_us >= 0),

                    packet_id INTEGER NOT NULL
                        CHECK (packet_id >= 0),

                    from_id TEXT NOT NULL,
                    to_id TEXT NOT NULL,

                    portnum INTEGER NOT NULL
                        CHECK (portnum >= 0),

                    channel TEXT,

                    has_traceroute INTEGER NOT NULL
                        CHECK (has_traceroute IN (0, 1)),

                    event_json TEXT NOT NULL
                )
                WITHOUT ROWID;

                CREATE INDEX IF NOT EXISTS
                    idx_live_events_imported_at
                ON live_events (
                    imported_at_us
                );

                CREATE INDEX IF NOT EXISTS
                    idx_live_events_portnum_time
                ON live_events (
                    portnum,
                    imported_at_us
                );

                CREATE INDEX IF NOT EXISTS
                    idx_live_events_from_time
                ON live_events (
                    from_id,
                    imported_at_us
                );

                CREATE INDEX IF NOT EXISTS
                    idx_live_events_to_time
                ON live_events (
                    to_id,
                    imported_at_us
                );
                """
            )

            connection.execute(
                """
                INSERT INTO metadata (
                    key,
                    value
                )
                VALUES (
                    'schema_version',
                    ?
                )
                ON CONFLICT (key)
                DO UPDATE SET
                    value = excluded.value
                """,
                (
                    str(
                        LIVE_HISTORY_SCHEMA_VERSION
                    ),
                ),
            )


    def save_events(
        self,
        events: Iterable[Mapping[str, Any]],
    ) -> int:
        """Garda eventos idempotentemente polo seu identificador."""

        received = tuple(events)

        if not received:
            self.initialize()
            return 0

        rows = []

        for event in received:
            if not isinstance(event, Mapping):
                raise TypeError(
                    "Cada evento histórico debe ser un mapping"
                )

            event_id = event.get("id")
            imported_at_us = event.get(
                "imported_at_us"
            )
            packet_id = event.get("packet_id")
            from_id = event.get("from_id")
            to_id = event.get("to_id")
            portnum = event.get("portnum")

            if not isinstance(event_id, str) or not event_id:
                raise ValueError(
                    "Un evento histórico non ten id válido"
                )

            if (
                isinstance(imported_at_us, bool)
                or not isinstance(imported_at_us, int)
                or imported_at_us < 0
            ):
                raise ValueError(
                    "Un evento histórico non ten "
                    "imported_at_us válido"
                )

            if (
                isinstance(packet_id, bool)
                or not isinstance(packet_id, int)
                or packet_id < 0
            ):
                raise ValueError(
                    "Un evento histórico non ten packet_id válido"
                )

            if not isinstance(from_id, str) or not from_id:
                raise ValueError(
                    "Un evento histórico non ten from_id válido"
                )

            if not isinstance(to_id, str) or not to_id:
                raise ValueError(
                    "Un evento histórico non ten to_id válido"
                )

            if (
                isinstance(portnum, bool)
                or not isinstance(portnum, int)
                or portnum < 0
            ):
                raise ValueError(
                    "Un evento histórico non ten portnum válido"
                )

            rows.append(
                (
                    event_id,
                    imported_at_us,
                    packet_id,
                    from_id,
                    to_id,
                    portnum,
                    event.get("channel"),
                    int(
                        event.get("traceroute")
                        is not None
                    ),
                    json.dumps(
                        dict(event),
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                        allow_nan=False,
                    ),
                )
            )

        self.initialize()

        with _open_history_connection(
            self.database_path
        ) as connection:
            before = connection.total_changes

            connection.executemany(
                """
                INSERT INTO live_events (
                    event_id,
                    imported_at_us,
                    packet_id,
                    from_id,
                    to_id,
                    portnum,
                    channel,
                    has_traceroute,
                    event_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (event_id)
                DO UPDATE SET
                    imported_at_us = excluded.imported_at_us,
                    packet_id = excluded.packet_id,
                    from_id = excluded.from_id,
                    to_id = excluded.to_id,
                    portnum = excluded.portnum,
                    channel = excluded.channel,
                    has_traceroute = excluded.has_traceroute,
                    event_json = excluded.event_json
                """,
                rows,
            )

            return (
                connection.total_changes
                - before
            )


    def prune(
        self,
        *,
        reference: Any,
        retention_seconds: int = (
            LIVE_HISTORY_RETENTION_SECONDS
        ),
    ) -> int:
        """Elimina eventos anteriores á xanela de retención."""

        if (
            isinstance(retention_seconds, bool)
            or not isinstance(retention_seconds, int)
            or retention_seconds <= 0
        ):
            raise ValueError(
                "retention_seconds debe ser positivo"
            )

        reference_us = _timestamp_to_microseconds(
            reference
        )

        cutoff_us = (
            reference_us
            - retention_seconds * 1_000_000
        )

        self.initialize()

        with _open_history_connection(
            self.database_path
        ) as connection:
            return connection.execute(
                """
                DELETE FROM live_events
                WHERE imported_at_us < ?
                """,
                (cutoff_us,),
            ).rowcount


    def count(self) -> int:
        self.initialize()

        with _open_history_connection(
            self.database_path
        ) as connection:
            return int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM live_events
                    """
                ).fetchone()[0]
            )

    def query_events(
        self,
        *,
        start_us: int,
        end_us: int,
        limit: int = 500,
        kind: str = "all",
    ) -> LiveHistoryQueryResult:
        """Consulta eventos nun intervalo temporal semiaberto.

        ``start_us`` está incluído e ``end_us`` excluído.
        O resultado ordénase do evento máis antigo ao máis novo.
        """

        normalized_start = _history_microseconds(
            start_us,
            "start_us",
        )
        normalized_end = _history_microseconds(
            end_us,
            "end_us",
        )
        normalized_limit = _history_limit(
            limit
        )
        normalized_kind = _history_kind(
            kind
        )

        if normalized_end <= normalized_start:
            raise ValueError(
                "end_us debe ser maior ca start_us"
            )

        clauses = [
            "imported_at_us >= ?",
            "imported_at_us < ?",
        ]

        parameters: list[Any] = [
            normalized_start,
            normalized_end,
        ]

        if normalized_kind == "traceroute":
            clauses.append(
                "has_traceroute = 1"
            )
        elif normalized_kind == "packet":
            clauses.append(
                "has_traceroute = 0"
            )

        where = " AND ".join(
            clauses
        )

        self.initialize()

        with _open_history_connection(
            self.database_path
        ) as connection:
            total = int(
                connection.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM live_events
                    WHERE {where}
                    """,
                    parameters,
                ).fetchone()[0]
            )

            rows = connection.execute(
                f"""
                SELECT event_json
                FROM live_events
                WHERE {where}
                ORDER BY
                    imported_at_us ASC,
                    packet_id ASC,
                    event_id ASC
                LIMIT ?
                """,
                [
                    *parameters,
                    normalized_limit,
                ],
            ).fetchall()

        events = tuple(
            json.loads(
                row["event_json"]
            )
            for row in rows
        )

        return LiveHistoryQueryResult(
            events=events,
            total=total,
            truncated=total > len(events),
            start_us=normalized_start,
            end_us=normalized_end,
        )


    def hour_buckets(
        self,
    ) -> tuple[LiveHistoryHourBucket, ...]:
        """Lista as horas UTC que conteñen eventos."""

        hour_us = (
            60 * 60 * 1_000_000
        )

        self.initialize()

        with _open_history_connection(
            self.database_path
        ) as connection:
            rows = connection.execute(
                """
                SELECT
                    (
                        imported_at_us / ?
                    ) * ? AS start_us,
                    COUNT(*) AS events,
                    SUM(has_traceroute) AS traceroutes
                FROM live_events
                GROUP BY start_us
                ORDER BY start_us ASC
                """,
                (
                    hour_us,
                    hour_us,
                ),
            ).fetchall()

        return tuple(
            LiveHistoryHourBucket(
                start_us=int(row["start_us"]),
                end_us=(
                    int(row["start_us"])
                    + hour_us
                ),
                events=int(row["events"]),
                traceroutes=int(
                    row["traceroutes"] or 0
                ),
            )
            for row in rows
        )



    def node_hours(
        self,
    ) -> dict[str, tuple[int, ...]]:
        """Indexa as horas UTC nas que participa cada nodo.

        Considéranse participantes:
        - orixe;
        - destino, agás broadcast;
        - gateways observadores;
        - nodos presentes nas rutas RouteDiscovery.
        """

        hour_us = (
            60 * 60 * 1_000_000
        )

        self.initialize()

        with _open_history_connection(
            self.database_path
        ) as connection:
            rows = connection.execute(
                """
                SELECT
                    imported_at_us,
                    from_id,
                    to_id,
                    event_json
                FROM live_events
                ORDER BY imported_at_us ASC
                """
            ).fetchall()

        index: dict[str, set[int]] = {}

        def add(
            node_id: Any,
            hour_start_us: int,
        ) -> None:
            if (
                not isinstance(node_id, str)
                or not node_id
                or node_id == "meshtastic:!ffffffff"
            ):
                return

            index.setdefault(
                node_id,
                set(),
            ).add(
                hour_start_us
            )

        for row in rows:
            imported_at_us = int(
                row["imported_at_us"]
            )

            hour_start_us = (
                imported_at_us // hour_us
            ) * hour_us

            add(
                row["from_id"],
                hour_start_us,
            )

            add(
                row["to_id"],
                hour_start_us,
            )

            document = json.loads(
                row["event_json"]
            )

            for stage in (
                document.get("observed", {})
                .get("stages", [])
            ):
                for gateway in (
                    stage.get("gateways", [])
                ):
                    add(
                        gateway.get("gateway_id"),
                        hour_start_us,
                    )

            traceroute = document.get(
                "traceroute"
            )

            if isinstance(traceroute, Mapping):
                for direction in (
                    "towards",
                    "back",
                ):
                    for node_id in (
                        traceroute.get(direction)
                        or []
                    ):
                        add(
                            node_id,
                            hour_start_us,
                        )

        return {
            node_id: tuple(
                sorted(hours)
            )
            for node_id, hours in sorted(
                index.items()
            )
        }


    def time_bounds(
        self,
    ) -> tuple[int | None, int | None]:
        self.initialize()

        with _open_history_connection(
            self.database_path
        ) as connection:
            row = connection.execute(
                """
                SELECT
                    MIN(imported_at_us),
                    MAX(imported_at_us)
                FROM live_events
                """
            ).fetchone()

        return (
            (
                None
                if row[0] is None
                else int(row[0])
            ),
            (
                None
                if row[1] is None
                else int(row[1])
            ),
        )
