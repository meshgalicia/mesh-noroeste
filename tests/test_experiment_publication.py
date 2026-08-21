"""Probas da publicación experimental."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mesh_noroeste.experiment_publication import (
    EXPERIMENT_CSV_FILENAME,
    EXPERIMENT_PUBLIC_FILENAME,
    EXPERIMENT_XLSX_FILENAME,
    publish_experiment_report,
)
from mesh_noroeste.experiment_report import (
    EXPERIMENT_REPORT_SCHEMA,
)
from mesh_noroeste.experiment_store import (
    connect_experiment_store,
)


class ExperimentPublicationTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.temporary = (
            tempfile.TemporaryDirectory()
        )

        self.root = Path(
            self.temporary.name
        )

        self.database = (
            self.root
            / "experiment.db"
        )

        self.output = (
            self.root
            / "public"
        )

        connection = (
            connect_experiment_store(
                self.database
            )
        )

        connection.close()


    def tearDown(self) -> None:
        self.temporary.cleanup()


    def test_publishes_expected_filename(
        self,
    ) -> None:
        path = (
            publish_experiment_report(
                self.database,
                self.output,
                generated_at=(
                    "2026-08-19T12:00:00Z"
                ),
            )
        )

        self.assertEqual(
            path,
            (
                self.output
                / EXPERIMENT_PUBLIC_FILENAME
            ).resolve(),
        )

        self.assertTrue(
            path.is_file()
        )


    def test_publishes_downloadable_exports(
        self,
    ) -> None:
        publish_experiment_report(
            self.database,
            self.output,
            generated_at=(
                "2026-08-19T12:00:00Z"
            ),
        )

        csv_path = (
            self.output
            / EXPERIMENT_CSV_FILENAME
        )

        xlsx_path = (
            self.output
            / EXPERIMENT_XLSX_FILENAME
        )

        self.assertTrue(
            csv_path.is_file()
        )

        self.assertTrue(
            xlsx_path.is_file()
        )

        self.assertGreater(
            csv_path.stat().st_size,
            0,
        )

        self.assertGreater(
            xlsx_path.stat().st_size,
            0,
        )


    def test_published_document_is_valid(
        self,
    ) -> None:
        path = (
            publish_experiment_report(
                self.database,
                self.output,
                generated_at=(
                    "2026-08-19T12:00:00Z"
                ),
            )
        )

        document = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            document["schema"],
            EXPERIMENT_REPORT_SCHEMA,
        )

        self.assertEqual(
            document["generated_at"],
            "2026-08-19T12:00:00Z",
        )

        self.assertIn(
            "LongFast",
            document["channels"],
        )

        self.assertIn(
            "NarrowFast",
            document["channels"],
        )


    def test_public_artifacts_are_world_readable(
        self,
    ) -> None:
        publish_experiment_report(
            self.database,
            self.output,
            generated_at=(
                "2026-08-19T12:00:00Z"
            ),
        )

        for filename in (
            "experiment.json",
            "experiment.csv",
            "experiment.xlsx",
        ):
            path = (
                self.output
                / filename
            )

            self.assertTrue(
                path.is_file()
            )

            self.assertEqual(
                (
                    path.stat().st_mode
                    & 0o777
                ),
                0o644,
                filename,
            )


    def test_replaces_previous_document(
        self,
    ) -> None:
        self.output.mkdir(
            parents=True,
            exist_ok=True,
        )

        target = (
            self.output
            / EXPERIMENT_PUBLIC_FILENAME
        )

        target.write_text(
            '{"old": true}\n',
            encoding="utf-8",
        )

        publish_experiment_report(
            self.database,
            self.output,
            generated_at=(
                "2026-08-19T12:00:00Z"
            ),
        )

        document = json.loads(
            target.read_text(
                encoding="utf-8"
            )
        )

        self.assertNotIn(
            "old",
            document,
        )

        self.assertEqual(
            document["schema"],
            EXPERIMENT_REPORT_SCHEMA,
        )


    def test_failure_does_not_replace_target(
        self,
    ) -> None:
        self.output.mkdir(
            parents=True,
            exist_ok=True,
        )

        target = (
            self.output
            / EXPERIMENT_PUBLIC_FILENAME
        )

        original = (
            '{"preserve": true}\n'
        )

        target.write_text(
            original,
            encoding="utf-8",
        )

        with patch(
            (
                "mesh_noroeste."
                "experiment_publication."
                "os.replace"
            ),
            side_effect=OSError(
                "simulated failure"
            ),
        ):
            with self.assertRaises(
                OSError
            ):
                publish_experiment_report(
                    self.database,
                    self.output,
                    generated_at=(
                        "2026-08-19T12:00:00Z"
                    ),
                )

        self.assertEqual(
            target.read_text(
                encoding="utf-8"
            ),
            original,
        )

        temporary_files = list(
            self.output.glob(
                ".experiment.json.*.tmp"
            )
        )

        self.assertEqual(
            temporary_files,
            [],
        )


if __name__ == "__main__":
    unittest.main()
