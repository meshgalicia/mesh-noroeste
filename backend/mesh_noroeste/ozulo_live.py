"""Adaptador clean-room para o tráfico Meshtastic de O Zulo."""

from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

from mesh_noroeste.domain import (
    MeshtasticLivePacket,
    MeshtasticLiveReception,
    normalize_meshtastic_id,
)


class OzuloLiveError(ValueError):
    """Indica que unha resposta live de O Zulo non é válida."""


def _required(
    record: Mapping[Any, Any],
    key: str,
    index: int,
    *,
    kind: str,
) -> Any:
    if key not in record:
        raise OzuloLiveError(
            f"{kind} {index}: falta o campo {key!r}"
        )

    return record[key]


def _integer(
    value: Any,
    field: str,
    index: int,
    *,
    kind: str,
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OzuloLiveError(
            f"{kind} {index}: {field} debe ser un enteiro"
        )

    if value < minimum:
        raise OzuloLiveError(
            f"{kind} {index}: {field} está fóra de rango"
        )

    if maximum is not None and value > maximum:
        raise OzuloLiveError(
            f"{kind} {index}: {field} está fóra de rango"
        )

    return value


def _optional_integer(
    value: Any,
    field: str,
    index: int,
    *,
    kind: str,
    minimum: int = 0,
    maximum: int | None = None,
) -> int | None:
    if value is None:
        return None

    return _integer(
        value,
        field,
        index,
        kind=kind,
        minimum=minimum,
        maximum=maximum,
    )


def _optional_number(
    value: Any,
    field: str,
    index: int,
    *,
    kind: str,
) -> float | None:
    if value is None:
        return None

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
    ):
        raise OzuloLiveError(
            f"{kind} {index}: {field} debe ser numérico ou null"
        )

    normalized = float(value)

    if not math.isfinite(normalized):
        raise OzuloLiveError(
            f"{kind} {index}: {field} debe ser finito"
        )

    return normalized


def _optional_text(
    value: Any,
    field: str,
    index: int,
    *,
    kind: str,
) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise OzuloLiveError(
            f"{kind} {index}: {field} debe ser texto ou null"
        )

    normalized = value.strip()

    return normalized or None


def _text(
    value: Any,
    field: str,
    index: int,
    *,
    kind: str,
) -> str:
    if not isinstance(value, str):
        raise OzuloLiveError(
            f"{kind} {index}: {field} debe ser texto"
        )

    return value


def parse_ozulo_live_packets(
    document: Any,
    *,
    source: str = "ozulo_map",
) -> tuple[MeshtasticLivePacket, ...]:
    """Normaliza ``/api/packets`` de Meshview O Zulo."""

    if not isinstance(source, str):
        raise TypeError("source debe ser texto")

    normalized_source = source.strip().lower()

    if normalized_source != "ozulo_map":
        raise ValueError(
            "O tráfico live de O Zulo debe usar source='ozulo_map'"
        )

    if not isinstance(document, Mapping):
        raise OzuloLiveError(
            "A raíz de /api/packets debe ser un obxecto"
        )

    records = document.get("packets")

    if not isinstance(records, list):
        raise OzuloLiveError(
            "/api/packets non contén unha lista packets"
        )

    result: list[MeshtasticLivePacket] = []

    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise OzuloLiveError(
                f"Paquete {index}: debe ser un obxecto"
            )

        packet_id = _integer(
            _required(
                record,
                "id",
                index,
                kind="Paquete",
            ),
            "id",
            index,
            kind="Paquete",
            maximum=0xFFFFFFFF,
        )

        from_node_id = _integer(
            _required(
                record,
                "from_node_id",
                index,
                kind="Paquete",
            ),
            "from_node_id",
            index,
            kind="Paquete",
            maximum=0xFFFFFFFF,
        )

        to_node_id = _integer(
            _required(
                record,
                "to_node_id",
                index,
                kind="Paquete",
            ),
            "to_node_id",
            index,
            kind="Paquete",
            maximum=0xFFFFFFFF,
        )

        portnum = _integer(
            _required(
                record,
                "portnum",
                index,
                kind="Paquete",
            ),
            "portnum",
            index,
            kind="Paquete",
            maximum=0xFFFFFFFF,
        )

        imported_at_us = _integer(
            _required(
                record,
                "import_time_us",
                index,
                kind="Paquete",
            ),
            "import_time_us",
            index,
            kind="Paquete",
        )

        result.append(
            MeshtasticLivePacket(
                source=normalized_source,
                packet_id=packet_id,
                from_source_id=normalize_meshtastic_id(
                    from_node_id
                ),
                to_source_id=normalize_meshtastic_id(
                    to_node_id
                ),
                portnum=portnum,
                channel=_optional_text(
                    record.get("channel"),
                    "channel",
                    index,
                    kind="Paquete",
                ),
                imported_at_us=imported_at_us,
                long_name=_optional_text(
                    record.get("long_name"),
                    "long_name",
                    index,
                    kind="Paquete",
                ),
                to_long_name=_optional_text(
                    record.get("to_long_name"),
                    "to_long_name",
                    index,
                    kind="Paquete",
                ),
                payload=_text(
                    record.get("payload", ""),
                    "payload",
                    index,
                    kind="Paquete",
                ),
            )
        )

    return tuple(result)


