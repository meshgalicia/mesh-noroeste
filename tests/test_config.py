"""Pruebas de la configuración del backend."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mesh_noroeste.config import Settings


CONFIG_VARIABLES = (
    "ACTIVE_NODE_HOURS",
    "RECENT_NODE_DAYS",
    "HISTORICAL_NODE_DAYS",
    "MESH_DATA_DIR",
    "MESH_STATE_DIR",
    "MESH_CONFIGURATION_WARNINGS_PATH",
    "MESH_EXCLUSIONS_PATH",
)


class SettingsTests(unittest.TestCase):
    def clean_environment(self) -> dict[str, str]:
        return {
            key: value
            for key, value in os.environ.items()
            if key not in CONFIG_VARIABLES
        }

    def test_default_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            with patch.dict(
                os.environ,
                self.clean_environment(),
                clear=True,
            ):
                settings = Settings.from_env(root)

        self.assertEqual(settings.root_dir, root.resolve())
        self.assertEqual(
            settings.data_dir,
            (root / "data").resolve(),
        )
        self.assertEqual(
            settings.state_dir,
            (root / "state").resolve(),
        )
        self.assertEqual(settings.active_node_hours, 24)
        self.assertEqual(settings.recent_node_days, 7)
        self.assertEqual(settings.historical_node_days, 30)
        self.assertIsNone(
            settings.configuration_warnings_path
        )
        self.assertIsNone(settings.exclusions_path)

    def test_environment_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            custom_data = root / "generated"
            custom_state = root / "database"
            custom_warnings = root / "warnings.json"
            custom_exclusions = root / "exclusions.json"

            environment = self.clean_environment()
            environment.update(
                {
                    "ACTIVE_NODE_HOURS": "12",
                    "RECENT_NODE_DAYS": "5",
                    "HISTORICAL_NODE_DAYS": "45",
                    "MESH_DATA_DIR": str(custom_data),
                    "MESH_STATE_DIR": str(custom_state),
                    "MESH_CONFIGURATION_WARNINGS_PATH": (
                        str(custom_warnings)
                    ),
                    "MESH_EXCLUSIONS_PATH": (
                        str(custom_exclusions)
                    ),
                }
            )

            with patch.dict(
                os.environ,
                environment,
                clear=True,
            ):
                settings = Settings.from_env(root)

        self.assertEqual(settings.active_node_hours, 12)
        self.assertEqual(settings.recent_node_days, 5)
        self.assertEqual(settings.historical_node_days, 45)
        self.assertEqual(
            settings.data_dir,
            custom_data.resolve(),
        )
        self.assertEqual(
            settings.state_dir,
            custom_state.resolve(),
        )
        self.assertEqual(
            settings.configuration_warnings_path,
            custom_warnings.resolve(),
        )
        self.assertEqual(
            settings.exclusions_path,
            custom_exclusions.resolve(),
        )

    def test_invalid_integer_is_rejected(self) -> None:
        environment = self.clean_environment()
        environment["ACTIVE_NODE_HOURS"] = "mañana"

        with patch.dict(
            os.environ,
            environment,
            clear=True,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "ACTIVE_NODE_HOURS debe ser un número entero",
            ):
                Settings.from_env()

    def test_active_window_cannot_exceed_recent_window(
        self,
    ) -> None:
        environment = self.clean_environment()
        environment.update(
            {
                "ACTIVE_NODE_HOURS": "49",
                "RECENT_NODE_DAYS": "2",
            }
        )

        with patch.dict(
            os.environ,
            environment,
            clear=True,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "ACTIVE_NODE_HOURS no puede superar",
            ):
                Settings.from_env()

    def test_historical_window_cannot_be_shorter(
        self,
    ) -> None:
        environment = self.clean_environment()
        environment.update(
            {
                "RECENT_NODE_DAYS": "10",
                "HISTORICAL_NODE_DAYS": "7",
            }
        )

        with patch.dict(
            os.environ,
            environment,
            clear=True,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "HISTORICAL_NODE_DAYS debe ser mayor",
            ):
                Settings.from_env()


if __name__ == "__main__":
    unittest.main()
