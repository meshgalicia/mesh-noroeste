"""Interpretación estruturada do payload Telemetry de Meshtastic."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


TELEMETRY_PORTNUM = 67


_DEVICE_FIELDS = frozenset({
    "battery_level",
    "voltage",
    "channel_utilization",
    "air_util_tx",
    "uptime_seconds",
})

_ENVIRONMENT_FIELDS = frozenset({
    "temperature",
    "relative_humidity",
    "barometric_pressure",
    "gas_resistance",
    "iaq",
    "lux",
    "voltage",
    "current",
})

_POWER_FIELDS = frozenset({
    "ch1_voltage",
    "ch1_current",
    "ch2_voltage",
    "ch2_current",
    "ch3_voltage",
    "ch3_current",
})

_SECTION_FIELDS = {
    "device_metrics": _DEVICE_FIELDS,
    "environment_metrics": _ENVIRONMENT_FIELDS,
    "power_metrics": _POWER_FIELDS,
}

_SECTION_RE = re.compile(
    r"(?ms)^"
    r"(?P<section>"
    r"device_metrics|environment_metrics|power_metrics"
    r")\s*\{\s*"
    r"(?P<body>.*?)"
    r"^\s*\}"
)

_FIELD_RE = re.compile(
    r"^\s*"
    r"(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)"
    r":\s*"
    r"(?P<value>"
    r"[-+]?"
    r"(?:\d+(?:\.\d*)?|\.\d+)"
    r"(?:[eE][-+]?\d+)?"
    r")"
    r"\s*$"
)

_TIME_RE = re.compile(
    r"(?m)^\s*time:\s*(?P<value>\d+)\s*$"
)


@dataclass(frozen=True, slots=True)
class LiveTelemetry:
    """Telemetry Meshtastic xa extraída do payload protobuf textual."""

    time: int | None
    device_metrics: dict[str, int | float] | None
    environment_metrics: dict[str, int | float] | None
    power_metrics: dict[str, int | float] | None

    @property
    def has_metrics(self) -> bool:
        return any((
            self.device_metrics,
            self.environment_metrics,
            self.power_metrics,
        ))


def _numeric_value(value: str) -> int | float:
    """Conserva enteiros cando o texto non precisa decimal."""

    if not isinstance(value, str):
        raise TypeError("value debe ser texto")

    normalized = value.strip()

    if not normalized:
        raise ValueError("value non pode estar baleiro")

    if not any(
        marker in normalized.lower()
        for marker in (".", "e")
    ):
        return int(normalized)

    return float(normalized)


def _parse_section(
    body: str,
    *,
    allowed_fields: frozenset[str],
) -> dict[str, int | float]:
    result: dict[str, int | float] = {}

    for raw_line in body.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        match = _FIELD_RE.fullmatch(line)

        if match is None:
            continue

        name = match.group("name")

        if name not in allowed_fields:
            continue

        result[name] = _numeric_value(
            match.group("value")
        )

    return result


def parse_live_telemetry_payload(
    payload: str,
) -> LiveTelemetry:
    """Extrae só as métricas Telemetry coñecidas e numéricas.

    Non devolve nin conserva o payload bruto. Campos alleos ou aínda
    non soportados ignóranse deliberadamente.
    """

    if not isinstance(payload, str):
        raise TypeError("payload debe ser texto")

    time_match = _TIME_RE.search(payload)

    telemetry_time = (
        int(time_match.group("value"))
        if time_match is not None
        else None
    )

    sections: dict[
        str,
        dict[str, int | float] | None,
    ] = {
        "device_metrics": None,
        "environment_metrics": None,
        "power_metrics": None,
    }

    for match in _SECTION_RE.finditer(payload):
        section = match.group("section")

        parsed = _parse_section(
            match.group("body"),
            allowed_fields=_SECTION_FIELDS[section],
        )

        if parsed:
            sections[section] = parsed

    return LiveTelemetry(
        time=telemetry_time,
        device_metrics=sections["device_metrics"],
        environment_metrics=sections[
            "environment_metrics"
        ],
        power_metrics=sections["power_metrics"],
    )
