"""Persistencia SQLite de observaciones de nodos y conexiones."""

from __future__ import annotations

from dataclasses import dataclass

from collections.abc import Iterator
from contextlib import contextmanager
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable

from mesh_noroeste.normalization import canonical_node_id
from mesh_noroeste.domain import (
    SOURCE_ORDER,
    EdgeObservation,
    NeighborObservation,
    NodeObservation,
    ObserverReception,
    make_edge_observation,
    make_neighbor_observation,
    make_observation,
    make_observer_reception,
)
from mesh_noroeste.normalization import (
    normalize_timestamp,
)


SCHEMA_VERSION = 9


@contextmanager
def _open_connection(
    database_path: Path,
) -> Iterator[sqlite3.Connection]:
    """Abre una transacción y cierra siempre la conexión."""

    connection = sqlite3.connect(
        database_path,
        timeout=5.0,
    )

    try:
        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )
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


def _normalize_source(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("source debe ser texto")

    normalized = value.strip().lower()

    if normalized not in SOURCE_ORDER:
        raise ValueError(
            f"Fuente no admitida: {value!r}"
        )

    return normalized


_LEGACY_SOURCE_CONSTRAINT = re.compile(
    r"'meshview_es'\s*,\s*"
    r"'malha_pt'\s*,\s*"
    r"'meshcore_map'"
)


_MESHCORE_HUB_SOURCE_CONSTRAINT = re.compile(
    r"'meshview_es'\s*,\s*"
    r"'malha_pt'\s*,\s*"
    r"'ozulo_map'\s*,\s*"
    r"'meshcore_map'"
)

_CREATE_TABLE_HEAD = re.compile(
    (
        r"^CREATE TABLE\s+"
        r"(?:IF NOT EXISTS\s+)?"
        r"(?:"
        r'"[^"]+"'
        r"|`[^`]+`"
        r"|\[[^\]]+\]"
        r"|[^\s(]+"
        r")"
    ),
    re.IGNORECASE,
)


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _create_indexes(
    connection: sqlite3.Connection,
) -> None:
    connection.executescript(
        """
        CREATE INDEX IF NOT EXISTS
            idx_node_observations_canonical_time
        ON node_observations (
            canonical_id,
            observed_at
        );

        CREATE INDEX IF NOT EXISTS
            idx_node_observations_source_time
        ON node_observations (
            source,
            observed_at
        );

        CREATE INDEX IF NOT EXISTS
            idx_edge_observations_canonical_time
        ON edge_observations (
            canonical_id,
            observed_at
        );

        CREATE INDEX IF NOT EXISTS
            idx_edge_observations_source_time
        ON edge_observations (
            source,
            observed_at
        );

        CREATE INDEX IF NOT EXISTS
            idx_edge_observations_endpoints
        ON edge_observations (
            network,
            from_source_id,
            to_source_id
        );

        CREATE INDEX IF NOT EXISTS
            idx_neighbor_observations_pair_time
        ON neighbor_observations (
            source,
            from_source_id,
            to_source_id,
            observed_at
        );

        CREATE INDEX IF NOT EXISTS
            idx_neighbor_observations_endpoints
        ON neighbor_observations (
            from_source_id,
            to_source_id
        );

        CREATE INDEX IF NOT EXISTS
            idx_observer_receptions_node_time
        ON observer_receptions (
            node_source_id,
            observed_at
        );

        CREATE INDEX IF NOT EXISTS
            idx_observer_receptions_observer_time
        ON observer_receptions (
            observer_source_id,
            observed_at
        );

        CREATE INDEX IF NOT EXISTS
            idx_edge_observation_cursors_endpoints
        ON edge_observation_cursors (
            network,
            from_source_id,
            to_source_id
        );

        CREATE INDEX IF NOT EXISTS
            idx_source_runs_source_started
        ON source_runs (
            source,
            started_at
        );
        """
    )


def _migrate_source_constraints(
    connection: sqlite3.Connection,
) -> None:
    """Amplía as restricións SQLite para admitir O Zulo."""

    migrated = False

    for table in (
        "node_observations",
        "edge_observations",
        "source_runs",
    ):
        row = connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
            """,
            (table,),
        ).fetchone()

        if row is None or row["sql"] is None:
            raise RuntimeError(
                f"Falta a táboa SQLite {table}"
            )

        create_sql = row["sql"]

        if "'ozulo_map'" in create_sql:
            continue

        updated_sql, replacements = (
            _LEGACY_SOURCE_CONSTRAINT.subn(
                (
                    "'meshview_es', "
                    "'malha_pt', "
                    "'ozulo_map', "
                    "'meshcore_map'"
                ),
                create_sql,
                count=1,
            )
        )

        if replacements != 1:
            raise RuntimeError(
                "Non se puido ampliar a restrición "
                f"de fonte de {table}"
            )

        temporary = f"{table}_source_v4"
        quoted_table = _quote_identifier(table)
        quoted_temporary = _quote_identifier(
            temporary
        )

        connection.execute(
            f"DROP TABLE IF EXISTS {quoted_temporary}"
        )

        temporary_sql, renamed = (
            _CREATE_TABLE_HEAD.subn(
                f"CREATE TABLE {quoted_temporary}",
                updated_sql,
                count=1,
            )
        )

        if renamed != 1:
            raise RuntimeError(
                "Non se puido preparar a migración "
                f"de {table}"
            )

        connection.execute(temporary_sql)

        columns = [
            item["name"]
            for item in connection.execute(
                f"PRAGMA table_info({quoted_table})"
            )
        ]

        if not columns:
            raise RuntimeError(
                f"A táboa {table} non ten columnas"
            )

        column_list = ", ".join(
            _quote_identifier(column)
            for column in columns
        )

        connection.execute(
            f"""
            INSERT INTO {quoted_temporary} (
                {column_list}
            )
            SELECT
                {column_list}
            FROM {quoted_table}
            """
        )
        connection.execute(
            f"DROP TABLE {quoted_table}"
        )
        connection.execute(
            f"""
            ALTER TABLE {quoted_temporary}
            RENAME TO {quoted_table}
            """
        )

        migrated = True

    if migrated:
        _create_indexes(connection)



def _migrate_meshcore_hub_source_constraints(
    connection: sqlite3.Connection,
) -> None:
    """Amplía SQLite para admitir a fonte MeshCore Hub."""

    migrated = False

    for table in (
        "node_observations",
        "edge_observations",
        "node_observation_cursors",
        "edge_observation_cursors",
        "source_runs",
    ):
        row = connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
            """,
            (table,),
        ).fetchone()

        if row is None or row["sql"] is None:
            raise RuntimeError(
                f"Falta a táboa SQLite {table}"
            )

        create_sql = row["sql"]

        if "'meshcore_hub'" in create_sql:
            continue

        updated_sql, replacements = (
            _MESHCORE_HUB_SOURCE_CONSTRAINT.subn(
                (
                    "'meshview_es', "
                    "'malha_pt', "
                    "'ozulo_map', "
                    "'meshcore_map', "
                    "'meshcore_hub'"
                ),
                create_sql,
                count=1,
            )
        )

        if replacements != 1:
            raise RuntimeError(
                "Non se puido engadir MeshCore Hub "
                f"á restrición de fonte de {table}"
            )

        temporary = f"{table}_source_v7"
        quoted_table = _quote_identifier(table)
        quoted_temporary = _quote_identifier(
            temporary
        )

        connection.execute(
            f"DROP TABLE IF EXISTS {quoted_temporary}"
        )

        temporary_sql, renamed = (
            _CREATE_TABLE_HEAD.subn(
                f"CREATE TABLE {quoted_temporary}",
                updated_sql,
                count=1,
            )
        )

        if renamed != 1:
            raise RuntimeError(
                "Non se puido preparar a migración "
                f"de {table}"
            )

        connection.execute(temporary_sql)

        columns = [
            item["name"]
            for item in connection.execute(
                f"PRAGMA table_info({quoted_table})"
            )
        ]

        if not columns:
            raise RuntimeError(
                f"A táboa {table} non ten columnas"
            )

        column_list = ", ".join(
            _quote_identifier(column)
            for column in columns
        )

        connection.execute(
            f"""
            INSERT INTO {quoted_temporary} (
                {column_list}
            )
            SELECT
                {column_list}
            FROM {quoted_table}
            """
        )
        connection.execute(
            f"DROP TABLE {quoted_table}"
        )
        connection.execute(
            f"""
            ALTER TABLE {quoted_temporary}
            RENAME TO {quoted_table}
            """
        )

        migrated = True

    if migrated:
        _create_indexes(connection)