def parse_ozulo_live_receptions(
    document: Any,
    *,
    packet_id: int,
    from_source_id: str | int,
    source: str = "ozulo_map",
) -> tuple[MeshtasticLiveReception, ...]:
    """Normaliza ``/api/packets_seen/<id>`` de O Zulo."""

    if not isinstance(source, str):
        raise TypeError("source debe ser texto")

    normalized_source = source.strip().lower()

    if normalized_source != "ozulo_map":
        raise ValueError(
            "As recepcións live de O Zulo deben usar "
            "source='ozulo_map'"
        )

    normalized_packet_id = _integer(
        packet_id,
        "packet_id",
        0,
        kind="Consulta",
        maximum=0xFFFFFFFF,
    )
    normalized_from_source_id = normalize_meshtastic_id(
        from_source_id
    )

    if not isinstance(document, Mapping):
        raise OzuloLiveError(
            "A raíz de /api/packets_seen debe ser un obxecto"
        )

    records = document.get("seen")

    if not isinstance(records, list):
        raise OzuloLiveError(
            "/api/packets_seen non contén unha lista seen"
        )

    result: list[MeshtasticLiveReception] = []

    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise OzuloLiveError(
                f"Recepción {index}: debe ser un obxecto"
            )

        record_packet_id = _integer(
            _required(
                record,
                "packet_id",
                index,
                kind="Recepción",
            ),
            "packet_id",
            index,
            kind="Recepción",
            maximum=0xFFFFFFFF,
        )

        if record_packet_id != normalized_packet_id:
            raise OzuloLiveError(
                f"Recepción {index}: packet_id non coincide "
                "coa consulta"
            )

        gateway_node_id = _integer(
            _required(
                record,
                "node_id",
                index,
                kind="Recepción",
            ),
            "node_id",
            index,
            kind="Recepción",
            maximum=0xFFFFFFFF,
        )

        result.append(
            MeshtasticLiveReception(
                source=normalized_source,
                packet_id=record_packet_id,
                from_source_id=normalized_from_source_id,
                gateway_source_id=normalize_meshtastic_id(
                    gateway_node_id
                ),
                rx_time=_integer(
                    _required(
                        record,
                        "rx_time",
                        index,
                        kind="Recepción",
                    ),
                    "rx_time",
                    index,
                    kind="Recepción",
                ),
                hop_limit=_integer(
                    _required(
                        record,
                        "hop_limit",
                        index,
                        kind="Recepción",
                    ),
                    "hop_limit",
                    index,
                    kind="Recepción",
                    maximum=255,
                ),
                hop_start=_optional_integer(
                    record.get("hop_start"),
                    "hop_start",
                    index,
                    kind="Recepción",
                    maximum=255,
                ),
                snr_db=_optional_number(
                    record.get("rx_snr"),
                    "rx_snr",
                    index,
                    kind="Recepción",
                ),
                rssi_dbm=_optional_number(
                    record.get("rx_rssi"),
                    "rx_rssi",
                    index,
                    kind="Recepción",
                ),
                channel=_optional_text(
                    record.get("channel"),
                    "channel",
                    index,
                    kind="Recepción",
                ),
                topic=_optional_text(
                    record.get("topic"),
                    "topic",
                    index,
                    kind="Recepción",
                ),
                imported_at_us=_integer(
                    _required(
                        record,
                        "import_time_us",
                        index,
                        kind="Recepción",
                    ),
                    "import_time_us",
                    index,
                    kind="Recepción",
                ),
            )
        )

    return tuple(result)
