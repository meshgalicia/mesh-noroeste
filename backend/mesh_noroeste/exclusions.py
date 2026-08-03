"""Carga y validación de exclusiones privadas de nodos."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

from mesh_noroeste.normalization import canonical_node_id


class ExclusionsError(ValueError):
    """Indica que la configuración de exclusiones no es válida."""


def _normalized_canonical_id(
    value: Any,
    context: str,
) -> str:
    if not isinstance(value, str):
        raise ExclusionsError(
            f"{context}: canonical_id debe ser texto"
        )

    candidate = value.strip()

    if not candidate:
        raise ExclusionsError(
            f"{context}: canonical_id no puede estar vacío"
        )

    if ":" not in candidate:
        raise ExclusionsError(
            f"{context}: canonical_id debe incluir "
            "el prefijo de red"
        )

    network, source_id = candidate.split(":", 1)

    if not network or not source_id:
        raise ExclusionsError(
            f"{context}: canonical_id no es válido"
        )

    try:
        return canonical_node_id(
            network,
            source_id,
        )
    except (TypeError, ValueError) as exc:
        raise ExclusionsError(
            f"{context}: canonical_id no es válido: {exc}"
        ) from exc


def _validate_note(
    value: Any,
    context: str,
) -> None:
    if not isinstance(value, str):
        raise ExclusionsError(
            f"{context}: note debe ser texto"
        )

    normalized = value.strip()

    if not normalized:
        raise ExclusionsError(
            f"{context}: note no puede estar vacía"
        )

    if len(normalized) > 1000:
        raise ExclusionsError(
            f"{context}: note supera 1000 caracteres"
        )


def load_exclusions(
    path: Path | str | None,
) -> frozenset[str]:
    """Carga los identificadores canónicos excluidos."""

    if path is None:
        return frozenset()

    resolved_path = Path(path).expanduser().resolve()

    try:
        document = json.loads(
            resolved_path.read_text(encoding="utf-8")
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ExclusionsError(
            "No se pudo leer la lista de exclusiones "
            f"{resolved_path}: {exc}"
        ) from exc

    if not isinstance(document, Mapping):
        raise ExclusionsError(
            "La raíz de la lista de exclusiones "
            "debe ser un objeto"
        )

    root_fields = set(document)

    if root_fields != {"exclusions"}:
        missing = {"exclusions"} - root_fields
        unexpected = root_fields - {"exclusions"}
        details: list[str] = []

        if missing:
            details.append(
                "falta: " + ", ".join(sorted(missing))
            )

        if unexpected:
            details.append(
                "sobran: " + ", ".join(sorted(unexpected))
            )

        raise ExclusionsError(
            "Campos raíz incorrectos: "
            + "; ".join(details)
        )

    records = document["exclusions"]

    if not isinstance(records, list):
        raise ExclusionsError(
            "exclusions debe ser una lista"
        )

    normalized_ids: set[str] = set()

    for index, record in enumerate(records):
        context = f"Exclusión {index}"

        if not isinstance(record, Mapping):
            raise ExclusionsError(
                f"{context}: debe ser un objeto"
            )

        fields = set(record)
        allowed_fields = {
            "canonical_id",
            "note",
        }

        if "canonical_id" not in record:
            raise ExclusionsError(
                f"{context}: falta el campo 'canonical_id'"
            )

        unexpected = fields - allowed_fields

        if unexpected:
            raise ExclusionsError(
                f"{context}: campos no admitidos: "
                + ", ".join(sorted(unexpected))
            )

        canonical_id = _normalized_canonical_id(
            record["canonical_id"],
            context,
        )

        if "note" in record:
            _validate_note(
                record["note"],
                context,
            )

        if canonical_id in normalized_ids:
            raise ExclusionsError(
                f"{context}: identificador duplicado "
                f"{canonical_id}"
            )

        normalized_ids.add(canonical_id)

    return frozenset(normalized_ids)