def _populate_observation_cursors(
    connection: sqlite3.Connection,
) -> None:
    """Migra o último timestamp coñecido a cursores mínimos."""

    connection.execute(
        """
        INSERT INTO node_observation_cursors (
            source,
            canonical_id,
            last_observed_at
        )
        SELECT
            source,
            canonical_id,
            observed_at
        FROM (
            SELECT
                source,
                canonical_id,
                observed_at,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        source,
                        canonical_id
                    ORDER BY
                        observed_at DESC,
                        id DESC
                ) AS position
            FROM node_observations
        )
        WHERE position = 1
        ON CONFLICT (
            source,
            canonical_id
        )
        DO UPDATE SET
            last_observed_at =
                excluded.last_observed_at
        WHERE excluded.last_observed_at >
            node_observation_cursors.last_observed_at
        """
    )

    connection.execute(
        """
        INSERT INTO edge_observation_cursors (
            source,
            canonical_id,
            network,
            from_source_id,
            to_source_id,
            last_observed_at
        )
        SELECT
            source,
            canonical_id,
            network,
            from_source_id,
            to_source_id,
            observed_at
        FROM (
            SELECT
                source,
                canonical_id,
                network,
                from_source_id,
                to_source_id,
                observed_at,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        source,
                        canonical_id
                    ORDER BY
                        observed_at DESC,
                        id DESC
                ) AS position
            FROM edge_observations
        )
        WHERE position = 1
        ON CONFLICT (
            source,
            canonical_id
        )
        DO UPDATE SET
            network = excluded.network,
            from_source_id =
                excluded.from_source_id,
            to_source_id =
                excluded.to_source_id,
            last_observed_at =
                excluded.last_observed_at
        WHERE excluded.last_observed_at >
            edge_observation_cursors.last_observed_at
        """
    )


@dataclass(frozen=True, slots=True)
class NodePurgeResult:
    """Resultado del borrado persistente de un nodo."""

    node_observations_deleted: int
    edge_observations_deleted: int


