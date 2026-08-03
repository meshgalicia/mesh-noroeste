"""Normalización de identificadores, fechas y coordenadas."""

from __future__ import annotations

from datetime import datetime, timezone
import math
import re
from typing import Any


_MESHTASTIC_ID = re.compile(
    r"^!?([0-9a-fA-F]{8})$"
)

_HEXADECIMAL = re.compile(
    r"^[0-9a-fA-F]+$"
)

_NUMERIC_TEXT = re.compile(
    r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$"
)


def normalize_meshtastic_id(value: str | int) -> str:
    """Devuelve un identificador Meshtastic como !xxxxxxxx."""

    if isinstance(value, bool):
        raise ValueError(
            "Un booleano no es un identificador Meshtastic válido"
        )

    if isinstance(value, int):
        if not 0 <= value <= 0xFFFFFFFF:
            raise ValueError(
                "El identificador numérico Meshtastic "
                "debe estar entre 0 y 4294967295"
            )

        return f"!{value:08x}"

    if not isinstance(value, str):
        raise TypeError(
            "El identificador Meshtastic debe ser texto o entero"
        )

    candidate = value.strip()
    match = _MESHTASTIC_ID.fullmatch(candidate)

    if match is None:
        raise ValueError(
            "El identificador Meshtastic debe contener "
            "ocho caracteres hexadecimales"
        )

    return f"!{match.group(1).lower()}"


def normalize_meshcore_id(value: str) -> str:
    """Normaliza un identificador público estable de MeshCore."""

    if not isinstance(value, str):
        raise TypeError(
            "El identificador MeshCore debe ser texto"
        )

    candidate = value.strip()

    if not candidate:
        raise ValueError(
            "El identificador MeshCore no puede estar vacío"
        )

    if len(candidate) > 256:
        raise ValueError(
            "El identificador MeshCore supera 256 caracteres"
        )

    if any(character.isspace() for character in candidate):
        raise ValueError(
            "El identificador MeshCore no puede contener espacios"
        )

    if _HEXADECIMAL.fullmatch(candidate):
        return candidate.lower()

    return candidate


def canonical_node_id(
    network: str,
    source_id: str | int,
) -> str:
    """Construye el identificador canónico con prefijo de red."""

    if not isinstance(network, str):
        raise TypeError("La red debe ser texto")

    normalized_network = network.strip().lower()

    if normalized_network == "meshtastic":
        return (
            "meshtastic:"
            + normalize_meshtastic_id(source_id)
        )

    if normalized_network == "meshcore":
        if not isinstance(source_id, str):
            raise TypeError(
                "El identificador MeshCore debe ser texto"
            )

        return (
            "meshcore:"
            + normalize_meshcore_id(source_id)
        )

    raise ValueError(
        f"Red no admitida: {network!r}"
    )


def _datetime_from_epoch(value: float) -> datetime:
    if not math.isfinite(value):
        raise ValueError(
            "El timestamp Unix debe ser un número finito"
        )

    absolute_value = abs(value)

    if absolute_value >= 100_000_000_000_000:
        seconds = value / 1_000_000
    elif absolute_value >= 100_000_000_000:
        seconds = value / 1_000
    else:
        seconds = value

    try:
        return datetime.fromtimestamp(
            seconds,
            tz=timezone.utc,
        )
    except (OverflowError, OSError, ValueError) as exc:
        raise ValueError(
            f"Timestamp Unix fuera de rango: {value!r}"
        ) from exc


def normalize_timestamp(
    value: datetime | str | int | float,
) -> str:
    """Devuelve una fecha UTC ISO 8601 con precisión de segundos."""

    parsed: datetime

    if isinstance(value, bool):
        raise ValueError(
            "Un booleano no es un timestamp válido"
        )

    if isinstance(value, datetime):
        parsed = value

    elif isinstance(value, (int, float)):
        parsed = _datetime_from_epoch(float(value))

    elif isinstance(value, str):
        candidate = value.strip()

        if not candidate:
            raise ValueError(
                "El timestamp no puede estar vacío"
            )

        if _NUMERIC_TEXT.fullmatch(candidate):
            parsed = _datetime_from_epoch(float(candidate))
        else:
            iso_value = candidate

            if iso_value.endswith(("Z", "z")):
                iso_value = iso_value[:-1] + "+00:00"

            try:
                parsed = datetime.fromisoformat(iso_value)
            except ValueError as exc:
                raise ValueError(
                    f"Fecha ISO 8601 inválida: {value!r}"
                ) from exc

    else:
        raise TypeError(
            "El timestamp debe ser datetime, texto o número"
        )

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(
            "El timestamp debe incluir una zona horaria"
        )

    utc_value = parsed.astimezone(timezone.utc)
    utc_value = utc_value.replace(microsecond=0)

    return (
        utc_value.isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _finite_number(
    value: Any,
    field_name: str,
) -> float:
    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} no puede ser un booleano"
        )

    if isinstance(value, str):
        candidate = value.strip()

        if not candidate:
            raise ValueError(
                f"{field_name} no puede estar vacío"
            )

        try:
            number = float(candidate)
        except ValueError as exc:
            raise ValueError(
                f"{field_name} debe ser numérico"
            ) from exc

    elif isinstance(value, (int, float)):
        number = float(value)

    else:
        raise TypeError(
            f"{field_name} debe ser texto o número"
        )

    if not math.isfinite(number):
        raise ValueError(
            f"{field_name} debe ser un número finito"
        )

    return number


def normalize_coordinates(
    latitude: Any,
    longitude: Any,
) -> tuple[float | None, float | None]:
    """Valida y normaliza una pareja de coordenadas WGS84."""

    if latitude is None and longitude is None:
        return None, None

    if latitude is None or longitude is None:
        raise ValueError(
            "La latitud y la longitud deben aparecer juntas"
        )

    normalized_latitude = _finite_number(
        latitude,
        "latitude",
    )
    normalized_longitude = _finite_number(
        longitude,
        "longitude",
    )

    if not -90 <= normalized_latitude <= 90:
        raise ValueError(
            "latitude debe estar entre -90 y 90"
        )

    if not -180 <= normalized_longitude <= 180:
        raise ValueError(
            "longitude debe estar entre -180 y 180"
        )

    if (
        normalized_latitude == 0
        and normalized_longitude == 0
    ):
        raise ValueError(
            "La posición 0, 0 no se considera válida"
        )

    return normalized_latitude, normalized_longitude
