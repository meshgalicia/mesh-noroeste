"""Probas da persistencia do estado incremental live."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from mesh_noroeste.storage import (
    SCHEMA_VERSION,
    ObservationStore,
)


UPDATED_AT = "2026-08-17T05:45:00Z"


class LiveCursorStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        self.database_path = (
            Path(self.temporary_directory.name)
            / "live-state.db"
        )
        self.store = ObservationStore(
            self.database_path
        )

    def test_missing_cursor_returns_none(self) -> None:
        self.assertIsNone(
            self.store.load_live_cursor(
                "ozulo_map"
            )
        )

        self.assertEqual(
            self.store.schema_version(),
            SCHEMA_VERSION,
        )

    def test_cursor_survives_new_store_instance(
        self,
    ) -> None:
        self.store.save_live_cursor(
            "ozulo_map",
            1_786_907_236_648_410,
            updated_at=UPDATED_AT,
        )

        reopened = ObservationStore(
            self.database_path
        )

        self.assertEqual(
            reopened.load_live_cursor(
                "ozulo_map"
            ),
            1_786_907_236_648_410,
        )
        self.assertEqual(
            reopened.quick_check(),
            "ok",
        )

    def test_cursor_can_advance(self) -> None:
        self.store.save_live_cursor(
            "ozulo_map",
            100,
            updated_at="2026-08-17T05:40:00Z",
        )

        self.store.save_live_cursor(
            "ozulo_map",
            200,
            updated_at="2026-08-17T05:41:00Z",
        )

        self.assertEqual(
            self.store.load_live_cursor(
                "ozulo_map"
            ),
            200,
        )

    def test_same_cursor_can_be_confirmed_again(
        self,
    ) -> None:
        self.store.save_live_cursor(
            "ozulo_map",
            100,
            updated_at="2026-08-17T05:40:00Z",
        )

        self.store.save_live_cursor(
            "ozulo_map",
            100,
            updated_at="2026-08-17T05:41:00Z",
        )

        self.assertEqual(
            self.store.load_live_cursor(
                "ozulo_map"
            ),
            100,
        )

    def test_cursor_cannot_move_backwards(
        self,
    ) -> None:
        self.store.save_live_cursor(
            "ozulo_map",
            200,
            updated_at="2026-08-17T05:40:00Z",
        )

        with self.assertRaisesRegex(
            ValueError,
            "non pode retroceder",
        ):
            self.store.save_live_cursor(
                "ozulo_map",
                199,
                updated_at="2026-08-17T05:41:00Z",
            )

        self.assertEqual(
            self.store.load_live_cursor(
                "ozulo_map"
            ),
            200,
        )

    def test_negative_cursor_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "non pode ser negativo",
        ):
            self.store.save_live_cursor(
                "ozulo_map",
                -1,
                updated_at=UPDATED_AT,
            )

    def test_boolean_cursor_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "debe ser un enteiro",
        ):
            self.store.save_live_cursor(
                "ozulo_map",
                True,
                updated_at=UPDATED_AT,
            )

    def test_unknown_source_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Fuente no admitida",
        ):
            self.store.load_live_cursor(
                "fonte_inventada"
            )


class LiveCursorMigrationTests(unittest.TestCase):
    def test_version_eleven_database_adds_live_state(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = (
                Path(directory)
                / "migration-v11.db"
            )
            store = ObservationStore(
                database_path
            )

            # Creamos unha base actual e reproducimos despois
            # exactamente o estado estrutural anterior a v12.
            store.initialize()

            with closing(
                sqlite3.connect(
                    database_path
                )
            ) as connection:
                with connection:
                    connection.execute(
                        "DROP TABLE live_source_state"
                    )
                    connection.execute(
                        "PRAGMA user_version = 11"
                    )

            migrated = ObservationStore(
                database_path
            )

            self.assertIsNone(
                migrated.load_live_cursor(
                    "ozulo_map"
                )
            )
            self.assertEqual(
                migrated.schema_version(),
                SCHEMA_VERSION,
            )
            self.assertEqual(
                migrated.quick_check(),
                "ok",
            )

            with closing(
                sqlite3.connect(
                    database_path
                )
            ) as connection:
                table = connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                      AND name = 'live_source_state'
                    """
                ).fetchone()

            self.assertIsNotNone(table)

            migrated.save_live_cursor(
                "ozulo_map",
                123456,
                updated_at=UPDATED_AT,
            )

            self.assertEqual(
                migrated.load_live_cursor(
                    "ozulo_map"
                ),
                123456,
            )


if __name__ == "__main__":
    unittest.main()
