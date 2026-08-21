"""Persistencia local das observacións para experimentos Meshtastic."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable


EXPERIMENT_CHANNELS = frozenset({
    "LongFast",
    "NarrowFast",
})


@dataclass(frozen=True, slots=True)
class ExperimentObservation:
    """Observación normalizada dun paquete útil para análise."""

    event_id: str
    packet_id: int
    from_id: str
    channel: str
    portnum: int
    imported_at_us: int

    gateway_count: int
    stage_count: int

    snr_values: tuple[float, ...]
    rssi_values: tuple[float, ...]

    route_discovery: bool

    telemetry_time: int | None
    channel_utilization: float | None
    air_util_tx: float | None
    battery_level: float | None
    voltage: float | None
    uptime_seconds: float | None


def _valid_radio_value(
    value: Any,
) -> float | None:
    """Normaliza unha medida RF.

    O par RSSI/SNR 0/0 observado nalgunhas fontes representa ausencia
    de medida, pero a decisión de descartar o par faise posteriormente.
    Aquí só validamos que sexa numérico.
    """

    if isinstance(value, bool):
        return None

    if not isinstance(value, (int, float)):
        return None

    return float(value)


def _radio_values(
    event: dict[str, Any],
) -> tuple[
    tuple[float, ...],
    tuple[float, ...],
]:
    snrs: list[float] = []
    rssis: list[float] = []

    observed = event.get("observed")

    if not isinstance(observed, dict):
        return (), ()

    stages = observed.get("stages")

    if not isinstance(stages, list):
        return (), ()

    for stage in stages:
        if not isinstance(stage, dict):
            continue

        gateways = stage.get("gateways")

        if not isinstance(gateways, list):
            continue

        for gateway in gateways:
            if not isinstance(gateway, dict):
                continue

            snr = _valid_radio_value(
                gateway.get("snr_db")
            )

            rssi = _valid_radio_value(
                gateway.get("rssi_dbm")
            )

            # O caso 0/0 que vimos en NarrowFast non debe entrar
            # nas estatísticas como unha medida RF real.
            if (
                snr == 0.0
                and rssi == 0.0
            ):
                continue

            if snr is not None:
                snrs.append(snr)

            if rssi is not None:
                rssis.append(rssi)

    return (
        tuple(snrs),
        tuple(rssis),
    )


def _device_metric(
    event: dict[str, Any],
    name: str,
) -> float | None:
    telemetry = event.get("telemetry")

    if not isinstance(telemetry, dict):
        return None

    device = telemetry.get(
        "device_metrics"
    )

    if not isinstance(device, dict):
        return None

    value = device.get(name)

    if isinstance(value, bool):
        return None

    if not isinstance(value, (int, float)):
        return None

    return float(value)


def observation_from_event(
    event: dict[str, Any],
) -> ExperimentObservation | None:
    """Converte un evento live nunha observación experimental."""

    if not isinstance(event, dict):
        raise TypeError(
            "event debe ser un obxecto"
        )

    if event.get("network") != "meshtastic":
        return None

    channel = event.get("channel")

    if channel not in EXPERIMENT_CHANNELS:
        return None

    event_id = event.get("id")
    packet_id = event.get("packet_id")
    from_id = event.get("from_id")
    portnum = event.get("portnum")
    imported_at_us = event.get(
        "imported_at_us"
    )

    if not isinstance(event_id, str):
        return None

    if (
        isinstance(packet_id, bool)
        or not isinstance(packet_id, int)
    ):
        return None

    if not isinstance(from_id, str):
        return None

    if (
        isinstance(portnum, bool)
        or not isinstance(portnum, int)
    ):
        return None

    if (
        isinstance(imported_at_us, bool)
        or not isinstance(
            imported_at_us,
            int,
        )
    ):
        return None

    observed = event.get("observed")

    if isinstance(observed, dict):
        gateway_count = observed.get(
            "gateway_count",
            0,
        )
        stage_count = observed.get(
            "stage_count",
            0,
        )
    else:
        gateway_count = 0
        stage_count = 0

    if (
        isinstance(gateway_count, bool)
        or not isinstance(
            gateway_count,
            int,
        )
    ):
        gateway_count = 0

    if (
        isinstance(stage_count, bool)
        or not isinstance(
            stage_count,
            int,
        )
    ):
        stage_count = 0

    telemetry = event.get("telemetry")

    telemetry_time: int | None = None

    if isinstance(telemetry, dict):
        candidate_time = telemetry.get(
            "time"
        )

        if (
            not isinstance(
                candidate_time,
                bool,
            )
            and isinstance(
                candidate_time,
                int,
            )
        ):
            telemetry_time = (
                candidate_time
            )

    snrs, rssis = _radio_values(event)

    return ExperimentObservation(
        event_id=event_id,
        packet_id=packet_id,
        from_id=from_id,
        channel=channel,
        portnum=portnum,
        imported_at_us=imported_at_us,
        gateway_count=gateway_count,
        stage_count=stage_count,
        snr_values=snrs,
        rssi_values=rssis,
        route_discovery=(
            portnum == 70
        ),
        telemetry_time=telemetry_time,
        channel_utilization=(
            _device_metric(
                event,
                "channel_utilization",
            )
        ),
        air_util_tx=(
            _device_metric(
                event,
                "air_util_tx",
            )
        ),
        battery_level=(
            _device_metric(
                event,
                "battery_level",
            )
        ),
        voltage=(
            _device_metric(
                event,
                "voltage",
            )
        ),
        uptime_seconds=(
            _device_metric(
                event,
                "uptime_seconds",
            )
        ),
    )


def connect_experiment_store(
    path: str | Path,
) -> sqlite3.Connection:
    database = Path(path)

    database.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        database
    )

    connection.row_factory = (
        sqlite3.Row
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS
        experiment_observations (
            event_id TEXT PRIMARY KEY,
            packet_id INTEGER NOT NULL,
            from_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            portnum INTEGER NOT NULL,
            imported_at_us INTEGER NOT NULL,

            gateway_count INTEGER NOT NULL,
            stage_count INTEGER NOT NULL,

            snr_values_json TEXT NOT NULL,
            rssi_values_json TEXT NOT NULL,

            route_discovery INTEGER NOT NULL,

            telemetry_time INTEGER,
            channel_utilization REAL,
            air_util_tx REAL,
            battery_level REAL,
            voltage REAL,
            uptime_seconds REAL,

            CHECK (
                channel IN (
                    'LongFast',
                    'NarrowFast'
                )
            ),
            CHECK (
                route_discovery IN (0, 1)
            )
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_experiment_channel_time
        ON experiment_observations (
            channel,
            imported_at_us
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_experiment_from_time
        ON experiment_observations (
            from_id,
            imported_at_us
        )
        """
    )

    connection.commit()

    return connection


