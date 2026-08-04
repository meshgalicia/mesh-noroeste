"""Pruebas de las operaciones completas."""

from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import call, patch

import msgpack

from mesh_noroeste.application import (
    MALHA_PT_URL,
    MESHCORE_MAP_URL,
    MESHVIEW_ES_NEIGHBOR_EDGES_URL,
    MESHVIEW_ES_POSITION_PACKETS_URL,
    MESHVIEW_ES_TRACEROUTE_EDGES_URL,
    MESHVIEW_ES_URL,
    OZULO_MAP_EDGES_URL,
    OZULO_MAP_NODES_URL,
    OZULO_NEIGHBOR_PACKETS_URL,
    collect_malha_pt,
    collect_meshcore_map,
    collect_meshview_es,
    collect_ozulo_map,
    publish_from_store,
)
from mesh_noroeste.config import Settings
from mesh_noroeste.domain import (
    make_edge_observation,
    make_neighbor_observation,
    make_observation,
)
from mesh_noroeste.exclusions import ExclusionsError
from mesh_noroeste.http_client import (
    BinaryFetchResult,
    FetchError,
    JsonFetchResult,
)
from mesh_noroeste.malha_http import (
    MALHA_TIMEOUT_SECONDS,
    MalhaFetchResult,
)
from mesh_noroeste.publication import (
    PUBLIC_DOCUMENT_NAMES,
    PUBLIC_GENERATIONS_DIRECTORY,
    PUBLIC_MANIFEST_NAME,
)
from mesh_noroeste.storage import ObservationStore


NOW = "2026-07-25T12:00:00Z"

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


def meshcore_payload() -> bytes:
    inserted_at = datetime(
        2026,
        7,
        20,
        9,
        10,
        tzinfo=timezone.utc,
    )
    updated_at = datetime(
        2026,
        7,
        25,
        11,
        58,
        tzinfo=timezone.utc,
    )

    return msgpack.packb(
        [
            {
                "pk": bytes.fromhex("01" * 32),
                "t": 2,
                "n": "Repetidor de prueba",
                "id": inserted_at,
                "la": datetime(
                    1970,
                    1,
                    1,
                    tzinfo=timezone.utc,
                ),
                "ud": updated_at,
                "lat": 43.1,
                "lon": -8.1,
                "p": {
                    "freq": 869.618,
                    "bw": 62.5,
                    "sf": 8,
                    "cr": 8,
                },
                "s": "u",
                "l": b"\x11\x00",
            }
        ],
        use_bin_type=True,
        datetime=True,
    )


def meshview_document() -> dict[str, object]:
    first_seen = datetime(
        2026,
        7,
        20,
        9,
        10,
        tzinfo=timezone.utc,
    )
    last_seen = datetime(
        2026,
        7,
        25,
        11,
        58,
        tzinfo=timezone.utc,
    )

    return {
        "nodes": [
            {
                "id": "!0123abcd",
                "node_id": int("0123abcd", 16),
                "first_seen_us": int(
                    first_seen.timestamp()
                    * 1_000_000
                ),
                "last_seen_us": int(
                    last_seen.timestamp()
                    * 1_000_000
                ),
                "short_name": "BRMA",
                "long_name": "Bruma Connection",
                "hw_model": "HELTEC_V4",
                "role": "CLIENT_MUTE",
                "last_lat": 431_000_000,
                "last_long": -81_000_000,
                "channel": "LongFast",
                "firmware": "2.7.15",
                "is_mqtt_gateway": False,
            }
        ]
    }



def meshview_position_packets_document() -> dict[str, object]:
    imported_at = datetime(
        2026,
        7,
        25,
        11,
        58,
        tzinfo=timezone.utc,
    )

    return {
        "latest_import_time": int(
            imported_at.timestamp() * 1_000_000
        ),
        "packets": [
            {
                "from_node_id": int("0123abcd", 16),
                "import_time_us": int(
                    imported_at.timestamp() * 1_000_000
                ),
                "payload": (
                    "latitude_i: 431000000\n"
                    "longitude_i: -81000000\n"
                    "precision_bits: 18"
                ),
            }
        ],
    }

def meshview_edges_document(
    edge_type: str,
) -> dict[str, object]:
    return {
        "edges": [
            {
                "from": int("0123abcd", 16),
                "to": int("89abcdef", 16),
                "type": edge_type,
            }
        ]
    }


def malha_document() -> dict[str, object]:
    observed_at = datetime(
        2026,
        7,
        25,
        11,
        58,
        tzinfo=timezone.utc,
    )

    return {
        "locations": [
            {
                "node_id": int("0123abcd", 16),
                "hex_id": "!0123abcd",
                "timestamp": observed_at.timestamp(),
                "latitude": 43.1,
                "longitude": -8.1,
                "altitude": 120,
                "short_name": "BRMA",
                "long_name": "Bruma Connection",
                "hw_model": "HELTEC_V4",
                "role": "CLIENT_MUTE",
                "avg_snr": 7.25,
                "primary_channel": "LongFast",
            }
        ],
        "traceroute_links": [
            {
                "from_node_id": int(
                    "0123abcd",
                    16,
                ),
                "to_node_id": int(
                    "89abcdef",
                    16,
                ),
                "last_seen": observed_at.timestamp(),
                "avg_snr": 6.5,
            }
        ],
        "packet_links": [],
    }


def ozulo_nodes_document() -> dict[str, object]:
    return {
        "count": 1,
        "nodes": [
            {
                "node_id": "!70e4b96f",
                "first_seen": 1_782_661_488,
                "last_seen": 1_785_325_863,
                "updated_at": 1_785_325_864,
                "short_name": "ath0",
                "long_name": "ea2ath-0",
                "hardware": "TRACKER_T1000_E",
                "role": "CLIENT",
                "latitude": 42.3493632,
                "longitude": -7.2482816,
                "altitude": 630,
                "precision_bits": 14,
                "battery_level": 76,
                "voltage": 4.02,
                "channel_util": 3.5,
                "air_util_tx": 1.2,
                "snr": 7.25,
                "rssi": -91,
                "channel": "LongFast",
                "firmware": "2.7.15",
                "hops_away": 2,
                "is_mqtt_gateway": 0,
            }
        ],
    }


