"""Configuración central de Mesh Noroeste."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _positive_integer(name: str, default: int) -> int:
    raw_value = os.environ.get(name, str(default)).strip()

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(
            f"{name} debe ser un número entero; "
            f"valor recibido: {raw_value!r}"
        ) from exc

    if value < 1:
        raise ValueError(
            f"{name} debe ser mayor que cero; "
            f"valor recibido: {value}"
        )

    return value


def _configured_path(
    name: str,
    default: Path,
) -> Path:
    raw_value = os.environ.get(name)

    if raw_value is None or not raw_value.strip():
        return default.resolve()

    return Path(raw_value).expanduser().resolve()


def _optional_configured_path(
    name: str,
) -> Path | None:
    raw_value = os.environ.get(name)

    if raw_value is None or not raw_value.strip():
        return None

    return Path(raw_value).expanduser().resolve()


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuración validada de la aplicación."""

    root_dir: Path
    data_dir: Path
    state_dir: Path
    active_node_hours: int
    recent_node_days: int
    historical_node_days: int
    configuration_warnings_path: Path | None = None
    exclusions_path: Path | None = None

    @classmethod
    def from_env(
        cls,
        root_dir: Path | None = None,
    ) -> "Settings":
        project_root = (
            root_dir
            if root_dir is not None
            else Path(__file__).resolve().parents[2]
        ).resolve()

        active_node_hours = _positive_integer(
            "ACTIVE_NODE_HOURS",
            24,
        )
        recent_node_days = _positive_integer(
            "RECENT_NODE_DAYS",
            7,
        )
        historical_node_days = _positive_integer(
            "HISTORICAL_NODE_DAYS",
            30,
        )

        if active_node_hours > recent_node_days * 24:
            raise ValueError(
                "ACTIVE_NODE_HOURS no puede superar "
                "la ventana expresada por RECENT_NODE_DAYS"
            )

        if historical_node_days < recent_node_days:
            raise ValueError(
                "HISTORICAL_NODE_DAYS debe ser mayor "
                "o igual que RECENT_NODE_DAYS"
            )

        return cls(
            root_dir=project_root,
            data_dir=_configured_path(
                "MESH_DATA_DIR",
                project_root / "data",
            ),
            state_dir=_configured_path(
                "MESH_STATE_DIR",
                project_root / "state",
            ),
            active_node_hours=active_node_hours,
            recent_node_days=recent_node_days,
            historical_node_days=historical_node_days,
            configuration_warnings_path=(
                _optional_configured_path(
                    "MESH_CONFIGURATION_WARNINGS_PATH"
                )
            ),
            exclusions_path=(
                _optional_configured_path(
                    "MESH_EXCLUSIONS_PATH"
                )
            ),
        )