def store_observations(
    connection: sqlite3.Connection,
    observations: Iterable[
        ExperimentObservation
    ],
) -> int:
    """Garda observacións de maneira idempotente."""

    inserted = 0

    for observation in observations:
        existed = connection.execute(
            """
            SELECT 1
            FROM experiment_observations
            WHERE event_id = ?
            """,
            (
                observation.event_id,
            ),
        ).fetchone() is not None

        connection.execute(
            """
            INSERT INTO
            experiment_observations (
                event_id,
                packet_id,
                from_id,
                channel,
                portnum,
                imported_at_us,
                gateway_count,
                stage_count,
                snr_values_json,
                rssi_values_json,
                route_discovery,
                telemetry_time,
                channel_utilization,
                air_util_tx,
                battery_level,
                voltage,
                uptime_seconds
            )
            VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(event_id) DO UPDATE SET
                packet_id = excluded.packet_id,
                from_id = excluded.from_id,
                channel = excluded.channel,
                portnum = excluded.portnum,
                imported_at_us = excluded.imported_at_us,
                gateway_count = excluded.gateway_count,
                stage_count = excluded.stage_count,
                snr_values_json = excluded.snr_values_json,
                rssi_values_json = excluded.rssi_values_json,
                route_discovery = excluded.route_discovery,
                telemetry_time = excluded.telemetry_time,
                channel_utilization = excluded.channel_utilization,
                air_util_tx = excluded.air_util_tx,
                battery_level = excluded.battery_level,
                voltage = excluded.voltage,
                uptime_seconds = excluded.uptime_seconds
            """,
            (
                observation.event_id,
                observation.packet_id,
                observation.from_id,
                observation.channel,
                observation.portnum,
                observation.imported_at_us,
                observation.gateway_count,
                observation.stage_count,
                json.dumps(
                    observation.snr_values
                ),
                json.dumps(
                    observation.rssi_values
                ),
                int(
                    observation.route_discovery
                ),
                observation.telemetry_time,
                observation.channel_utilization,
                observation.air_util_tx,
                observation.battery_level,
                observation.voltage,
                observation.uptime_seconds,
            ),
        )

        if not existed:
            inserted += 1

    connection.commit()

    return inserted


def store_live_document(
    connection: sqlite3.Connection,
    document: dict[str, Any],
) -> int:
    """Importa os eventos útiles dun live.json."""

    if not isinstance(document, dict):
        raise TypeError(
            "document debe ser un obxecto"
        )

    events = document.get("events")

    if not isinstance(events, list):
        raise ValueError(
            "document.events debe ser unha lista"
        )

    observations = []

    for event in events:
        if not isinstance(event, dict):
            continue

        observation = (
            observation_from_event(event)
        )

        if observation is not None:
            observations.append(
                observation
            )

    return store_observations(
        connection,
        observations,
    )