class ObservationStore:
    """Almacén SQLite de observaciones de nodos."""

    def __init__(
        self,
        database_path: Path | str,
    ) -> None:
        self.database_path = Path(
            database_path
        ).expanduser().resolve()

    def initialize(self) -> None:
        """Crea o valida el esquema de la base de datos."""

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with _open_connection(
            self.database_path
        ) as connection:
            current_version = connection.execute(
                "PRAGMA user_version"
            ).fetchone()[0]

            if current_version not in {
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                SCHEMA_VERSION,
            }:
                raise RuntimeError(
                    "Versión SQLite incompatible: "
                    f"{current_version}; "
                    f"esperada: {SCHEMA_VERSION}"
                )

            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS node_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    canonical_id TEXT NOT NULL,

                    network TEXT NOT NULL
                        CHECK (
                            network IN (
                                'meshtastic',
                                'meshcore'
                            )
                        ),

                    source TEXT NOT NULL
                        CHECK (
                            source IN (
                                'meshview_es',
                                'malha_pt',
                                'ozulo_map',
                                'meshcore_map',
                                'meshcore_hub'
                            )
                        ),

                    source_id TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    first_seen TEXT,

                    short_name TEXT,
                    long_name TEXT,
                    hardware TEXT,
                    role TEXT,
                    node_type TEXT,
                    is_observer INTEGER
                        CHECK (
                            is_observer IS NULL
                            OR is_observer IN (0, 1)
                        ),

                    latitude REAL,
                    longitude REAL,
                    altitude_m REAL,
                    position_precision_bits INTEGER
                        CHECK (
                            position_precision_bits IS NULL
                            OR position_precision_bits
                                BETWEEN 0 AND 32
                        ),
                    position_updated_at TEXT,

                    metrics_json TEXT NOT NULL,
                    radio_json TEXT NOT NULL,

                    inserted_at TEXT NOT NULL DEFAULT (
                        strftime(
                            '%Y-%m-%dT%H:%M:%SZ',
                            'now'
                        )
                    ),

                    UNIQUE (
                        source,
                        canonical_id,
                        observed_at
                    ),

                    CHECK (
                        (
                            latitude IS NULL
                            AND longitude IS NULL
                            AND position_updated_at IS NULL
                        )
                        OR
                        (
                            latitude IS NOT NULL
                            AND longitude IS NOT NULL
                            AND position_updated_at IS NOT NULL
                        )
                    )
                );

                CREATE INDEX IF NOT EXISTS
                    idx_node_observations_canonical_time
                ON node_observations (
                    canonical_id,
                    observed_at
                );

                CREATE INDEX IF NOT EXISTS
                    idx_node_observations_source_time
                ON node_observations (
                    source,
                    observed_at
                );

                CREATE TABLE IF NOT EXISTS edge_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    canonical_id TEXT NOT NULL,

                    network TEXT NOT NULL
                        CHECK (
                            network IN (
                                'meshtastic',
                                'meshcore'
                            )
                        ),

                    source TEXT NOT NULL
                        CHECK (
                            source IN (
                                'meshview_es',
                                'malha_pt',
                                'ozulo_map',
                                'meshcore_map',
                                'meshcore_hub'
                            )
                        ),

                    from_source_id TEXT NOT NULL,
                    to_source_id TEXT NOT NULL,

                    edge_type TEXT NOT NULL
                        CHECK (
                            edge_type IN (
                                'neighbor',
                                'traceroute',
                                'observed',
                                'unknown'
                            )
                        ),

                    directed INTEGER NOT NULL
                        CHECK (directed IN (0, 1)),

                    observed_at TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,

                    inserted_at TEXT NOT NULL DEFAULT (
                        strftime(
                            '%Y-%m-%dT%H:%M:%SZ',
                            'now'
                        )
                    ),

                    UNIQUE (
                        source,
                        canonical_id,
                        observed_at
                    ),

                    CHECK (
                        from_source_id <> to_source_id
                    ),

                    CHECK (
                        edge_type <> 'neighbor'
                        OR directed = 0
                    ),

                    CHECK (
                        edge_type <> 'traceroute'
                        OR directed = 1
                    )
                );

                CREATE INDEX IF NOT EXISTS
                    idx_edge_observations_canonical_time
                ON edge_observations (
                    canonical_id,
                    observed_at
                );

                CREATE INDEX IF NOT EXISTS
                    idx_edge_observations_source_time
                ON edge_observations (
                    source,
                    observed_at
                );

                CREATE INDEX IF NOT EXISTS
                    idx_edge_observations_endpoints
                ON edge_observations (
                    network,
                    from_source_id,
                    to_source_id
                );

                CREATE TABLE IF NOT EXISTS
                    neighbor_observations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,

                        source TEXT NOT NULL
                            CHECK (
                                source IN (
                                    'meshview_es',
                                    'malha_pt',
                                    'ozulo_map'
                                )
                            ),

                        from_source_id TEXT NOT NULL,
                        to_source_id TEXT NOT NULL,
                        observed_at TEXT NOT NULL,
                        snr_db REAL NOT NULL,

                        inserted_at TEXT NOT NULL DEFAULT (
                            strftime(
                                '%Y-%m-%dT%H:%M:%SZ',
                                'now'
                            )
                        ),

                        UNIQUE (
                            source,
                            from_source_id,
                            to_source_id,
                            observed_at
                        ),

                        CHECK (
                            from_source_id <> to_source_id
                        )
                    );

                CREATE INDEX IF NOT EXISTS
                    idx_neighbor_observations_pair_time
                ON neighbor_observations (
                    source,
                    from_source_id,
                    to_source_id,
                    observed_at
                );

                CREATE INDEX IF NOT EXISTS
                    idx_neighbor_observations_endpoints
                ON neighbor_observations (
                    from_source_id,
                    to_source_id
                );

                CREATE TABLE IF NOT EXISTS
                    observer_receptions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,

                        source TEXT NOT NULL
                            CHECK (
                                source = 'meshcore_hub'
                            ),

                        node_source_id TEXT NOT NULL,
                        observer_source_id TEXT NOT NULL,
                        packet_hash TEXT NOT NULL,
                        observed_at TEXT NOT NULL,
                        snr_db REAL,
                        path_len INTEGER
                            CHECK (
                                path_len IS NULL
                                OR path_len >= 0
                            ),

                        inserted_at TEXT NOT NULL DEFAULT (
                            strftime(
                                '%Y-%m-%dT%H:%M:%SZ',
                                'now'
                            )
                        ),

                        UNIQUE (
                            source,
                            node_source_id,
                            observer_source_id,
                            packet_hash
                        )
                    );

                CREATE INDEX IF NOT EXISTS
                    idx_observer_receptions_node_time
                ON observer_receptions (
                    node_source_id,
                    observed_at
                );

                CREATE INDEX IF NOT EXISTS
                    idx_observer_receptions_observer_time
                ON observer_receptions (
                    observer_source_id,
                    observed_at
                );

                CREATE TABLE IF NOT EXISTS
                    node_observation_cursors (
                        source TEXT NOT NULL
                            CHECK (
                                source IN (
                                    'meshview_es',
                                    'malha_pt',
                                    'ozulo_map',
                                    'meshcore_map',
                                    'meshcore_hub'
                                )
                            ),

                        canonical_id TEXT NOT NULL,
                        last_observed_at TEXT NOT NULL,

                        PRIMARY KEY (
                            source,
                            canonical_id
                        )
                    )
                    WITHOUT ROWID;

                CREATE TABLE IF NOT EXISTS
                    edge_observation_cursors (
                        source TEXT NOT NULL
                            CHECK (
                                source IN (
                                    'meshview_es',
                                    'malha_pt',
                                    'ozulo_map',
                                    'meshcore_map',
                                    'meshcore_hub'
                                )
                            ),

                        canonical_id TEXT NOT NULL,

                        network TEXT NOT NULL
                            CHECK (
                                network IN (
                                    'meshtastic',
                                    'meshcore'
                                )
                            ),

                        from_source_id TEXT NOT NULL,
                        to_source_id TEXT NOT NULL,
                        last_observed_at TEXT NOT NULL,

                        PRIMARY KEY (
                            source,
                            canonical_id
                        ),

                        CHECK (
                            from_source_id <> to_source_id
                        )
                    )
                    WITHOUT ROWID;

                CREATE INDEX IF NOT EXISTS
                    idx_edge_observation_cursors_endpoints
                ON edge_observation_cursors (
                    network,
                    from_source_id,
                    to_source_id
                );

                CREATE TABLE IF NOT EXISTS source_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    source TEXT NOT NULL
                        CHECK (
                            source IN (
                                'meshview_es',
                                'malha_pt',
                                'ozulo_map',
                                'meshcore_map',
                                'meshcore_hub'
                            )
                        ),

                    started_at TEXT NOT NULL,
                    finished_at TEXT,

                    success INTEGER
                        CHECK (
                            success IS NULL
                            OR success IN (0, 1)
                        ),

                    records_received INTEGER NOT NULL
                        DEFAULT 0
                        CHECK (records_received >= 0),

                    error_message TEXT,

                    CHECK (
                        (
                            finished_at IS NULL
                            AND success IS NULL
                        )
                        OR
                        (
                            finished_at IS NOT NULL
                            AND success IS NOT NULL
                        )
                    ),

                    CHECK (
                        success IS NOT 1
                        OR error_message IS NULL
                    )
                );

                CREATE INDEX IF NOT EXISTS
                    idx_source_runs_source_started
                ON source_runs (
                    source,
                    started_at
                );
                """
            )

            node_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(node_observations)"
                )
            }

            if "position_precision_bits" not in node_columns:
                connection.execute(
                    """
                    ALTER TABLE node_observations
                    ADD COLUMN position_precision_bits INTEGER
                        CHECK (
                            position_precision_bits IS NULL
                            OR position_precision_bits
                                BETWEEN 0 AND 32
                        )
                    """
                )

            if "is_observer" not in node_columns:
                connection.execute(
                    """
                    ALTER TABLE node_observations
                    ADD COLUMN is_observer INTEGER
                        CHECK (
                            is_observer IS NULL
                            OR is_observer IN (0, 1)
                        )
                    """
                )

            _migrate_source_constraints(
                connection
            )
            _migrate_meshcore_hub_source_constraints(
                connection
            )

            if current_version < SCHEMA_VERSION:
                _populate_observation_cursors(
                    connection
                )

            connection.execute(
                f"PRAGMA user_version = {SCHEMA_VERSION}"
            )

    def save(
        self,
        observations: Iterable[NodeObservation],
    ) -> int:
        """Guarda observaciones y devuelve cuántas insertó."""

        received = tuple(observations)

        if not received:
            return 0

        self.initialize()

        rows = [
            (
                observation.id,
                observation.network,
                observation.source,
                observation.source_id,
                observation.observed_at,
                observation.first_seen,
                observation.short_name,
                observation.long_name,
                observation.hardware,
                observation.role,
                observation.node_type,
                (
                    None
                    if observation.is_observer is None
                    else int(observation.is_observer)
                ),
                observation.latitude,
                observation.longitude,
                observation.altitude_m,
                observation.position_precision_bits,
                observation.position_updated_at,
                json.dumps(
                    observation.metrics,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                json.dumps(
                    observation.radio,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                observation.source,
                observation.id,
                observation.observed_at,
            )
            for observation in received
        ]

        cursor_rows = [
            (
                observation.source,
                observation.id,
                observation.observed_at,
            )
            for observation in received
        ]

        with _open_connection(
            self.database_path
        ) as connection:
            changes_before = connection.total_changes

            connection.executemany(
                """
                INSERT OR IGNORE INTO node_observations (
                    canonical_id,
                    network,
                    source,
                    source_id,
                    observed_at,
                    first_seen,
                    short_name,
                    long_name,
                    hardware,
                    role,
                    node_type,
                    is_observer,
                    latitude,
                    longitude,
                    altitude_m,
                    position_precision_bits,
                    position_updated_at,
                    metrics_json,
                    radio_json
                )
                SELECT
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM node_observation_cursors
                    WHERE source = ?
                      AND canonical_id = ?
                      AND last_observed_at >= ?
                )
                """,
                rows,
            )

            inserted = (
                connection.total_changes
                - changes_before
            )

            connection.executemany(
                """
                INSERT INTO node_observation_cursors (
                    source,
                    canonical_id,
                    last_observed_at
                )
                VALUES (?, ?, ?)
                ON CONFLICT (
                    source,
                    canonical_id
                )
                DO UPDATE SET
                    last_observed_at =
                        excluded.last_observed_at
                WHERE excluded.last_observed_at >
                    node_observation_cursors.last_observed_at
                """,
                cursor_rows,
            )

            return inserted


    def load(
        self,
        canonical_id: str,
    ) -> list[NodeObservation]:
        """Carga las observaciones de un nodo."""

        if not isinstance(canonical_id, str):
            raise TypeError(
                "canonical_id debe ser texto"
            )

        normalized_id = canonical_id.strip()

        if not normalized_id:
            raise ValueError(
                "canonical_id no puede estar vacío"
            )

        self.initialize()

        with _open_connection(
            self.database_path
        ) as connection:
            rows = connection.execute(
                """
                SELECT
                    source,
                    network,
                    source_id,
                    observed_at,
                    first_seen,
                    short_name,
                    long_name,
                    hardware,
                    role,
                    node_type,
                    is_observer,
                    latitude,
                    longitude,
                    altitude_m,
                    position_precision_bits,
                    position_updated_at,
                    metrics_json,
                    radio_json
                FROM node_observations
                WHERE canonical_id = ?
                ORDER BY observed_at ASC, id ASC
                """,
                (normalized_id,),
            ).fetchall()

        return [
            make_observation(
                source=row["source"],
                network=row["network"],
                source_id=row["source_id"],
                observed_at=row["observed_at"],
                first_seen=row["first_seen"],
                short_name=row["short_name"],
                long_name=row["long_name"],
                hardware=row["hardware"],
                role=row["role"],
                node_type=row["node_type"],
                is_observer=(
                    None
                    if row["is_observer"] is None
                    else bool(row["is_observer"])
                ),
                latitude=row["latitude"],
                longitude=row["longitude"],
                altitude_m=row["altitude_m"],
                position_precision_bits=(
                    row["position_precision_bits"]
                ),
                position_updated_at=(
                    row["position_updated_at"]
                ),
                metrics=json.loads(
                    row["metrics_json"]
                ),
                radio=json.loads(
                    row["radio_json"]
                ),
            )
            for row in rows
        ]

    def load_all(self) -> list[NodeObservation]:
        """Carga todas las observaciones almacenadas."""

        self.initialize()

        with _open_connection(
            self.database_path
        ) as connection:
            rows = connection.execute(
                """
                SELECT
                    source,
                    network,
                    source_id,
                    observed_at,
                    first_seen,
                    short_name,
                    long_name,
                    hardware,
                    role,
                    node_type,
                    is_observer,
                    latitude,
                    longitude,
                    altitude_m,
                    position_precision_bits,
                    position_updated_at,
                    metrics_json,
                    radio_json
                FROM node_observations
                ORDER BY
                    canonical_id ASC,
                    observed_at ASC,
                    id ASC
                """
            )

            return [
                make_observation(
                    source=row["source"],
                    network=row["network"],
                    source_id=row["source_id"],
                    observed_at=row["observed_at"],
                    first_seen=row["first_seen"],
                    short_name=row["short_name"],
                    long_name=row["long_name"],
                    hardware=row["hardware"],
                    role=row["role"],
                    node_type=row["node_type"],
                    is_observer=(
                        None
                        if row["is_observer"] is None
                        else bool(row["is_observer"])
                    ),
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                    altitude_m=row["altitude_m"],
                    position_precision_bits=(
                        row["position_precision_bits"]
                    ),
                    position_updated_at=(
                        row["position_updated_at"]
                    ),
                    metrics=json.loads(
                        row["metrics_json"]
                    ),
                    radio=json.loads(
                        row["radio_json"]
                    ),
                )
                for row in rows
            ]

    def save_edges(
        self,
        observations: Iterable[EdgeObservation],
    ) -> int:
        """Guarda conexiones y devuelve cuántas insertó."""

        received = tuple(observations)

        if not received:
            return 0

        for observation in received:
            if not isinstance(
                observation,
                EdgeObservation,
            ):
                raise TypeError(
                    "Todas las conexiones deben ser "
                    "EdgeObservation"
                )

        self.initialize()

        rows = [
            (
                observation.id,
                observation.network,
                observation.source,
                observation.from_source_id,
                observation.to_source_id,
                observation.edge_type,
                int(observation.directed),
                observation.observed_at,
                json.dumps(
                    observation.metrics,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                observation.source,
                observation.id,
                observation.observed_at,
            )
            for observation in received
        ]

        cursor_rows = [
            (
                observation.source,
                observation.id,
                observation.network,
                observation.from_source_id,
                observation.to_source_id,
                observation.observed_at,
            )
            for observation in received
        ]

        with _open_connection(
            self.database_path
        ) as connection:
            changes_before = connection.total_changes

            connection.executemany(
                """
                INSERT OR IGNORE INTO edge_observations (
                    canonical_id,
                    network,
                    source,
                    from_source_id,
                    to_source_id,
                    edge_type,
                    directed,
                    observed_at,
                    metrics_json
                )
                SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM edge_observation_cursors
                    WHERE source = ?
                      AND canonical_id = ?
                      AND last_observed_at >= ?
                )
                """,
                rows,
            )

            inserted = (
                connection.total_changes
                - changes_before
            )

            connection.executemany(
                """
                INSERT INTO edge_observation_cursors (
                    source,
                    canonical_id,
                    network,
                    from_source_id,
                    to_source_id,
                    last_observed_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (
                    source,
                    canonical_id
                )
                DO UPDATE SET
                    network = excluded.network,
                    from_source_id =
                        excluded.from_source_id,
                    to_source_id =
                        excluded.to_source_id,
                    last_observed_at =
                        excluded.last_observed_at
                WHERE excluded.last_observed_at >
                    edge_observation_cursors.last_observed_at
                """,
                cursor_rows,
            )

            return inserted


    def replace_edges(
        self,
        source: str,
        observations: Iterable[EdgeObservation],
    ) -> int:
        """Actualiza las conexiones recibidas sin retirar las ausentes."""

        normalized_source = _normalize_source(source)
        received = tuple(observations)

        for observation in received:
            if not isinstance(
                observation,
                EdgeObservation,
            ):
                raise TypeError(
                    "Todas las conexiones deben ser "
                    "EdgeObservation"
                )

            if observation.source != normalized_source:
                raise ValueError(
                    "La fuente de cada conexión debe "
                    "coincidir con source"
                )

        self.initialize()

        rows = [
            (
                observation.id,
                observation.network,
                observation.source,
                observation.from_source_id,
                observation.to_source_id,
                observation.edge_type,
                int(observation.directed),
                observation.observed_at,
                json.dumps(
                    observation.metrics,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            )
            for observation in received
        ]

        cursor_rows = [
            (
                observation.source,
                observation.id,
                observation.network,
                observation.from_source_id,
                observation.to_source_id,
                observation.observed_at,
            )
            for observation in received
        ]

        with _open_connection(
            self.database_path
        ) as connection:
            existing_keys = {
                (
                    row["canonical_id"],
                    row["observed_at"],
                )
                for row in connection.execute(
                    """
                    SELECT
                        canonical_id,
                        observed_at
                    FROM edge_observations
                    WHERE source = ?
                    """,
                    (normalized_source,),
                )
            }

            cursor_times = {
                row["canonical_id"]:
                    row["last_observed_at"]
                for row in connection.execute(
                    """
                    SELECT
                        canonical_id,
                        last_observed_at
                    FROM edge_observation_cursors
                    WHERE source = ?
                    """,
                    (normalized_source,),
                )
            }

            allowed_rows = [
                row
                for row in rows
                if (
                    (row[0], row[7]) in existing_keys
                    or row[7] > cursor_times.get(
                        row[0],
                        "",
                    )
                )
            ]

            refreshed_ids = sorted({
                row[0]
                for row in allowed_rows
            })

            connection.executemany(
                """
                DELETE FROM edge_observations
                WHERE source = ?
                  AND canonical_id = ?
                """,
                [
                    (
                        normalized_source,
                        canonical_id,
                    )
                    for canonical_id in refreshed_ids
                ],
            )

            changes_before = connection.total_changes

            connection.executemany(
                """
                INSERT INTO edge_observations (
                    canonical_id,
                    network,
                    source,
                    from_source_id,
                    to_source_id,
                    edge_type,
                    directed,
                    observed_at,
                    metrics_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                allowed_rows,
            )

            inserted = (
                connection.total_changes
                - changes_before
            )

            connection.executemany(
                """
                INSERT INTO edge_observation_cursors (
                    source,
                    canonical_id,
                    network,
                    from_source_id,
                    to_source_id,
                    last_observed_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (
                    source,
                    canonical_id
                )
                DO UPDATE SET
                    network = excluded.network,
                    from_source_id =
                        excluded.from_source_id,
                    to_source_id =
                        excluded.to_source_id,
                    last_observed_at =
                        excluded.last_observed_at
                WHERE excluded.last_observed_at >
                    edge_observation_cursors.last_observed_at
                """,
                cursor_rows,
            )

            return inserted


    def save_neighbors(
        self,
        observations: Iterable[NeighborObservation],
    ) -> int:
        """Garda observacións NeighborInfo e devolve cantas inseriu."""

        received = tuple(observations)

        if not received:
            return 0

        for observation in received:
            if not isinstance(
                observation,
                NeighborObservation,
            ):
                raise TypeError(
                    "Todas as observacións deben ser "
                    "NeighborObservation"
                )

        self.initialize()

        rows = [
            (
                observation.source,
                observation.from_source_id,
                observation.to_source_id,
                observation.observed_at,
                observation.snr_db,
            )
            for observation in received
        ]

        with _open_connection(
            self.database_path
        ) as connection:
            changes_before = connection.total_changes

            connection.executemany(
                """
                INSERT OR IGNORE INTO neighbor_observations (
                    source,
                    from_source_id,
                    to_source_id,
                    observed_at,
                    snr_db
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )

            return (
                connection.total_changes
                - changes_before
            )


    def load_all_neighbors(
        self,
    ) -> list[NeighborObservation]:
        """Carga todas as observacións NeighborInfo almacenadas."""

        self.initialize()

        with _open_connection(
            self.database_path
        ) as connection:
            rows = connection.execute(
                """
                SELECT
                    source,
                    from_source_id,
                    to_source_id,
                    observed_at,
                    snr_db
                FROM neighbor_observations
                ORDER BY
                    source ASC,
                    from_source_id ASC,
                    to_source_id ASC,
                    observed_at ASC,
                    id ASC
                """
            )

            return [
                make_neighbor_observation(
                    source=row["source"],
                    from_source_id=row[
                        "from_source_id"
                    ],
                    to_source_id=row[
                        "to_source_id"
                    ],
                    observed_at=row["observed_at"],
                    snr_db=row["snr_db"],
                )
                for row in rows
            ]


    def count_neighbors(self) -> int:
        """Devolve o número de observacións NeighborInfo."""

        self.initialize()

        with _open_connection(
            self.database_path
        ) as connection:
            return connection.execute(
                """
                SELECT COUNT(*)
                FROM neighbor_observations
                """
            ).fetchone()[0]


    def save_observer_receptions(
        self,
        receptions: Iterable[ObserverReception],
    ) -> int:
        """Garda recepcións de observers e devolve cantas inseriu."""

        received = tuple(receptions)

        if not received:
            return 0

        for reception in received:
            if not isinstance(
                reception,
                ObserverReception,
            ):
                raise TypeError(
                    "Todas as recepcións deben ser "
                    "ObserverReception"
                )

        self.initialize()

        rows = [
            (
                reception.source,
                reception.node_source_id,
                reception.observer_source_id,
                reception.packet_hash,
                reception.observed_at,
                reception.snr_db,
                reception.path_len,
            )
            for reception in received
        ]

        with _open_connection(
            self.database_path
        ) as connection:
            changes_before = connection.total_changes

            connection.executemany(
                """
                INSERT OR IGNORE INTO observer_receptions (
                    source,
                    node_source_id,
                    observer_source_id,
                    packet_hash,
                    observed_at,
                    snr_db,
                    path_len
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

            return (
                connection.total_changes
                - changes_before
            )


    def load_all_observer_receptions(
        self,
    ) -> list[ObserverReception]:
        """Carga todas as recepcións dos observers almacenadas."""

        self.initialize()

        with _open_connection(
            self.database_path
        ) as connection:
            rows = connection.execute(
                """
                SELECT
                    source,
                    node_source_id,
                    observer_source_id,
                    packet_hash,
                    observed_at,
                    snr_db,
                    path_len
                FROM observer_receptions
                ORDER BY
                    node_source_id ASC,
                    observer_source_id ASC,
                    observed_at ASC,
                    packet_hash ASC,
                    id ASC
                """
            )

            return [
                make_observer_reception(
                    source=row["source"],
                    node_source_id=row[
                        "node_source_id"
                    ],
                    observer_source_id=row[
                        "observer_source_id"
                    ],
                    packet_hash=row["packet_hash"],
                    observed_at=row["observed_at"],
                    snr_db=row["snr_db"],
                    path_len=row["path_len"],
                )
                for row in rows
            ]


    def count_observer_receptions(self) -> int:
        """Devolve o número de recepcións de observers almacenadas."""

        self.initialize()

        with _open_connection(
            self.database_path
        ) as connection:
            return connection.execute(
                """
                SELECT COUNT(*)
                FROM observer_receptions
                """
            ).fetchone()[0]


    def load_all_edges(
        self,
    ) -> list[EdgeObservation]:
        """Carga todas las conexiones almacenadas."""

        self.initialize()

        with _open_connection(
            self.database_path
        ) as connection:
            rows = connection.execute(
                """
                SELECT
                    source,
                    network,
                    from_source_id,
                    to_source_id,
                    edge_type,
                    directed,
                    observed_at,
                    metrics_json
                FROM edge_observations
                ORDER BY
                    canonical_id ASC,
                    observed_at ASC,
                    id ASC
                """
            )

            return [
                make_edge_observation(
                    source=row["source"],
                    network=row["network"],
                    from_source_id=row[
                        "from_source_id"
                    ],
                    to_source_id=row[
                        "to_source_id"
                    ],
                    edge_type=row["edge_type"],
                    directed=bool(row["directed"]),
                    observed_at=row["observed_at"],
                    metrics=json.loads(
                        row["metrics_json"]
                    ),
                )
                for row in rows
            ]

    def purge_node(
        self,
        canonical_id: str,
    ) -> NodePurgeResult:
        """Elimina un nodo y todas sus conexiones incidentes."""

        if not isinstance(canonical_id, str):
            raise TypeError(
                "canonical_id debe ser texto"
            )

        candidate = canonical_id.strip()

        if ":" not in candidate:
            raise ValueError(
                "canonical_id debe incluir "
                "el prefijo de red"
            )

        network, source_id = candidate.split(":", 1)

        normalized_canonical_id = canonical_node_id(
            network,
            source_id,
        )
        normalized_network, normalized_source_id = (
            normalized_canonical_id.split(":", 1)
        )

        self.initialize()

        with _open_connection(
            self.database_path
        ) as connection:
            connection.execute(
                """
                DELETE FROM edge_observation_cursors
                WHERE network = ?
                  AND (
                      from_source_id = ?
                      OR to_source_id = ?
                  )
                """,
                (
                    normalized_network,
                    normalized_source_id,
                    normalized_source_id,
                ),
            )

            connection.execute(
                """
                DELETE FROM node_observation_cursors
                WHERE canonical_id = ?
                """,
                (normalized_canonical_id,),
            )

            if normalized_network == "meshcore":
                connection.execute(
                    """
                    DELETE FROM observer_receptions
                    WHERE node_source_id = ?
                       OR observer_source_id = ?
                    """,
                    (
                        normalized_source_id,
                        normalized_source_id,
                    ),
                )

            changes_before_edges = (
                connection.total_changes
            )

            connection.execute(
                """
                DELETE FROM edge_observations
                WHERE network = ?
                  AND (
                      from_source_id = ?
                      OR to_source_id = ?
                  )
                """,
                (
                    normalized_network,
                    normalized_source_id,
                    normalized_source_id,
                ),
            )

            edges_deleted = (
                connection.total_changes
                - changes_before_edges
            )

            changes_before_nodes = (
                connection.total_changes
            )

            connection.execute(
                """
                DELETE FROM node_observations
                WHERE canonical_id = ?
                """,
                (normalized_canonical_id,),
            )

            nodes_deleted = (
                connection.total_changes
                - changes_before_nodes
            )

        return NodePurgeResult(
            node_observations_deleted=nodes_deleted,
            edge_observations_deleted=edges_deleted,
        )


    def count_edges(self) -> int:
        """Devuelve el número de conexiones almacenadas."""

        self.initialize()

        with _open_connection(
            self.database_path
        ) as connection:
            return connection.execute(
                """
                SELECT COUNT(*)
                FROM edge_observations
                """
            ).fetchone()[0]

    def begin_source_run(
        self,
        source: str,
        started_at: Any,
    ) -> int:
        """Registra el inicio de una ejecución de fuente."""

        normalized_source = _normalize_source(source)
        normalized_started_at = normalize_timestamp(
            started_at
        )

        self.initialize()

        with _open_connection(
            self.database_path
        ) as connection:
            cursor = connection.execute(
                """
                INSERT INTO source_runs (
                    source,
                    started_at
                )
                VALUES (?, ?)
                """,
                (
                    normalized_source,
                    normalized_started_at,
                ),
            )

            run_id = cursor.lastrowid

        if run_id is None:
            raise RuntimeError(
                "SQLite no devolvió el identificador "
                "de la ejecución"
            )

        return int(run_id)

    def finish_source_run(
        self,
        run_id: int,
        *,
        finished_at: Any,
        success: bool,
        records_received: int = 0,
        error_message: str | None = None,
    ) -> None:
        """Finaliza una ejecución previamente iniciada."""

        if isinstance(run_id, bool) or not isinstance(
            run_id,
            int,
        ):
            raise TypeError(
                "run_id debe ser un entero"
            )

        if run_id < 1:
            raise ValueError(
                "run_id debe ser mayor que cero"
            )

        if not isinstance(success, bool):
            raise TypeError(
                "success debe ser booleano"
            )

        if (
            isinstance(records_received, bool)
            or not isinstance(records_received, int)
        ):
            raise TypeError(
                "records_received debe ser un entero"
            )

        if records_received < 0:
            raise ValueError(
                "records_received no puede ser negativo"
            )

        normalized_finished_at = normalize_timestamp(
            finished_at
        )

        normalized_error: str | None

        if error_message is None:
            normalized_error = None
        elif not isinstance(error_message, str):
            raise TypeError(
                "error_message debe ser texto o null"
            )
        else:
            normalized_error = error_message.strip()

            if not normalized_error:
                normalized_error = None

            if (
                normalized_error is not None
                and len(normalized_error) > 1000
            ):
                raise ValueError(
                    "error_message supera 1000 caracteres"
                )

        if success and normalized_error is not None:
            raise ValueError(
                "Una ejecución correcta no puede "
                "incluir error_message"
            )

        if not success and normalized_error is None:
            raise ValueError(
                "Una ejecución fallida debe incluir "
                "error_message"
            )

        self.initialize()

        with _open_connection(
            self.database_path
        ) as connection:
            row = connection.execute(
                """
                SELECT
                    started_at,
                    finished_at
                FROM source_runs
                WHERE id = ?
                """,
                (run_id,),
            ).fetchone()

            if row is None:
                raise ValueError(
                    f"No existe la ejecución {run_id}"
                )

            if row["finished_at"] is not None:
                raise ValueError(
                    f"La ejecución {run_id} ya está finalizada"
                )

            if normalized_finished_at < row["started_at"]:
                raise ValueError(
                    "finished_at no puede ser anterior "
                    "a started_at"
                )

            cursor = connection.execute(
                """
                UPDATE source_runs
                SET
                    finished_at = ?,
                    success = ?,
                    records_received = ?,
                    error_message = ?
                WHERE id = ?
                  AND finished_at IS NULL
                """,
                (
                    normalized_finished_at,
                    int(success),
                    records_received,
                    normalized_error,
                    run_id,
                ),
            )

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "No se pudo finalizar la ejecución "
                    f"{run_id}"
                )

    def source_statistics(
        self,
    ) -> dict[str, dict[str, Any]]:
        """Resume el último éxito y error de cada fuente."""

        self.initialize()

        statistics: dict[str, dict[str, Any]] = {
            source: {
                "last_success": None,
                "last_error_at": None,
                "last_error": None,
                "records_received": 0,
            }
            for source in SOURCE_ORDER
        }

        with _open_connection(
            self.database_path
        ) as connection:
            for source in SOURCE_ORDER:
                successful = connection.execute(
                    """
                    SELECT
                        finished_at,
                        records_received
                    FROM source_runs
                    WHERE source = ?
                      AND success = 1
                    ORDER BY
                        finished_at DESC,
                        id DESC
                    LIMIT 1
                    """,
                    (source,),
                ).fetchone()

                failed = connection.execute(
                    """
                    SELECT
                        finished_at,
                        error_message
                    FROM source_runs
                    WHERE source = ?
                      AND success = 0
                    ORDER BY
                        finished_at DESC,
                        id DESC
                    LIMIT 1
                    """,
                    (source,),
                ).fetchone()

                if successful is not None:
                    statistics[source][
                        "last_success"
                    ] = successful["finished_at"]
                    statistics[source][
                        "records_received"
                    ] = successful[
                        "records_received"
                    ]

                if failed is not None:
                    statistics[source][
                        "last_error_at"
                    ] = failed["finished_at"]
                    statistics[source][
                        "last_error"
                    ] = failed["error_message"]

        return statistics

    def prune(
        self,
        before: Any,
    ) -> dict[str, int]:
        """Retira todas las observaciones completas caducadas."""

        normalized_before = normalize_timestamp(before)

        self.initialize()

        with _open_connection(
            self.database_path
        ) as connection:
            deleted_nodes = connection.execute(
                """
                DELETE FROM node_observations
                WHERE observed_at < ?
                """,
                (normalized_before,),
            ).rowcount

            deleted_edges = connection.execute(
                """
                DELETE FROM edge_observations
                WHERE observed_at < ?
                """,
                (normalized_before,),
            ).rowcount

            deleted_observer_receptions = connection.execute(
                """
                DELETE FROM observer_receptions
                WHERE observed_at < ?
                """,
                (normalized_before,),
            ).rowcount

            deleted_runs = connection.execute(
                """
                DELETE FROM source_runs
                WHERE COALESCE(
                    finished_at,
                    started_at
                ) < ?
                  AND id NOT IN (
                      SELECT id
                      FROM (
                          SELECT
                              id,
                              ROW_NUMBER() OVER (
                                  PARTITION BY
                                      source,
                                      success
                                  ORDER BY
                                      finished_at DESC,
                                      id DESC
                              ) AS position
                          FROM source_runs
                          WHERE success IN (0, 1)
                      )
                      WHERE position = 1
                  )
                """,
                (normalized_before,),
            ).rowcount

        return {
            "node_observations": deleted_nodes,
            "edge_observations": deleted_edges,
            "observer_receptions": (
                deleted_observer_receptions
            ),
            "source_runs": deleted_runs,
        }


    def count(self) -> int:
        """Devuelve el número de observaciones almacenadas."""

        self.initialize()

        with _open_connection(
            self.database_path
        ) as connection:
            return connection.execute(
                """
                SELECT COUNT(*)
                FROM node_observations
                """
            ).fetchone()[0]

    def schema_version(self) -> int:
        """Devuelve la versión del esquema SQLite."""

        self.initialize()

        with _open_connection(
            self.database_path
        ) as connection:
            return connection.execute(
                "PRAGMA user_version"
            ).fetchone()[0]

    def quick_check(self) -> str:
        """Ejecuta PRAGMA quick_check."""

        self.initialize()

        with _open_connection(
            self.database_path
        ) as connection:
            return connection.execute(
                "PRAGMA quick_check"
            ).fetchone()[0]

    def journal_mode(self) -> str:
        """Devuelve el modo actual del diario SQLite."""

        self.initialize()

        with _open_connection(
            self.database_path
        ) as connection:
            return connection.execute(
                "PRAGMA journal_mode"
            ).fetchone()[0]
