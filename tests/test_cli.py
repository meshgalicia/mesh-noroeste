"""Pruebas de la interfaz de línea de comandos."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import ANY, patch

from mesh_noroeste.application import (
    CollectionResult,
    MALHA_PT_URL,
    MESHCORE_HUB_NODES_URL,
    MESHCORE_HUB_PAGE_SIZE,
    MESHCORE_MAP_URL,
    MESHVIEW_ES_URL,
    OZULO_MAP_EDGES_URL,
    OZULO_MAP_NODES_URL,
)
from mesh_noroeste.cli import main
from mesh_noroeste.http_client import FetchError
from mesh_noroeste.malha_http import (
    MALHA_TIMEOUT_SECONDS,
)
from mesh_noroeste.publication import (
    PUBLIC_DOCUMENT_NAMES,
    PUBLIC_GENERATIONS_DIRECTORY,
    PUBLIC_MANIFEST_NAME,
)
from mesh_noroeste.storage import SCHEMA_VERSION
from mesh_noroeste.domain import make_edge_observation, make_observation
from mesh_noroeste.storage import ObservationStore


def read_public_document(
    directory: Path,
    filename: str,
) -> dict[str, object]:
    manifest = json.loads(
        (
            directory
            / PUBLIC_MANIFEST_NAME
        ).read_text(encoding="utf-8")
    )

    relative_path = manifest["documents"][filename]

    return json.loads(
        (
            directory
            / relative_path
        ).read_text(encoding="utf-8")
    )


class CommandLineTests(unittest.TestCase):
    def environment(
        self,
        root: Path,
    ) -> dict[str, str]:
        return {
            "MESH_DATA_DIR": str(root / "data"),
            "MESH_STATE_DIR": str(root / "state"),
            "ACTIVE_NODE_HOURS": "24",
            "RECENT_NODE_DAYS": "7",
            "HISTORICAL_NODE_DAYS": "30",
        }

    def test_publish_creates_empty_documents(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            standard_output = StringIO()

            with patch.dict(
                os.environ,
                self.environment(root),
                clear=True,
            ):
                with redirect_stdout(
                    standard_output
                ):
                    result = main(
                        [
                            "publish",
                            "--generated-at",
                            "2026-07-25T12:00:00Z",
                            "--bounds",
                            "36.5",
                            "-10.5",
                            "44.5",
                            "-3.5",
                        ]
                    )

            response = json.loads(
                standard_output.getvalue()
            )

            self.assertEqual(result, 0)
            self.assertEqual(
                response["status"],
                "ok",
            )
            self.assertEqual(
                response["observations"],
                0,
            )
            self.assertEqual(
                response["nodes"],
                0,
            )
            self.assertEqual(
                response["edges"],
                0,
            )

            self.assertEqual(
                sorted(
                    path.name
                    for path in (root / "data").iterdir()
                ),
                sorted(
                    (
                        PUBLIC_GENERATIONS_DIRECTORY,
                        PUBLIC_MANIFEST_NAME,
                    )
                ),

            )

            meta = read_public_document(
                root / "data",
                "meta.json",
                )

            self.assertEqual(
                meta["region"]["bounds"],
                {
                    "south": 36.5,
                    "west": -10.5,
                    "north": 44.5,
                    "east": -3.5,
                },
            )

    def test_compact_output_is_single_line_json(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            standard_output = StringIO()

            with patch.dict(
                os.environ,
                self.environment(root),
                clear=True,
            ):
                with redirect_stdout(standard_output):
                    result = main(
                        [
                            "--compact",
                            "publish",
                            "--generated-at",
                            "2026-07-25T12:00:00Z",
                        ]
                    )

            output = standard_output.getvalue()

            self.assertEqual(result, 0)
            self.assertEqual(
                len(output.rstrip("\n").splitlines()),
                1,
            )
            self.assertEqual(
                json.loads(output)["status"],
                "ok",
            )

    def test_check_reports_healthy_database(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = self.environment(root)

            with patch.dict(
                os.environ,
                environment,
                clear=True,
            ):
                with redirect_stdout(StringIO()):
                    publish_result = main(
                        [
                            "publish",
                            "--generated-at",
                            "2026-07-25T12:00:00Z",
                        ]
                    )

                standard_output = StringIO()

                with redirect_stdout(
                    standard_output
                ):
                    check_result = main(["check"])

            response = json.loads(
                standard_output.getvalue()
            )

            self.assertEqual(publish_result, 0)
            self.assertEqual(check_result, 0)
            self.assertEqual(
                response["quick_check"],
                "ok",
            )
            self.assertEqual(
                response["journal_mode"].lower(),
                "wal",
            )
            self.assertEqual(
                response["schema_version"],
                SCHEMA_VERSION,
            )
            self.assertEqual(
                response["observations"],
                0,
            )

    def test_collect_meshview_reports_success(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database_path = root / "custom.db"
            standard_output = StringIO()
            source_url = (
                "https://example.test/meshview-nodes"
            )

            collection_result = CollectionResult(
                database_path=database_path.resolve(),
                source="meshview_es",
                requested_url=source_url,
                final_url=source_url,
                bytes_received=929201,
                records_received=2783,
                records_inserted=2783,
            )

            with patch.dict(
                os.environ,
                self.environment(root),
                clear=True,
            ):
                with patch(
                    "mesh_noroeste.cli."
                    "collect_meshview_es",
                    return_value=collection_result,
                ) as mocked_collect:
                    with redirect_stdout(
                        standard_output
                    ):
                        result = main(
                            [
                                "collect-meshview",
                                "--database",
                                str(database_path),
                                "--url",
                                source_url,
                                "--timeout",
                                "7.5",
                                "--max-bytes",
                                "8000000",
                            ]
                        )

            response = json.loads(
                standard_output.getvalue()
            )

            self.assertEqual(result, 0)
            self.assertEqual(
                response,
                {
                    "status": "ok",
                    "source": "meshview_es",
                    "database": str(
                        database_path.resolve()
                    ),
                    "requested_url": source_url,
                    "final_url": source_url,
                    "bytes_received": 929201,
                    "records_received": 2783,
                    "records_inserted": 2783,
                },
            )

            mocked_collect.assert_called_once_with(
                settings=ANY,
                database_path=database_path,
                url=source_url,
                timeout=7.5,
                max_bytes=8000000,
            )

    def test_collect_meshview_failure_returns_error(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            standard_error = StringIO()

            with patch.dict(
                os.environ,
                self.environment(root),
                clear=True,
            ):
                with patch(
                    "mesh_noroeste.cli."
                    "collect_meshview_es",
                    side_effect=FetchError(
                        "HTTP 503 temporal"
                    ),
                ):
                    with redirect_stderr(
                        standard_error
                    ):
                        result = main(
                            ["collect-meshview"]
                        )

            self.assertEqual(result, 2)
            self.assertIn(
                "ERROR: HTTP 503 temporal",
                standard_error.getvalue(),
            )

    def test_collect_meshview_uses_public_url_by_default(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            collection_result = CollectionResult(
                database_path=(
                    root / "state" / "mesh-noroeste.db"
                ).resolve(),
                source="meshview_es",
                requested_url=MESHVIEW_ES_URL,
                final_url=MESHVIEW_ES_URL,
                bytes_received=1,
                records_received=0,
                records_inserted=0,
            )

            with patch.dict(
                os.environ,
                self.environment(root),
                clear=True,
            ):
                with patch(
                    "mesh_noroeste.cli."
                    "collect_meshview_es",
                    return_value=collection_result,
                ) as mocked_collect:
                    with redirect_stdout(StringIO()):
                        result = main(
                            ["collect-meshview"]
                        )

            self.assertEqual(result, 0)
            self.assertEqual(
                mocked_collect.call_args.kwargs["url"],
                MESHVIEW_ES_URL,
            )

    def test_collect_malha_reports_success(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database_path = root / "custom.db"
            cookie_path = root / "malha.cookies"
            cache_path = root / "malha.json"
            standard_output = StringIO()
            source_url = (
                "https://example.test/malha-locations"
            )

            collection_result = CollectionResult(
                database_path=database_path.resolve(),
                source="malha_pt",
                requested_url=source_url,
                final_url=source_url,
                bytes_received=1438709,
                records_received=2455,
                records_inserted=2455,
            )

            with patch.dict(
                os.environ,
                self.environment(root),
                clear=True,
            ):
                with patch(
                    "mesh_noroeste.cli.collect_malha_pt",
                    return_value=collection_result,
                ) as mocked_collect:
                    with redirect_stdout(
                        standard_output
                    ):
                        result = main(
                            [
                                "collect-malha",
                                "--database",
                                str(database_path),
                                "--cookie-file",
                                str(cookie_path),
                                "--cache-file",
                                str(cache_path),
                                "--url",
                                source_url,
                                "--timeout",
                                "61.5",
                                "--max-bytes",
                                "9000000",
                            ]
                        )

            response = json.loads(
                standard_output.getvalue()
            )

            self.assertEqual(result, 0)
            self.assertEqual(
                response,
                {
                    "status": "ok",
                    "source": "malha_pt",
                    "database": str(
                        database_path.resolve()
                    ),
                    "requested_url": source_url,
                    "final_url": source_url,
                    "bytes_received": 1438709,
                    "records_received": 2455,
                    "records_inserted": 2455,
                },
            )

            mocked_collect.assert_called_once_with(
                settings=ANY,
                database_path=database_path,
                cookie_path=cookie_path,
                cache_path=cache_path,
                url=source_url,
                timeout=61.5,
                max_bytes=9000000,
            )

    def test_collect_malha_failure_returns_error(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            standard_error = StringIO()

            with patch.dict(
                os.environ,
                self.environment(root),
                clear=True,
            ):
                with patch(
                    "mesh_noroeste.cli.collect_malha_pt",
                    side_effect=FetchError(
                        "HTTP 503 temporal"
                    ),
                ):
                    with redirect_stderr(
                        standard_error
                    ):
                        result = main(
                            ["collect-malha"]
                        )

            self.assertEqual(result, 2)
            self.assertIn(
                "ERROR: HTTP 503 temporal",
                standard_error.getvalue(),
            )

    def test_collect_malha_uses_defaults(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            collection_result = CollectionResult(
                database_path=(
                    root / "state" / "mesh-noroeste.db"
                ).resolve(),
                source="malha_pt",
                requested_url=MALHA_PT_URL,
                final_url=MALHA_PT_URL,
                bytes_received=1,
                records_received=0,
                records_inserted=0,
            )

            with patch.dict(
                os.environ,
                self.environment(root),
                clear=True,
            ):
                with patch(
                    "mesh_noroeste.cli.collect_malha_pt",
                    return_value=collection_result,
                ) as mocked_collect:
                    with redirect_stdout(StringIO()):
                        result = main(
                            ["collect-malha"]
                        )

            self.assertEqual(result, 0)

            arguments = mocked_collect.call_args.kwargs

            self.assertIsNone(
                arguments["database_path"]
            )
            self.assertIsNone(
                arguments["cookie_path"]
            )
            self.assertIsNone(
                arguments["cache_path"]
            )
            self.assertEqual(
                arguments["url"],
                MALHA_PT_URL,
            )
            self.assertEqual(
                arguments["timeout"],
                MALHA_TIMEOUT_SECONDS,
            )
            self.assertEqual(
                arguments["max_bytes"],
                20 * 1024 * 1024,
            )

    def test_collect_ozulo_reports_success(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database_path = root / "custom.db"
            standard_output = StringIO()
            nodes_url = (
                "https://example.test/ozulo-nodes.json"
            )
            edges_url = (
                "https://example.test/ozulo-edges.json"
            )

            collection_result = CollectionResult(
                database_path=database_path.resolve(),
                source="ozulo_map",
                requested_url=nodes_url,
                final_url=nodes_url,
                bytes_received=184500,
                records_received=1424,
                records_inserted=1424,
            )

            with patch.dict(
                os.environ,
                self.environment(root),
                clear=True,
            ):
                with patch(
                    "mesh_noroeste.cli.collect_ozulo_map",
                    return_value=collection_result,
                ) as mocked_collect:
                    with redirect_stdout(
                        standard_output
                    ):
                        result = main(
                            [
                                "collect-ozulo",
                                "--database",
                                str(database_path),
                                "--nodes-url",
                                nodes_url,
                                "--edges-url",
                                edges_url,
                                "--timeout",
                                "7.5",
                                "--max-bytes",
                                "18000000",
                            ]
                        )

            response = json.loads(
                standard_output.getvalue()
            )

            self.assertEqual(result, 0)
            self.assertEqual(
                response,
                {
                    "status": "ok",
                    "source": "ozulo_map",
                    "database": str(
                        database_path.resolve()
                    ),
                    "requested_url": nodes_url,
                    "final_url": nodes_url,
                    "bytes_received": 184500,
                    "records_received": 1424,
                    "records_inserted": 1424,
                },
            )
            mocked_collect.assert_called_once_with(
                settings=ANY,
                database_path=database_path,
                nodes_url=nodes_url,
                edges_url=edges_url,
                timeout=7.5,
                max_bytes=18000000,
            )

    def test_collect_ozulo_uses_public_urls_by_default(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            collection_result = CollectionResult(
                database_path=(
                    root / "state" / "mesh-noroeste.db"
                ).resolve(),
                source="ozulo_map",
                requested_url=OZULO_MAP_NODES_URL,
                final_url=OZULO_MAP_NODES_URL,
                bytes_received=1,
                records_received=0,
                records_inserted=0,
            )

            with patch.dict(
                os.environ,
                self.environment(root),
                clear=True,
            ):
                with patch(
                    "mesh_noroeste.cli.collect_ozulo_map",
                    return_value=collection_result,
                ) as mocked_collect:
                    with redirect_stdout(StringIO()):
                        result = main(
                            ["collect-ozulo"]
                        )

            self.assertEqual(result, 0)
            arguments = mocked_collect.call_args.kwargs
            self.assertEqual(
                arguments["nodes_url"],
                OZULO_MAP_NODES_URL,
            )
            self.assertEqual(
                arguments["edges_url"],
                OZULO_MAP_EDGES_URL,
            )

    def test_collect_meshcore_hub_reports_success(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database_path = root / "custom.db"
            standard_output = StringIO()
            source_url = (
                "https://example.test/api/v1/nodes"
            )

            collection_result = CollectionResult(
                database_path=database_path.resolve(),
                source="meshcore_hub",
                requested_url=(
                    source_url + "?limit=50&offset=0"
                ),
                final_url=(
                    source_url + "?limit=50&offset=50"
                ),
                bytes_received=6400,
                records_received=75,
                records_inserted=70,
                receptions_received=120,
                receptions_inserted=115,
            )

            environment = self.environment(root)
            environment[
                "MESHCORE_HUB_API_READ_KEY"
            ] = "read-secret"

            with patch.dict(
                os.environ,
                environment,
                clear=True,
            ):
                with patch(
                    "mesh_noroeste.cli."
                    "collect_meshcore_hub",
                    return_value=collection_result,
                ) as mocked_collect:
                    with redirect_stdout(
                        standard_output
                    ):
                        result = main(
                            [
                                "collect-meshcore-hub",
                                "--database",
                                str(database_path),
                                "--url",
                                source_url,
                                "--page-size",
                                "50",
                                "--timeout",
                                "7.5",
                                "--max-bytes",
                                "18000000",
                            ]
                        )

            response = json.loads(
                standard_output.getvalue()
            )

            self.assertEqual(result, 0)
            self.assertEqual(
                response,
                {
                    "status": "ok",
                    "source": "meshcore_hub",
                    "database": str(
                        database_path.resolve()
                    ),
                    "requested_url": (
                        source_url
                        + "?limit=50&offset=0"
                    ),
                    "final_url": (
                        source_url
                        + "?limit=50&offset=50"
                    ),
                    "bytes_received": 6400,
                    "records_received": 75,
                    "records_inserted": 70,
                    "receptions_received": 120,
                    "receptions_inserted": 115,
                },
            )

            mocked_collect.assert_called_once_with(
                settings=ANY,
                api_read_key="read-secret",
                database_path=database_path,
                url=source_url,
                page_size=50,
                timeout=7.5,
                max_bytes=18000000,
            )

    def test_collect_meshcore_hub_uses_defaults(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            collection_result = CollectionResult(
                database_path=(
                    root / "state" / "mesh-noroeste.db"
                ).resolve(),
                source="meshcore_hub",
                requested_url=MESHCORE_HUB_NODES_URL,
                final_url=MESHCORE_HUB_NODES_URL,
                bytes_received=1,
                records_received=0,
                records_inserted=0,
            )

            environment = self.environment(root)
            environment[
                "MESHCORE_HUB_API_READ_KEY"
            ] = "read-secret"

            with patch.dict(
                os.environ,
                environment,
                clear=True,
            ):
                with patch(
                    "mesh_noroeste.cli."
                    "collect_meshcore_hub",
                    return_value=collection_result,
                ) as mocked_collect:
                    with redirect_stdout(StringIO()):
                        result = main(
                            ["collect-meshcore-hub"]
                        )

            self.assertEqual(result, 0)

            arguments = mocked_collect.call_args.kwargs

            self.assertEqual(
                arguments["api_read_key"],
                "read-secret",
            )
            self.assertEqual(
                arguments["url"],
                MESHCORE_HUB_NODES_URL,
            )
            self.assertEqual(
                arguments["page_size"],
                MESHCORE_HUB_PAGE_SIZE,
            )
            self.assertIsNone(
                arguments["database_path"]
            )

    def test_collect_meshcore_hub_requires_key(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            standard_error = StringIO()

            with patch.dict(
                os.environ,
                self.environment(root),
                clear=True,
            ):
                with patch(
                    "mesh_noroeste.cli."
                    "collect_meshcore_hub"
                ) as mocked_collect:
                    with redirect_stderr(
                        standard_error
                    ):
                        result = main(
                            ["collect-meshcore-hub"]
                        )

            self.assertEqual(result, 2)
            self.assertIn(
                (
                    "ERROR: MESHCORE_HUB_API_READ_KEY "
                    "non está configurada"
                ),
                standard_error.getvalue(),
            )
            mocked_collect.assert_not_called()

    def test_collect_meshcore_reports_success(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database_path = root / "custom.db"
            standard_output = StringIO()
            source_url = (
                "https://example.test/meshcore-nodes"
            )

            collection_result = CollectionResult(
                database_path=database_path.resolve(),
                source="meshcore_map",
                requested_url=source_url,
                final_url=source_url,
                bytes_received=15218225,
                records_received=52326,
                records_inserted=52326,
            )

            with patch.dict(
                os.environ,
                self.environment(root),
                clear=True,
            ):
                with patch(
                    "mesh_noroeste.cli."
                    "collect_meshcore_map",
                    return_value=collection_result,
                ) as mocked_collect:
                    with redirect_stdout(
                        standard_output
                    ):
                        result = main(
                            [
                                "collect-meshcore",
                                "--database",
                                str(database_path),
                                "--url",
                                source_url,
                                "--timeout",
                                "7.5",
                                "--max-bytes",
                                "18000000",
                            ]
                        )

            response = json.loads(
                standard_output.getvalue()
            )

            self.assertEqual(result, 0)
            self.assertEqual(
                response,
                {
                    "status": "ok",
                    "source": "meshcore_map",
                    "database": str(
                        database_path.resolve()
                    ),
                    "requested_url": source_url,
                    "final_url": source_url,
                    "bytes_received": 15218225,
                    "records_received": 52326,
                    "records_inserted": 52326,
                },
            )

            mocked_collect.assert_called_once_with(
                settings=ANY,
                database_path=database_path,
                url=source_url,
                timeout=7.5,
                max_bytes=18000000,
            )

    def test_collect_meshcore_failure_returns_error(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            standard_error = StringIO()

            with patch.dict(
                os.environ,
                self.environment(root),
                clear=True,
            ):
                with patch(
                    "mesh_noroeste.cli."
                    "collect_meshcore_map",
                    side_effect=FetchError(
                        "HTTP 503 temporal"
                    ),
                ):
                    with redirect_stderr(
                        standard_error
                    ):
                        result = main(
                            ["collect-meshcore"]
                        )

            self.assertEqual(result, 2)
            self.assertIn(
                "ERROR: HTTP 503 temporal",
                standard_error.getvalue(),
            )

    def test_collect_meshcore_uses_public_url_by_default(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            collection_result = CollectionResult(
                database_path=(
                    root / "state" / "mesh-noroeste.db"
                ).resolve(),
                source="meshcore_map",
                requested_url=MESHCORE_MAP_URL,
                final_url=MESHCORE_MAP_URL,
                bytes_received=1,
                records_received=0,
                records_inserted=0,
            )

            with patch.dict(
                os.environ,
                self.environment(root),
                clear=True,
            ):
                with patch(
                    "mesh_noroeste.cli."
                    "collect_meshcore_map",
                    return_value=collection_result,
                ) as mocked_collect:
                    with redirect_stdout(StringIO()):
                        result = main(
                            ["collect-meshcore"]
                        )

            self.assertEqual(result, 0)
            self.assertEqual(
                mocked_collect.call_args.kwargs["url"],
                MESHCORE_MAP_URL,
            )

    def test_purge_node_deletes_and_republishes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exclusions_path = (
                root / "exclusions.json"
            )
            exclusions_path.write_text(
                json.dumps({
                    "exclusions": [{
                        "canonical_id": (
                            "meshtastic:!a35b4144"
                        ),
                    }],
                }),
                encoding="utf-8",
            )

            environment = self.environment(root)
            environment[
                "MESH_EXCLUSIONS_PATH"
            ] = str(exclusions_path)

            database_path = (
                root
                / "state"
                / "mesh-noroeste.db"
            )
            store = ObservationStore(database_path)

            target_a = make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="a35b4144",
                observed_at="2026-07-25T12:00:00Z",
            )
            target_b = make_observation(
                source="malha_pt",
                network="meshtastic",
                source_id="!A35B4144",
                observed_at="2026-07-25T12:01:00Z",
            )
            survivor_a = make_observation(
                source="malha_pt",
                network="meshtastic",
                source_id="b1234567",
                observed_at="2026-07-25T12:02:00Z",
            )
            survivor_b = make_observation(
                source="malha_pt",
                network="meshtastic",
                source_id="c7654321",
                observed_at="2026-07-25T12:03:00Z",
            )

            incident_edge = make_edge_observation(
                source="malha_pt",
                network="meshtastic",
                from_source_id="a35b4144",
                to_source_id="b1234567",
                edge_type="traceroute",
                directed=True,
                observed_at="2026-07-25T12:04:00Z",
            )
            survivor_edge = make_edge_observation(
                source="malha_pt",
                network="meshtastic",
                from_source_id="b1234567",
                to_source_id="c7654321",
                edge_type="traceroute",
                directed=True,
                observed_at="2026-07-25T12:05:00Z",
            )

            self.assertEqual(
                store.save([
                    target_a,
                    target_b,
                    survivor_a,
                    survivor_b,
                ]),
                4,
            )
            self.assertEqual(
                store.save_edges([
                    incident_edge,
                    survivor_edge,
                ]),
                2,
            )

            standard_output = StringIO()

            with patch.dict(
                os.environ,
                environment,
                clear=True,
            ):
                with redirect_stdout(standard_output):
                    result = main([
                        "purge-node",
                        " MESHTASTIC:!A35B4144 ",
                        "--generated-at",
                        "2026-07-30T12:00:00Z",
                    ])

            response = json.loads(
                standard_output.getvalue()
            )

            self.assertEqual(result, 0)
            self.assertEqual(
                response["status"],
                "ok",
            )
            self.assertEqual(
                response["canonical_id"],
                "meshtastic:!a35b4144",
            )
            self.assertEqual(
                response["deleted"],
                {
                    "node_observations": 2,
                    "edge_observations": 1,
                },
            )
            self.assertEqual(
                response["quick_check"],
                "ok",
            )
            self.assertEqual(
                response["published"][
                    "observations"
                ],
                2,
            )
            self.assertEqual(
                store.load(
                    "meshtastic:!a35b4144"
                ),
                [],
            )
            self.assertEqual(
                store.count_edges(),
                1,
            )

            public_nodes = read_public_document(
                root / "data",
                "nodes.json",
                )

            self.assertNotIn(
                "meshtastic:!a35b4144",
                {
                    node["id"]
                    for node in public_nodes["nodes"]
                },
            )

    def test_purge_node_rejects_unlisted_identifier(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exclusions_path = (
                root / "exclusions.json"
            )
            exclusions_path.write_text(
                json.dumps({
                    "exclusions": [{
                        "canonical_id": (
                            "meshtastic:!ffffffff"
                        ),
                    }],
                }),
                encoding="utf-8",
            )

            environment = self.environment(root)
            environment[
                "MESH_EXCLUSIONS_PATH"
            ] = str(exclusions_path)

            database_path = (
                root
                / "state"
                / "mesh-noroeste.db"
            )
            store = ObservationStore(database_path)
            target = make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="a35b4144",
                observed_at="2026-07-25T12:00:00Z",
            )
            self.assertEqual(
                store.save([target]),
                1,
            )

            standard_error = StringIO()

            with patch.dict(
                os.environ,
                environment,
                clear=True,
            ):
                with redirect_stderr(standard_error):
                    result = main([
                        "purge-node",
                        "meshtastic:!a35b4144",
                    ])

            self.assertEqual(result, 2)
            self.assertIn(
                "no figura en la lista privada",
                standard_error.getvalue(),
            )
            self.assertEqual(
                len(
                    store.load(
                        "meshtastic:!a35b4144"
                    )
                ),
                1,
            )
            self.assertFalse(
                (root / "data").exists()
            )

    def test_purge_node_remains_deleted_when_publish_fails(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exclusions_path = (
                root / "exclusions.json"
            )
            exclusions_path.write_text(
                json.dumps({
                    "exclusions": [{
                        "canonical_id": (
                            "meshtastic:!a35b4144"
                        ),
                    }],
                }),
                encoding="utf-8",
            )

            environment = self.environment(root)
            environment[
                "MESH_EXCLUSIONS_PATH"
            ] = str(exclusions_path)

            database_path = (
                root
                / "state"
                / "mesh-noroeste.db"
            )
            store = ObservationStore(database_path)
            target = make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="a35b4144",
                observed_at="2026-07-25T12:00:00Z",
            )
            self.assertEqual(
                store.save([target]),
                1,
            )

            standard_error = StringIO()

            with (
                patch.dict(
                    os.environ,
                    environment,
                    clear=True,
                ),
                patch(
                    "mesh_noroeste.cli."
                    "publish_from_store",
                    side_effect=RuntimeError(
                        "fallo de publicación"
                    ),
                ),
                redirect_stderr(standard_error),
            ):
                result = main([
                    "purge-node",
                    "meshtastic:!a35b4144",
                ])

            self.assertEqual(result, 2)
            self.assertIn(
                "fallo de publicación",
                standard_error.getvalue(),
            )
            self.assertEqual(
                store.load(
                    "meshtastic:!a35b4144"
                ),
                [],
            )


    def test_prune_reports_deleted_rows(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            standard_output = StringIO()

            with patch.dict(
                os.environ,
                self.environment(root),
                clear=True,
            ):
                with redirect_stdout(
                    standard_output
                ):
                    result = main(
                        [
                            "prune",
                            "--before",
                            "2026-07-01T00:00:00Z",
                        ]
                    )

            response = json.loads(
                standard_output.getvalue()
            )

            self.assertEqual(result, 0)
            self.assertEqual(
                response["before"],
                "2026-07-01T00:00:00Z",
            )
            self.assertEqual(
                response["deleted"],
                {
                    "edge_observations": 0,
                    "node_observations": 0,
                    "observer_receptions": 0,
                    "source_runs": 0,
                },
            )
            self.assertEqual(
                response["quick_check"],
                "ok",
            )

    def test_invalid_timestamp_returns_error(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            standard_error = StringIO()

            with patch.dict(
                os.environ,
                self.environment(root),
                clear=True,
            ):
                with redirect_stderr(
                    standard_error
                ):
                    result = main(
                        [
                            "publish",
                            "--generated-at",
                            "fecha-imposible",
                        ]
                    )

            self.assertEqual(result, 2)
            self.assertIn(
                "ERROR:",
                standard_error.getvalue(),
            )

    def test_invalid_retention_returns_error(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = self.environment(root)

            environment[
                "HISTORICAL_NODE_DAYS"
            ] = "2"

            standard_error = StringIO()

            with patch.dict(
                os.environ,
                environment,
                clear=True,
            ):
                with redirect_stderr(
                    standard_error
                ):
                    result = main(["check"])

            self.assertEqual(result, 2)
            self.assertIn(
                "HISTORICAL_NODE_DAYS",
                standard_error.getvalue(),
            )


if __name__ == "__main__":
    unittest.main()