def ozulo_edges_document() -> dict[str, object]:
    return {
        "count": 1,
        "edges": [
            {
                "from_node": "!70e4b96f",
                "to_node": "!9e780100",
                "edge_type": "traceroute",
                "last_seen": 1_785_325_865,
                "snr": 5.75,
            }
        ],
    }


def ozulo_neighbor_packets_document() -> dict[str, object]:
    return {
        "latest_import_time": 1_785_814_685,
        "packets": [
            {
                "id": 3_396_163_074,
                "import_time_us": 1_785_814_685_059_745,
                "from_node_id": 2_956_739_956,
                "to_node_id": 1,
                "portnum": 71,
                "payload": (
                    "node_id: 2956739956\n"
                    "neighbors {\n"
                    "  node_id: 2905611713\n"
                    "  snr: 4.0\n"
                    "}\n"
                ),
            }
        ],
    }


class ApplicationTests(unittest.TestCase):
    def settings(
        self,
        root: Path,
        *,
        warnings_path: Path | None = None,
        exclusions_path: Path | None = None,
    ) -> Settings:
        environment = {}

        if warnings_path is not None:
            environment[
                "MESH_CONFIGURATION_WARNINGS_PATH"
            ] = str(warnings_path)

        if exclusions_path is not None:
            environment[
                "MESH_EXCLUSIONS_PATH"
            ] = str(exclusions_path)

        with patch.dict(
            os.environ,
            environment,
            clear=True,
        ):
            return Settings.from_env(root)

    def test_collect_meshview_es_saves_and_records_run(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = self.settings(root)
            documents = (
                meshview_document(),
                meshview_position_packets_document(),
                meshview_edges_document("traceroute"),
                meshview_edges_document("neighbor"),
            )
            urls = (
                MESHVIEW_ES_URL,
                MESHVIEW_ES_POSITION_PACKETS_URL,
                MESHVIEW_ES_TRACEROUTE_EDGES_URL,
                MESHVIEW_ES_NEIGHBOR_EDGES_URL,
            )
            encoded = tuple(
                json.dumps(document).encode("utf-8")
                for document in documents
            )
            fetched = tuple(
                JsonFetchResult(
                    document=document,
                    requested_url=url,
                    final_url=url,
                    status=200,
                    content_type="application/json",
                    bytes_received=len(payload),
                )
                for document, url, payload in zip(
                    documents,
                    urls,
                    encoded,
                    strict=True,
                )
            )
            timestamps = iter(
                (
                    "2026-07-25T11:59:00Z",
                    "2026-07-25T12:00:00Z",
                    "2026-07-25T12:01:00Z",
                )
            )

            with patch(
                "mesh_noroeste.application.fetch_json",
                side_effect=fetched,
            ) as mocked_fetch:
                result = collect_meshview_es(
                    settings=settings,
                    clock=lambda: next(timestamps),
                )

            database_path = (
                settings.state_dir / "mesh-noroeste.db"
            ).resolve()
            store = ObservationStore(database_path)

            self.assertEqual(result.database_path, database_path)
            self.assertEqual(result.source, "meshview_es")
            self.assertEqual(result.records_received, 1)
            self.assertEqual(result.records_inserted, 1)
            self.assertEqual(
                result.bytes_received,
                sum(len(payload) for payload in encoded),
            )
            self.assertEqual(store.count(), 1)
            self.assertEqual(
                store.load_all()[0].position_precision_bits,
                18,
            )

            with closing(
                sqlite3.connect(database_path)
            ) as connection:
                edges = connection.execute(
                    """
                    SELECT
                        from_source_id,
                        to_source_id,
                        edge_type,
                        directed,
                        observed_at
                    FROM edge_observations
                    ORDER BY edge_type
                    """
                ).fetchall()

            self.assertEqual(
                edges,
                [
                    (
                        "!0123abcd",
                        "!89abcdef",
                        "neighbor",
                        0,
                        "2026-07-25T12:00:00Z",
                    ),
                    (
                        "!0123abcd",
                        "!89abcdef",
                        "traceroute",
                        1,
                        "2026-07-25T12:00:00Z",
                    ),
                ],
            )
            self.assertEqual(
                store.source_statistics()["meshview_es"],
                {
                    "last_success": "2026-07-25T12:01:00Z",
                    "last_error_at": None,
                    "last_error": None,
                    "records_received": 1,
                },
            )
            mocked_fetch.assert_has_calls(
                [
                    call(
                        url,
                        timeout=20.0,
                        max_bytes=20 * 1024 * 1024,
                    )
                    for url in urls
                ]
            )
            self.assertEqual(mocked_fetch.call_count, 4)

    def test_collect_meshview_preserves_edges_omitted_by_later_snapshot(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = self.settings(root)

            documents = (
                meshview_document(),
                meshview_position_packets_document(),
                meshview_edges_document("traceroute"),
                meshview_edges_document("neighbor"),
                meshview_document(),
                meshview_position_packets_document(),
                {"edges": []},
                {"edges": []},
            )
            urls = (
                MESHVIEW_ES_URL,
                MESHVIEW_ES_POSITION_PACKETS_URL,
                MESHVIEW_ES_TRACEROUTE_EDGES_URL,
                MESHVIEW_ES_NEIGHBOR_EDGES_URL,
            ) * 2

            fetched = tuple(
                JsonFetchResult(
                    document=document,
                    requested_url=url,
                    final_url=url,
                    status=200,
                    content_type="application/json",
                    bytes_received=len(
                        json.dumps(document).encode("utf-8")
                    ),
                )
                for document, url in zip(
                    documents,
                    urls,
                    strict=True,
                )
            )
            timestamps = iter(
                (
                    "2026-07-25T11:59:00Z",
                    "2026-07-25T12:00:00Z",
                    "2026-07-25T12:01:00Z",
                    "2026-07-25T12:04:00Z",
                    "2026-07-25T12:05:00Z",
                    "2026-07-25T12:06:00Z",
                )
            )

            with patch(
                "mesh_noroeste.application.fetch_json",
                side_effect=fetched,
            ):
                collect_meshview_es(
                    settings=settings,
                    clock=lambda: next(timestamps),
                )
                collect_meshview_es(
                    settings=settings,
                    clock=lambda: next(timestamps),
                )

            store = ObservationStore(
                settings.state_dir / "mesh-noroeste.db"
            )

            self.assertEqual(store.count_edges(), 2)

    def test_collect_meshview_es_records_failure(
        self,
    ) -> None:
        documents = (
            meshview_document(),
            meshview_position_packets_document(),
            meshview_edges_document("traceroute"),
            meshview_edges_document("neighbor"),
        )
        urls = (
            MESHVIEW_ES_URL,
            MESHVIEW_ES_POSITION_PACKETS_URL,
            MESHVIEW_ES_TRACEROUTE_EDGES_URL,
            MESHVIEW_ES_NEIGHBOR_EDGES_URL,
        )

        for failed_index in range(4):
            with self.subTest(failed_url=urls[failed_index]):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    settings = self.settings(root)
                    fetched = tuple(
                        JsonFetchResult(
                            document=document,
                            requested_url=url,
                            final_url=url,
                            status=200,
                            content_type="application/json",
                            bytes_received=len(
                                json.dumps(document).encode("utf-8")
                            ),
                        )
                        for document, url in zip(
                            documents,
                            urls,
                            strict=True,
                        )
                    )
                    timestamps = iter(
                        (
                            "2026-07-25T11:59:00Z",
                            "2026-07-25T12:00:00Z",
                        )
                    )
                    sleep_delays: list[float] = []

                    def fetch_side_effect(
                        url: str,
                        **kwargs: object,
                    ) -> JsonFetchResult:
                        if url == urls[failed_index]:
                            raise FetchError(
                                "Error HTTP 503 temporal"
                            )

                        return fetched[urls.index(url)]

                    with patch(
                        "mesh_noroeste.application.fetch_json",
                        side_effect=fetch_side_effect,
                    ) as mocked_fetch:
                        with self.assertRaisesRegex(
                            FetchError,
                            "HTTP 503 temporal",
                        ):
                            collect_meshview_es(
                                settings=settings,
                                clock=lambda: next(timestamps),
                                sleeper=sleep_delays.append,
                            )

                    database_path = (
                        settings.state_dir / "mesh-noroeste.db"
                    )
                    store = ObservationStore(database_path)

                    self.assertEqual(store.count(), 0)

                    with closing(
                sqlite3.connect(database_path)
            ) as connection:
                        edge_count = connection.execute(
                            "SELECT COUNT(*) FROM edge_observations"
                        ).fetchone()[0]

                    self.assertEqual(edge_count, 0)
                    self.assertEqual(
                        store.source_statistics()["meshview_es"],
                        {
                            "last_success": None,
                            "last_error_at": (
                                "2026-07-25T12:00:00Z"
                            ),
                            "last_error": (
                                "FetchError: Error HTTP 503 temporal"
                            ),
                            "records_received": 0,
                        },
                    )
                    expected_calls = [
                        call(
                            url,
                            timeout=20.0,
                            max_bytes=20 * 1024 * 1024,
                        )
                        for url in urls[:failed_index]
                    ]
                    expected_calls.extend(
                        [
                            call(
                                urls[failed_index],
                                timeout=20.0,
                                max_bytes=20 * 1024 * 1024,
                            )
                        ]
                        * 3
                    )

                    self.assertEqual(
                        mocked_fetch.call_args_list,
                        expected_calls,
                    )
                    self.assertEqual(
                        sleep_delays,
                        [1.0, 3.0],
                    )

    def test_collect_malha_saves_nodes_edges_and_run(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = self.settings(root)
            document = malha_document()
            encoded = json.dumps(
                document
            ).encode("utf-8")

            cookie_path = (
                root
                / "cache"
                / "malha-pt.cookies"
            ).resolve()
            cache_path = (
                root
                / "cache"
                / "malha-pt.json"
            ).resolve()

            fetched = MalhaFetchResult(
                document=document,
                requested_url=MALHA_PT_URL,
                final_url=MALHA_PT_URL,
                status=200,
                content_type=(
                    "application/json; charset=utf-8"
                ),
                bytes_received=len(encoded),
                attempts=1,
                cookie_path=cookie_path,
                cache_path=cache_path,
            )

            timestamps = iter(
                (
                    "2026-07-25T11:59:00Z",
                    "2026-07-25T12:00:00Z",
                )
            )

            with patch(
                "mesh_noroeste.application."
                "fetch_malha_pt",
                return_value=fetched,
            ) as mocked_fetch:
                result = collect_malha_pt(
                    settings=settings,
                    clock=lambda: next(timestamps),
                )

            database_path = (
                settings.state_dir
                / "mesh-noroeste.db"
            ).resolve()
            store = ObservationStore(
                database_path
            )

            self.assertEqual(
                result.database_path,
                database_path,
            )
            self.assertEqual(
                result.source,
                "malha_pt",
            )
            self.assertEqual(
                result.records_received,
                2,
            )
            self.assertEqual(
                result.records_inserted,
                2,
            )
            self.assertEqual(
                result.bytes_received,
                len(encoded),
            )

            self.assertEqual(store.count(), 1)
            self.assertEqual(
                store.count_edges(),
                1,
            )

            node = store.load_all()[0]
            edge = store.load_all_edges()[0]

            self.assertEqual(
                node.id,
                "meshtastic:!0123abcd",
            )
            self.assertEqual(
                edge.id,
                (
                    "meshtastic:traceroute:"
                    "!0123abcd:!89abcdef"
                ),
            )

            self.assertEqual(
                store.source_statistics()[
                    "malha_pt"
                ],
                {
                    "last_success": (
                        "2026-07-25T12:00:00Z"
                    ),
                    "last_error_at": None,
                    "last_error": None,
                    "records_received": 2,
                },
            )

            mocked_fetch.assert_called_once_with(
                cookie_path=cookie_path,
                cache_path=cache_path,
                url=MALHA_PT_URL,
                timeout=MALHA_TIMEOUT_SECONDS,
                max_bytes=20 * 1024 * 1024,
            )

    def test_collect_malha_records_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = self.settings(root)

            timestamps = iter(
                (
                    "2026-07-25T11:59:00Z",
                    "2026-07-25T12:00:00Z",
                )
            )

            with patch(
                "mesh_noroeste.application."
                "fetch_malha_pt",
                side_effect=FetchError(
                    "HTTP 503 temporal"
                ),
            ):
                with self.assertRaisesRegex(
                    FetchError,
                    "HTTP 503 temporal",
                ):
                    collect_malha_pt(
                        settings=settings,
                        clock=lambda: next(timestamps),
                    )

            store = ObservationStore(
                settings.state_dir
                / "mesh-noroeste.db"
            )

            self.assertEqual(store.count(), 0)
            self.assertEqual(
                store.count_edges(),
                0,
            )
            self.assertEqual(
                store.source_statistics()[
                    "malha_pt"
                ],
                {
                    "last_success": None,
                    "last_error_at": (
                        "2026-07-25T12:00:00Z"
                    ),
                    "last_error": (
                        "FetchError: HTTP 503 temporal"
                    ),
                    "records_received": 0,
                },
            )

    def test_collect_ozulo_map_saves_and_records_run(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = self.settings(root)
            nodes = ozulo_nodes_document()
            edges = ozulo_edges_document()
            neighbor_packets = (
                ozulo_neighbor_packets_document()
            )

            fetched_nodes = JsonFetchResult(
                document=nodes,
                requested_url=OZULO_MAP_NODES_URL,
                final_url=OZULO_MAP_NODES_URL,
                status=200,
                content_type="application/json",
                bytes_received=len(
                    json.dumps(nodes).encode("utf-8")
                ),
            )
            fetched_edges = JsonFetchResult(
                document=edges,
                requested_url=OZULO_MAP_EDGES_URL,
                final_url=OZULO_MAP_EDGES_URL,
                status=200,
                content_type="application/json",
                bytes_received=len(
                    json.dumps(edges).encode("utf-8")
                ),
            )
            fetched_neighbor_packets = JsonFetchResult(
                document=neighbor_packets,
                requested_url=OZULO_NEIGHBOR_PACKETS_URL,
                final_url=OZULO_NEIGHBOR_PACKETS_URL,
                status=200,
                content_type="application/json",
                bytes_received=len(
                    json.dumps(
                        neighbor_packets
                    ).encode("utf-8")
                ),
            )

            timestamps = iter(
                (
                    "2026-07-29T11:59:00Z",
                    "2026-07-29T12:00:00Z",
                )
            )

            with patch(
                "mesh_noroeste.application.fetch_json",
                side_effect=(
                    fetched_nodes,
                    fetched_edges,
                    fetched_neighbor_packets,
                ),
            ) as mocked_fetch:
                result = collect_ozulo_map(
                    settings=settings,
                    clock=lambda: next(timestamps),
                )

            database_path = (
                settings.state_dir
                / "mesh-noroeste.db"
            ).resolve()
            store = ObservationStore(database_path)

            self.assertEqual(
                result.database_path,
                database_path,
            )
            self.assertEqual(result.source, "ozulo_map")
            self.assertEqual(result.records_received, 3)
            self.assertEqual(result.records_inserted, 3)
            self.assertEqual(store.count(), 1)
            self.assertEqual(store.count_edges(), 1)
            self.assertEqual(store.count_neighbors(), 1)
            self.assertEqual(
                store.source_statistics()["ozulo_map"],
                {
                    "last_success": (
                        "2026-07-29T12:00:00Z"
                    ),
                    "last_error_at": None,
                    "last_error": None,
                    "records_received": 3,
                },
            )
            self.assertEqual(
                mocked_fetch.call_args_list,
                [
                    call(
                        OZULO_MAP_NODES_URL,
                        timeout=20.0,
                        max_bytes=20 * 1024 * 1024,
                    ),
                    call(
                        OZULO_MAP_EDGES_URL,
                        timeout=20.0,
                        max_bytes=20 * 1024 * 1024,
                    ),
                    call(
                        OZULO_NEIGHBOR_PACKETS_URL,
                        timeout=20.0,
                        max_bytes=20 * 1024 * 1024,
                    ),
                ],
            )

    def test_collect_ozulo_map_records_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = self.settings(root)

            timestamps = iter(
                (
                    "2026-07-29T11:59:00Z",
                    "2026-07-29T12:00:00Z",
                )
            )

            with patch(
                "mesh_noroeste.application.fetch_json",
                side_effect=FetchError(
                    "HTTP 503 temporal"
                ),
            ):
                with self.assertRaisesRegex(
                    FetchError,
                    "HTTP 503 temporal",
                ):
                    collect_ozulo_map(
                        settings=settings,
                        clock=lambda: next(timestamps),
                    )

            store = ObservationStore(
                settings.state_dir
                / "mesh-noroeste.db"
            )

            self.assertEqual(store.count(), 0)
            self.assertEqual(store.count_edges(), 0)
            self.assertEqual(
                store.source_statistics()["ozulo_map"],
                {
                    "last_success": None,
                    "last_error_at": (
                        "2026-07-29T12:00:00Z"
                    ),
                    "last_error": (
                        "FetchError: HTTP 503 temporal"
                    ),
                    "records_received": 0,
                },
            )

    def test_collect_meshcore_map_saves_and_records_run(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = self.settings(root)
            payload = meshcore_payload()

            fetched = BinaryFetchResult(
                payload=payload,
                requested_url=MESHCORE_MAP_URL,
                final_url=MESHCORE_MAP_URL,
                status=200,
                content_type="application/msgpack",
                bytes_received=len(payload),
            )

            timestamps = iter(
                (
                    "2026-07-25T11:59:00Z",
                    "2026-07-25T12:00:00Z",
                )
            )

            with patch(
                "mesh_noroeste.application.fetch_bytes",
                return_value=fetched,
            ) as mocked_fetch:
                result = collect_meshcore_map(
                    settings=settings,
                    clock=lambda: next(timestamps),
                )

            database_path = (
                settings.state_dir
                / "mesh-noroeste.db"
            ).resolve()
            store = ObservationStore(database_path)

            self.assertEqual(
                result.database_path,
                database_path,
            )
            self.assertEqual(
                result.source,
                "meshcore_map",
            )
            self.assertEqual(
                result.records_received,
                1,
            )
            self.assertEqual(
                result.records_inserted,
                1,
            )
            self.assertEqual(
                result.bytes_received,
                len(payload),
            )
            self.assertEqual(store.count(), 1)

            self.assertEqual(
                store.source_statistics()[
                    "meshcore_map"
                ],
                {
                    "last_success": (
                        "2026-07-25T12:00:00Z"
                    ),
                    "last_error_at": None,
                    "last_error": None,
                    "records_received": 1,
                },
            )

            mocked_fetch.assert_called_once_with(
                MESHCORE_MAP_URL,
                timeout=20.0,
                max_bytes=20 * 1024 * 1024,
                accept="application/msgpack",
            )

    def test_collect_meshcore_map_records_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = self.settings(root)

            timestamps = iter(
                (
                    "2026-07-25T11:59:00Z",
                    "2026-07-25T12:00:00Z",
                )
            )

            with patch(
                "mesh_noroeste.application.fetch_bytes",
                side_effect=FetchError(
                    "HTTP 503 temporal"
                ),
            ):
                with self.assertRaisesRegex(
                    FetchError,
                    "HTTP 503 temporal",
                ):
                    collect_meshcore_map(
                        settings=settings,
                        clock=lambda: next(timestamps),
                    )

            store = ObservationStore(
                settings.state_dir
                / "mesh-noroeste.db"
            )

            self.assertEqual(store.count(), 0)
            self.assertEqual(
                store.source_statistics()[
                    "meshcore_map"
                ],
                {
                    "last_success": None,
                    "last_error_at": (
                        "2026-07-25T12:00:00Z"
                    ),
                    "last_error": (
                        "FetchError: HTTP 503 temporal"
                    ),
                    "records_received": 0,
                },
            )


    def write_exclusions(
        self,
        root: Path,
        canonical_id: str,
    ) -> Path:
        path = root / "exclusions.json"
        path.write_text(
            json.dumps({
                "exclusions": [{
                    "canonical_id": canonical_id,
                }],
            }),
            encoding="utf-8",
        )
        return path

    def test_collect_meshview_filters_excluded_data(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exclusions_path = self.write_exclusions(
                root,
                "meshtastic:!a35b4144",
            )
            settings = self.settings(
                root,
                exclusions_path=exclusions_path,
            )

            excluded = make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="a35b4144",
                observed_at=NOW,
            )
            included = make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="b1234567",
                observed_at=NOW,
            )
            edge = make_edge_observation(
                source="meshview_es",
                network="meshtastic",
                from_source_id="a35b4144",
                to_source_id="b1234567",
                edge_type="traceroute",
                directed=True,
                observed_at=NOW,
            )
            fetched = JsonFetchResult(
                document={},
                requested_url=MESHVIEW_ES_URL,
                final_url=MESHVIEW_ES_URL,
                status=200,
                content_type="application/json",
                bytes_received=1,
            )

            with (
                patch(
                    "mesh_noroeste.application.fetch_json",
                    return_value=fetched,
                ),
                patch(
                    "mesh_noroeste.application."
                    "parse_meshview_es_position_precisions",
                    return_value={},
                ),
                patch(
                    "mesh_noroeste.application."
                    "parse_meshview_es",
                    return_value=[
                        excluded,
                        included,
                    ],
                ),
                patch(
                    "mesh_noroeste.application."
                    "parse_meshview_es_edges",
                    side_effect=[
                        [edge],
                        [],
                    ],
                ),
            ):
                result = collect_meshview_es(
                    settings=settings,
                    clock=lambda: NOW,
                )

            store = ObservationStore(
                settings.state_dir
                / "mesh-noroeste.db"
            )

            self.assertEqual(
                result.records_received,
                2,
            )
            self.assertEqual(
                result.records_inserted,
                1,
            )
            self.assertEqual(
                [
                    node.id
                    for node in store.load_all()
                ],
                ["meshtastic:!b1234567"],
            )
            self.assertEqual(
                store.load_all_edges(),
                [],
            )

    def test_collect_malha_filters_excluded_data(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exclusions_path = self.write_exclusions(
                root,
                "meshtastic:!a35b4144",
            )
            settings = self.settings(
                root,
                exclusions_path=exclusions_path,
            )

            excluded = make_observation(
                source="malha_pt",
                network="meshtastic",
                source_id="a35b4144",
                observed_at=NOW,
            )
            included = make_observation(
                source="malha_pt",
                network="meshtastic",
                source_id="b1234567",
                observed_at=NOW,
            )
            edge = make_edge_observation(
                source="malha_pt",
                network="meshtastic",
                from_source_id="a35b4144",
                to_source_id="b1234567",
                edge_type="traceroute",
                directed=True,
                observed_at=NOW,
            )
            fetched = SimpleNamespace(
                document={},
                requested_url=MALHA_PT_URL,
                final_url=MALHA_PT_URL,
                bytes_received=1,
            )

            with (
                patch(
                    "mesh_noroeste.application."
                    "fetch_malha_pt",
                    return_value=fetched,
                ),
                patch(
                    "mesh_noroeste.application."
                    "parse_malha_pt",
                    return_value=[
                        excluded,
                        included,
                    ],
                ),
                patch(
                    "mesh_noroeste.application."
                    "parse_malha_pt_traceroutes",
                    return_value=[edge],
                ),
            ):
                result = collect_malha_pt(
                    settings=settings,
                    clock=lambda: NOW,
                )

            store = ObservationStore(
                settings.state_dir
                / "mesh-noroeste.db"
            )

            self.assertEqual(
                result.records_received,
                3,
            )
            self.assertEqual(
                result.records_inserted,
                1,
            )
            self.assertEqual(
                [
                    node.id
                    for node in store.load_all()
                ],
                ["meshtastic:!b1234567"],
            )
            self.assertEqual(
                store.load_all_edges(),
                [],
            )

    def test_collect_ozulo_filters_excluded_data(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exclusions_path = self.write_exclusions(
                root,
                "meshtastic:!a35b4144",
            )
            settings = self.settings(
                root,
                exclusions_path=exclusions_path,
            )

            excluded = make_observation(
                source="ozulo_map",
                network="meshtastic",
                source_id="a35b4144",
                observed_at=NOW,
            )
            included = make_observation(
                source="ozulo_map",
                network="meshtastic",
                source_id="b1234567",
                observed_at=NOW,
            )
            edge = make_edge_observation(
                source="ozulo_map",
                network="meshtastic",
                from_source_id="a35b4144",
                to_source_id="b1234567",
                edge_type="traceroute",
                directed=True,
                observed_at=NOW,
            )
            fetched = JsonFetchResult(
                document={},
                requested_url=OZULO_MAP_NODES_URL,
                final_url=OZULO_MAP_NODES_URL,
                status=200,
                content_type="application/json",
                bytes_received=1,
            )

            with (
                patch(
                    "mesh_noroeste.application.fetch_json",
                    return_value=fetched,
                ),
                patch(
                    "mesh_noroeste.application."
                    "parse_ozulo_map_nodes",
                    return_value=[
                        excluded,
                        included,
                    ],
                ),
                patch(
                    "mesh_noroeste.application."
                    "parse_ozulo_map_edges",
                    return_value=[edge],
                ),
                patch(
                    "mesh_noroeste.application."
                    "parse_ozulo_neighbor_packets",
                    return_value=[],
                ),
            ):
                result = collect_ozulo_map(
                    settings=settings,
                    clock=lambda: NOW,
                )

            store = ObservationStore(
                settings.state_dir
                / "mesh-noroeste.db"
            )

            self.assertEqual(
                result.records_received,
                3,
            )
            self.assertEqual(
                result.records_inserted,
                1,
            )
            self.assertEqual(
                [
                    node.id
                    for node in store.load_all()
                ],
                ["meshtastic:!b1234567"],
            )
            self.assertEqual(
                store.load_all_edges(),
                [],
            )

    def test_collect_meshcore_filters_excluded_data(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            excluded_source_id = "01" * 32
            included_source_id = "02" * 32
            exclusions_path = self.write_exclusions(
                root,
                "meshcore:" + excluded_source_id,
            )
            settings = self.settings(
                root,
                exclusions_path=exclusions_path,
            )

            excluded = make_observation(
                source="meshcore_map",
                network="meshcore",
                source_id=excluded_source_id,
                observed_at=NOW,
            )
            included = make_observation(
                source="meshcore_map",
                network="meshcore",
                source_id=included_source_id,
                observed_at=NOW,
            )
            fetched = SimpleNamespace(
                payload=b"",
                requested_url=MESHCORE_MAP_URL,
                final_url=MESHCORE_MAP_URL,
                bytes_received=1,
            )

            with (
                patch(
                    "mesh_noroeste.application.fetch_bytes",
                    return_value=fetched,
                ),
                patch(
                    "mesh_noroeste.application."
                    "parse_meshcore_map",
                    return_value=[
                        excluded,
                        included,
                    ],
                ),
            ):
                result = collect_meshcore_map(
                    settings=settings,
                    clock=lambda: NOW,
                )

            store = ObservationStore(
                settings.state_dir
                / "mesh-noroeste.db"
            )

            self.assertEqual(
                result.records_received,
                2,
            )
            self.assertEqual(
                result.records_inserted,
                1,
            )
            self.assertEqual(
                [
                    node.id
                    for node in store.load_all()
                ],
                [
                    "meshcore:"
                    + included_source_id
                ],
            )

    def test_invalid_exclusions_block_collection_before_fetch(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exclusions_path = (
                root / "exclusions.json"
            )
            exclusions_path.write_text(
                '{"exclusions": [}',
                encoding="utf-8",
            )
            settings = self.settings(
                root,
                exclusions_path=exclusions_path,
            )

            with patch(
                "mesh_noroeste.application.fetch_json"
            ) as mocked_fetch:
                with self.assertRaisesRegex(
                    ExclusionsError,
                    "No se pudo leer",
                ):
                    collect_meshview_es(
                        settings=settings,
                        clock=lambda: NOW,
                    )

            mocked_fetch.assert_not_called()
            self.assertFalse(
                settings.state_dir.exists()
            )

    def test_publish_from_populated_store(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = self.settings(root)

            database_path = (
                settings.state_dir
                / "mesh-noroeste.db"
            )

            store = ObservationStore(
                database_path
            )

            older = make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="a35b4144",
                observed_at=(
                    "2026-07-25T10:00:00Z"
                ),
                short_name="BRUMA",
                latitude=43.1,
                longitude=-8.1,
                position_updated_at=(
                    "2026-07-25T09:50:00Z"
                ),
            )

            newer = make_observation(
                source="malha_pt",
                network="meshtastic",
                source_id="!A35B4144",
                observed_at=(
                    "2026-07-25T11:00:00Z"
                ),
                long_name="Bruma Connection",
            )

            neighbor = make_neighbor_observation(
                source="ozulo_map",
                from_source_id="a35b4144",
                to_source_id="b1234567",
                observed_at="2026-07-25T11:30:00Z",
                snr_db=4.5,
            )

            self.assertEqual(
                store.save([older, newer]),
                2,
            )
            self.assertEqual(
                store.save_neighbors([neighbor]),
                1,
            )

            result = publish_from_store(
                settings=settings,
                generated_at=NOW,
                region_bounds={
                    "south": 36.5,
                    "west": -10.5,
                    "north": 44.5,
                    "east": -3.5,
                },
            )

            self.assertEqual(
                result.database_path,
                database_path.resolve(),
            )
            self.assertEqual(
                result.output_directory,
                settings.data_dir,
            )
            self.assertEqual(
                result.observation_count,
                2,
            )
            self.assertEqual(
                result.node_count,
                1,
            )
            self.assertEqual(
                result.edge_count,
                0,
            )
            self.assertEqual(
                tuple(
                    path.name
                    for path in result.written_files
                ),
                PUBLIC_DOCUMENT_NAMES,
            )

            nodes_document = read_public_document(
                settings.data_dir,
                "nodes.json",
            )

            neighbor_document = read_public_document(
                settings.data_dir,
                "neighbor-info.json",
            )

            stats_document = read_public_document(
                settings.data_dir,
                "stats.json",
            )

            self.assertEqual(
                neighbor_document["observations"],
                [
                    {
                        "source": "ozulo_map",
                        "network": "meshtastic",
                        "from_id": (
                            "meshtastic:!a35b4144"
                        ),
                        "to_id": (
                            "meshtastic:!b1234567"
                        ),
                        "observed_at": (
                            "2026-07-25T11:30:00Z"
                        ),
                        "snr_db": 4.5,
                    }
                ],
            )

            self.assertEqual(
                len(nodes_document["nodes"]),
                1,
            )
            self.assertEqual(
                nodes_document["nodes"][0]["id"],
                "meshtastic:!a35b4144",
            )
            self.assertEqual(
                nodes_document["nodes"][0][
                    "sources"
                ],
                ["meshview_es", "malha_pt"],
            )
            self.assertEqual(
                stats_document["totals"]["nodes"],
                1,
            )


    def test_publish_applies_configured_exclusions(
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
            settings = self.settings(
                root,
                exclusions_path=exclusions_path,
            )
            store = ObservationStore(
                settings.state_dir
                / "mesh-noroeste.db"
            )

            nodes = [
                make_observation(
                    source="malha_pt",
                    network="meshtastic",
                    source_id="a35b4144",
                    observed_at=(
                        "2026-07-25T11:30:00Z"
                    ),
                    latitude=43.1,
                    longitude=-8.1,
                    position_updated_at=(
                        "2026-07-25T11:30:00Z"
                    ),
                ),
                make_observation(
                    source="malha_pt",
                    network="meshtastic",
                    source_id="b1234567",
                    observed_at=(
                        "2026-07-25T11:31:00Z"
                    ),
                    latitude=42.9,
                    longitude=-8.0,
                    position_updated_at=(
                        "2026-07-25T11:31:00Z"
                    ),
                ),
            ]
            edge = make_edge_observation(
                source="malha_pt",
                network="meshtastic",
                from_source_id="a35b4144",
                to_source_id="b1234567",
                edge_type="traceroute",
                directed=True,
                observed_at=(
                    "2026-07-25T11:32:00Z"
                ),
            )

            self.assertEqual(store.save(nodes), 2)
            self.assertEqual(
                store.save_edges([edge]),
                1,
            )

            result = publish_from_store(
                settings=settings,
                generated_at=NOW,
            )

            nodes_document = read_public_document(
                settings.data_dir,
                "nodes.json",
            )
            edges_document = read_public_document(
                settings.data_dir,
                "edges.json",
            )
            stats_document = read_public_document(
                settings.data_dir,
                "stats.json",
            )

        self.assertEqual(
            result.observation_count,
            2,
        )
        self.assertEqual(result.node_count, 1)
        self.assertEqual(result.edge_count, 0)
        self.assertEqual(
            [
                node["id"]
                for node in nodes_document["nodes"]
            ],
            ["meshtastic:!b1234567"],
        )
        self.assertEqual(
            edges_document["edges"],
            [],
        )
        self.assertEqual(
            stats_document["totals"]["nodes"],
            1,
        )
        self.assertEqual(
            stats_document["totals"]["edges"],
            0,
        )

    def test_invalid_exclusions_block_publication(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exclusions_path = (
                root / "exclusions.json"
            )
            exclusions_path.write_text(
                '{"exclusions": [}',
                encoding="utf-8",
            )
            settings = self.settings(
                root,
                exclusions_path=exclusions_path,
            )

            with self.assertRaisesRegex(
                ExclusionsError,
                "No se pudo leer",
            ):
                publish_from_store(
                    settings=settings,
                    generated_at=NOW,
                )

            self.assertFalse(
                settings.data_dir.exists()
            )

    def test_publish_loads_edges_from_store(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = self.settings(root)
            store = ObservationStore(
                settings.state_dir
                / "mesh-noroeste.db"
            )

            nodes = [
                make_observation(
                    source="malha_pt",
                    network="meshtastic",
                    source_id="a35b4144",
                    observed_at=(
                        "2026-07-25T11:30:00Z"
                    ),
                    latitude=43.1,
                    longitude=-8.1,
                    position_updated_at=(
                        "2026-07-25T11:30:00Z"
                    ),
                ),
                make_observation(
                    source="malha_pt",
                    network="meshtastic",
                    source_id="b1234567",
                    observed_at=(
                        "2026-07-25T11:31:00Z"
                    ),
                    latitude=42.9,
                    longitude=-8.0,
                    position_updated_at=(
                        "2026-07-25T11:31:00Z"
                    ),
                ),
            ]

            edges = [
                make_edge_observation(
                    source="malha_pt",
                    network="meshtastic",
                    from_source_id="a35b4144",
                    to_source_id="b1234567",
                    edge_type="traceroute",
                    directed=True,
                    observed_at=(
                        "2026-07-25T10:00:00Z"
                    ),
                    metrics={"snr_db": 1.0},
                ),
                make_edge_observation(
                    source="malha_pt",
                    network="meshtastic",
                    from_source_id="a35b4144",
                    to_source_id="b1234567",
                    edge_type="traceroute",
                    directed=True,
                    observed_at=(
                        "2026-07-25T11:00:00Z"
                    ),
                    metrics={"snr_db": 7.5},
                ),
            ]

            self.assertEqual(store.save(nodes), 2)
            self.assertEqual(
                store.save_edges(edges),
                2,
            )

            result = publish_from_store(
                settings=settings,
                generated_at=NOW,
            )

            self.assertEqual(
                result.edge_count,
                1,
            )

            edges_document = read_public_document(
                settings.data_dir,
                "edges.json",
            )
            stats_document = read_public_document(
                settings.data_dir,
                "stats.json",
            )

            self.assertEqual(
                len(edges_document["edges"]),
                1,
            )
            self.assertEqual(
                edges_document["edges"][0][
                    "last_seen"
                ],
                "2026-07-25T11:00:00Z",
            )
            self.assertEqual(
                edges_document["edges"][0][
                    "metrics"
                ]["snr_db"],
                7.5,
            )
            self.assertEqual(
                stats_document["totals"]["edges"],
                1,
            )

    def test_publish_uses_source_runs(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = self.settings(root)

            database_path = (
                settings.state_dir
                / "mesh-noroeste.db"
            )
            store = ObservationStore(database_path)

            successful_run = store.begin_source_run(
                "meshcore_map",
                "2026-07-25T11:57:00Z",
            )
            store.finish_source_run(
                successful_run,
                finished_at=(
                    "2026-07-25T11:58:00Z"
                ),
                success=True,
                records_received=52326,
            )

            failed_run = store.begin_source_run(
                "meshcore_map",
                "2026-07-25T11:58:30Z",
            )
            store.finish_source_run(
                failed_run,
                finished_at=(
                    "2026-07-25T11:59:00Z"
                ),
                success=False,
                error_message=(
                    "HTTP 503 temporal"
                ),
            )

            publish_from_store(
                settings=settings,
                generated_at=NOW,
            )

            stats_document = read_public_document(
                settings.data_dir,
                "stats.json",
            )

            self.assertEqual(
                stats_document["sources"][
                    "meshcore_map"
                ],
                {
                    "last_success": (
                        "2026-07-25T11:58:00Z"
                    ),
                    "last_error_at": (
                        "2026-07-25T11:59:00Z"
                    ),
                    "last_error": (
                        "HTTP 503 temporal"
                    ),
                    "records_received": 52326,
                },
            )

    def test_publish_uses_configured_warning_analysis(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "warnings.json"
            source.write_text(
                json.dumps({
                    "updated": 1_785_193_457,
                    "nodes": [{
                        "id": "!a35b4144",
                        "issues": [{
                            "key": "position_fixed",
                            "severity": "high",
                        }],
                    }],
                }),
                encoding="utf-8",
            )

            settings = self.settings(
                root,
                warnings_path=source,
            )
            store = ObservationStore(
                settings.state_dir / "mesh-noroeste.db"
            )
            store.save([
                make_observation(
                    source="meshview_es",
                    network="meshtastic",
                    source_id="!a35b4144",
                    observed_at=NOW,
                    latitude=43.1,
                    longitude=-8.1,
                    position_updated_at=NOW,
                )
            ])

            publish_from_store(
                settings=settings,
                generated_at=NOW,
            )

            document = read_public_document(
                settings.data_dir,
                "configuration-warnings.json",
            )

        self.assertIs(
            document["analysis"]["available"],
            True,
        )
        self.assertEqual(
            document["analysis"]["analyzed_nodes"],
            1,
        )

    def test_invalid_warning_analysis_does_not_block_publish(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "warnings.json"
            source.write_text(
                '{"updated": true, "nodes": []}',
                encoding="utf-8",
            )
            settings = self.settings(
                root,
                warnings_path=source,
            )

            result = publish_from_store(
                settings=settings,
                generated_at=NOW,
            )

            document = read_public_document(
                settings.data_dir,
                "configuration-warnings.json",
            )

        self.assertEqual(result.node_count, 0)
        self.assertIs(
            document["analysis"]["available"],
            False,
        )
        self.assertEqual(document["nodes"], [])

    def test_empty_store_publishes_empty_documents(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = self.settings(root)

            result = publish_from_store(
                settings=settings,
                generated_at=NOW,
            )

            self.assertTrue(
                result.database_path.is_file()
            )
            self.assertEqual(
                result.observation_count,
                0,
            )
            self.assertEqual(
                result.node_count,
                0,
            )
            self.assertEqual(
                result.edge_count,
                0,
            )

            self.assertEqual(
                sorted(
                    path.name
                    for path in settings.data_dir.iterdir()
                ),
                sorted(
                    (
                        PUBLIC_GENERATIONS_DIRECTORY,
                        PUBLIC_MANIFEST_NAME,
                    )
                ),
            )

            nodes_document = read_public_document(
                settings.data_dir,
                "nodes.json",
            )

            self.assertEqual(
                nodes_document["nodes"],
                [],
            )


if __name__ == "__main__":
    unittest.main()
