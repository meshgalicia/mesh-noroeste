"""Pruebas de generación de documentos públicos."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import (
    Draft202012Validator,
    FormatChecker,
)

from mesh_noroeste.config import Settings
from mesh_noroeste.domain import (
    make_edge_observation,
    make_neighbor_observation,
    make_observation,
    make_observer_reception,
)
from mesh_noroeste.publication import (
    PUBLIC_DOCUMENT_NAMES,
    PUBLIC_GENERATIONS_DIRECTORY,
    PUBLIC_MANIFEST_NAME,
    PUBLIC_MANIFEST_SCHEMA,
    PUBLIC_GENERATIONS_TO_KEEP,
    build_public_documents,
    write_public_documents,
)
from mesh_noroeste.region import (
    DEFAULT_REGION_NAME,
    default_region_bounds,
)


NOW = "2026-07-25T12:00:00Z"


class PublicationTests(unittest.TestCase):
    def settings(self, root: Path) -> Settings:
        with patch.dict(
            os.environ,
            {},
            clear=True,
        ):
            return Settings.from_env(root)

    def observations(self):
        meshview = make_observation(
            source="meshview_es",
            network="meshtastic",
            source_id="a35b4144",
            observed_at="2026-07-25T10:00:00Z",
            first_seen="2026-07-20T09:00:00Z",
            short_name="BRUMA",
            role="CLIENT_MUTE",
            latitude=43.1,
            longitude=-8.1,
            position_precision_bits=14,
            position_updated_at=(
                "2026-07-25T09:50:00Z"
            ),
            metrics={
                "battery_percent": 76,
            },
        )

        malha = make_observation(
            source="malha_pt",
            network="meshtastic",
            source_id="!A35B4144",
            observed_at="2026-07-25T11:00:00Z",
            long_name="Bruma Connection",
            hardware="HELTEC_V4",
        )

        meshcore = make_observation(
            source="meshcore_map",
            network="meshcore",
            source_id="02AB34CD",
            observed_at="2026-07-18T12:00:00Z",
            node_type="repeater",
            is_observer=False,
            short_name="MC01",
            latitude=42.5,
            longitude=-8.5,
            position_updated_at=(
                "2026-07-18T11:50:00Z"
            ),
        )

        return meshview, malha, meshcore

    def test_documents_consolidate_and_count_nodes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            documents = build_public_documents(
                self.observations(),
                generated_at=NOW,
                settings=self.settings(root),
                region_bounds={
                    "south": 36.5,
                    "west": -10.5,
                    "north": 44.5,
                    "east": -3.5,
                },
            )

        self.assertEqual(
            set(documents),
            set(PUBLIC_DOCUMENT_NAMES),
        )

        nodes = documents["nodes.json"]["nodes"]

        self.assertEqual(len(nodes), 2)

        self.assertEqual(
            [node["id"] for node in nodes],
            [
                "meshcore:02ab34cd",
                "meshtastic:!a35b4144",
            ],
        )

        meshcore = nodes[0]
        meshtastic = nodes[1]

        self.assertIs(
            meshcore["is_observer"],
            False,
        )
        self.assertIsNone(
            meshtastic["is_observer"]
        )

        self.assertEqual(
            meshtastic["sources"],
            ["meshview_es", "malha_pt"],
        )
        self.assertEqual(
            meshtastic["long_name"],
            "Bruma Connection",
        )
        self.assertEqual(
            meshtastic["metrics"][
                "battery_percent"
            ],
            76.0,
        )
        self.assertEqual(
            meshtastic["position_precision_bits"],
            14,
        )

        stats = documents["stats.json"]

        self.assertEqual(
            stats["totals"]["nodes"],
            2,
        )
        self.assertEqual(
            stats["totals"]["active_nodes"],
            1,
        )
        self.assertEqual(
            stats["totals"]["recent_nodes"],
            1,
        )
        self.assertEqual(
            stats["totals"]["historical_nodes"],
            0,
        )
        self.assertEqual(
            stats["totals"]["positioned_nodes"],
            2,
        )

        self.assertEqual(
            stats["sources"]["meshview_es"][
                "records_received"
            ],
            1,
        )
        self.assertEqual(
            stats["sources"]["malha_pt"][
                "records_received"
            ],
            1,
        )
        self.assertEqual(
            stats["sources"]["meshcore_map"][
                "records_received"
            ],
            1,
        )
        self.assertEqual(
            stats["sources"]["meshcore_hub"][
                "records_received"
            ],
            0,
        )


    def test_exclusions_remove_nodes_edges_stats_and_warnings(
        self,
    ) -> None:
        excluded = make_observation(
            source="meshview_es",
            network="meshtastic",
            source_id="a35b4144",
            observed_at="2026-07-25T11:30:00Z",
            latitude=43.1,
            longitude=-8.1,
            position_updated_at=(
                "2026-07-25T11:30:00Z"
            ),
        )
        included = make_observation(
            source="meshview_es",
            network="meshtastic",
            source_id="b1234567",
            observed_at="2026-07-25T11:31:00Z",
            latitude=42.9,
            longitude=-8.0,
            position_updated_at=(
                "2026-07-25T11:31:00Z"
            ),
        )
        edge = make_edge_observation(
            source="meshview_es",
            network="meshtastic",
            from_source_id="a35b4144",
            to_source_id="b1234567",
            edge_type="traceroute",
            directed=True,
            observed_at="2026-07-25T11:32:00Z",
        )

        with tempfile.TemporaryDirectory() as temporary:
            documents = build_public_documents(
                [excluded, included],
                edge_observations=[edge],
                generated_at=NOW,
                settings=self.settings(
                    Path(temporary)
                ),
                excluded_node_ids={
                    "meshtastic:!a35b4144",
                },
                configuration_warnings_source={
                    "updated": 1_753_446_000,
                    "nodes": [
                        {
                            "id": "!a35b4144",
                            "issues": [{
                                "key": "position_fixed",
                                "severity": "high",
                            }],
                        },
                        {
                            "id": "!b1234567",
                            "issues": [{
                                "key": "position_fixed",
                                "severity": "high",
                            }],
                        },
                    ],
                },
            )

        self.assertEqual(
            [
                node["id"]
                for node in documents[
                    "nodes.json"
                ]["nodes"]
            ],
            ["meshtastic:!b1234567"],
        )
        self.assertEqual(
            documents["edges.json"]["edges"],
            [],
        )
        self.assertEqual(
            documents["stats.json"]["totals"][
                "nodes"
            ],
            1,
        )
        self.assertEqual(
            documents["stats.json"]["totals"][
                "edges"
            ],
            0,
        )
        self.assertEqual(
            documents["stats.json"]["sources"][
                "meshview_es"
            ]["records_received"],
            1,
        )
        self.assertEqual(
            documents[
                "configuration-warnings.json"
            ]["analysis"]["analyzed_nodes"],
            1,
        )
        self.assertEqual(
            [
                node["id"]
                for node in documents[
                    "configuration-warnings.json"
                ]["nodes"]
            ],
            ["meshtastic:!b1234567"],
        )

    def test_edges_use_latest_observation_and_region(
        self,
    ) -> None:
        observations = [
            make_observation(
                source="malha_pt",
                network="meshtastic",
                source_id="a35b4144",
                observed_at="2026-07-25T11:30:00Z",
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
                observed_at="2026-07-25T11:31:00Z",
                latitude=42.9,
                longitude=-8.0,
                position_updated_at=(
                    "2026-07-25T11:31:00Z"
                ),
            ),
            make_observation(
                source="malha_pt",
                network="meshtastic",
                source_id="c7654321",
                observed_at="2026-07-25T11:32:00Z",
                latitude=45.0,
                longitude=-8.0,
                position_updated_at=(
                    "2026-07-25T11:32:00Z"
                ),
            ),
        ]

        earlier = make_edge_observation(
            source="malha_pt",
            network="meshtastic",
            from_source_id="a35b4144",
            to_source_id="b1234567",
            edge_type="traceroute",
            directed=True,
            observed_at="2026-07-25T10:00:00Z",
            metrics={"snr_db": 1.0},
        )
        later = make_edge_observation(
            source="malha_pt",
            network="meshtastic",
            from_source_id="a35b4144",
            to_source_id="b1234567",
            edge_type="traceroute",
            directed=True,
            observed_at="2026-07-25T11:00:00Z",
            metrics={"snr_db": 7.5},
        )
        outside_region = make_edge_observation(
            source="malha_pt",
            network="meshtastic",
            from_source_id="a35b4144",
            to_source_id="c7654321",
            edge_type="traceroute",
            directed=True,
            observed_at="2026-07-25T11:10:00Z",
        )
        missing_endpoint = make_edge_observation(
            source="malha_pt",
            network="meshtastic",
            from_source_id="a35b4144",
            to_source_id="d1111111",
            edge_type="traceroute",
            directed=True,
            observed_at="2026-07-25T11:20:00Z",
        )

        with tempfile.TemporaryDirectory() as temporary:
            documents = build_public_documents(
                observations,
                edge_observations=[
                    later,
                    outside_region,
                    earlier,
                    missing_endpoint,
                ],
                generated_at=NOW,
                settings=self.settings(
                    Path(temporary)
                ),
                region_bounds={
                    "south": 36.5,
                    "west": -10.5,
                    "north": 44.5,
                    "east": -3.5,
                },
            )

        edges = documents["edges.json"]["edges"]

        self.assertEqual(len(edges), 1)
        self.assertEqual(
            edges[0],
            {
                "id": (
                    "meshtastic:traceroute:"
                    "!a35b4144:!b1234567"
                ),
                "network": "meshtastic",
                "source": "malha_pt",
                "from_id": (
                    "meshtastic:!a35b4144"
                ),
                "to_id": (
                    "meshtastic:!b1234567"
                ),
                "edge_type": "traceroute",
                "directed": True,
                "last_seen": (
                    "2026-07-25T11:00:00Z"
                ),
                "metrics": {
                    "snr_db": 7.5,
                    "rssi_dbm": None,
                },
                "route_id": None,
                "route_index": None,
            },
        )

        self.assertEqual(
            documents["stats.json"]["totals"]["edges"],
            1,
        )
        self.assertEqual(
            documents["stats.json"]["networks"][
                "meshtastic"
            ]["edges"],
            1,
        )
        self.assertEqual(
            documents["stats.json"]["networks"][
                "meshcore"
            ]["edges"],
            0,
        )

    def test_meshcore_observed_route_identity_is_published(
        self,
    ) -> None:
        first_key = "01" * 32
        second_key = "02" * 32

        observations = [
            make_observation(
                source="meshcore_hub",
                network="meshcore",
                source_id=first_key,
                observed_at="2026-08-10T11:29:00Z",
                latitude=42.1,
                longitude=-8.1,
                position_updated_at="2026-08-10T11:29:00Z",
            ),
            make_observation(
                source="meshcore_hub",
                network="meshcore",
                source_id=second_key,
                observed_at="2026-08-10T11:29:00Z",
                latitude=42.2,
                longitude=-8.2,
                position_updated_at="2026-08-10T11:29:00Z",
            ),
        ]

        route_id = (
            "64C4F8DA7624E41C:"
            + ("ab" * 32)
            + ":2026-08-10T11:30:00Z"
        )

        edge = make_edge_observation(
            source="meshcore_hub",
            network="meshcore",
            from_source_id=first_key,
            to_source_id=second_key,
            edge_type="observed",
            directed=True,
            observed_at="2026-08-10T11:30:00Z",
            metrics={"snr_db": -4.5},
            route_id=route_id,
            route_index=0,
        )

        with tempfile.TemporaryDirectory() as temporary:
            documents = build_public_documents(
                observations,
                edge_observations=[edge],
                generated_at="2026-08-10T11:31:00Z",
                settings=self.settings(
                    Path(temporary)
                ),
                region_bounds={
                    "south": 36.5,
                    "west": -10.5,
                    "north": 44.5,
                    "east": -3.5,
                },
            )

        published = documents["edges.json"]["edges"]

        self.assertEqual(len(published), 1)
        self.assertEqual(
            published[0]["route_id"],
            route_id,
        )
        self.assertEqual(
            published[0]["route_index"],
            0,
        )

    def test_neighbor_info_is_published_as_history(
        self,
    ) -> None:
        earlier = make_neighbor_observation(
            source="ozulo_map",
            from_source_id="b03c4574",
            to_source_id="ad301dc1",
            observed_at="2026-08-03T21:38:04Z",
            snr_db=1.0,
        )
        later = make_neighbor_observation(
            source="ozulo_map",
            from_source_id="b03c4574",
            to_source_id="ad301dc1",
            observed_at="2026-08-04T03:38:05Z",
            snr_db=4.0,
        )
        excluded = make_neighbor_observation(
            source="ozulo_map",
            from_source_id="b03c4574",
            to_source_id="35982f26",
            observed_at="2026-08-04T03:38:05Z",
            snr_db=6.75,
        )

        nodes = [
            make_observation(
                source="ozulo_map",
                network="meshtastic",
                source_id="b03c4574",
                observed_at="2026-08-04T03:40:00Z",
                latitude=42.9,
                longitude=-8.0,
                position_updated_at=(
                    "2026-08-04T03:40:00Z"
                ),
            ),
            make_observation(
                source="ozulo_map",
                network="meshtastic",
                source_id="ad301dc1",
                observed_at="2026-08-04T03:40:00Z",
                latitude=42.91,
                longitude=-8.01,
                position_updated_at=(
                    "2026-08-04T03:40:00Z"
                ),
            ),
        ]

        with tempfile.TemporaryDirectory() as temporary:
            documents = build_public_documents(
                nodes,
                neighbor_observations=[
                    later,
                    earlier,
                    earlier,
                    excluded,
                ],
                generated_at=(
                    "2026-08-04T09:35:13Z"
                ),
                settings=self.settings(
                    Path(temporary)
                ),
                excluded_node_ids={
                    "meshtastic:!35982f26",
                },
            )

        self.assertEqual(
            documents["neighbor-info.json"],
            {
                "schema": "mesh-noroeste.data/v1",
                "generated_at": (
                    "2026-08-04T09:35:13Z"
                ),
                "observations": [
                    {
                        "source": "ozulo_map",
                        "network": "meshtastic",
                        "from_id": (
                            "meshtastic:!b03c4574"
                        ),
                        "to_id": (
                            "meshtastic:!ad301dc1"
                        ),
                        "observed_at": (
                            "2026-08-03T21:38:04Z"
                        ),
                        "snr_db": 1.0,
                    },
                    {
                        "source": "ozulo_map",
                        "network": "meshtastic",
                        "from_id": (
                            "meshtastic:!b03c4574"
                        ),
                        "to_id": (
                            "meshtastic:!ad301dc1"
                        ),
                        "observed_at": (
                            "2026-08-04T03:38:05Z"
                        ),
                        "snr_db": 4.0,
                    },
                ],
            },
        )

    def test_neighbor_info_requires_published_endpoints(
        self,
    ) -> None:
        nodes = [
            make_observation(
                source="ozulo_map",
                network="meshtastic",
                source_id="b03c4574",
                observed_at="2026-08-04T03:40:00Z",
                latitude=42.9,
                longitude=-8.0,
                position_updated_at=(
                    "2026-08-04T03:40:00Z"
                ),
            ),
            make_observation(
                source="ozulo_map",
                network="meshtastic",
                source_id="ad301dc1",
                observed_at="2026-08-04T03:40:00Z",
                latitude=42.91,
                longitude=-8.01,
                position_updated_at=(
                    "2026-08-04T03:40:00Z"
                ),
            ),
        ]

        valid = make_neighbor_observation(
            source="ozulo_map",
            from_source_id="b03c4574",
            to_source_id="ad301dc1",
            observed_at="2026-08-04T03:38:05Z",
            snr_db=4.0,
        )
        orphan = make_neighbor_observation(
            source="ozulo_map",
            from_source_id="b03c4574",
            to_source_id="35982f26",
            observed_at="2026-08-04T03:38:06Z",
            snr_db=6.75,
        )

        with tempfile.TemporaryDirectory() as temporary:
            documents = build_public_documents(
                nodes,
                neighbor_observations=[
                    valid,
                    orphan,
                ],
                generated_at=(
                    "2026-08-04T09:35:13Z"
                ),
                settings=self.settings(
                    Path(temporary)
                ),
            )

        observations = documents[
            "neighbor-info.json"
        ]["observations"]

        self.assertEqual(
            len(observations),
            1,
        )
        self.assertEqual(
            observations[0]["from_id"],
            "meshtastic:!b03c4574",
        )
        self.assertEqual(
            observations[0]["to_id"],
            "meshtastic:!ad301dc1",
        )


    def test_neighbor_info_rejects_wrong_objects(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                TypeError,
                "NeighborObservation",
            ):
                build_public_documents(
                    self.observations(),
                    neighbor_observations=[
                        object()
                    ],  # type: ignore[list-item]
                    generated_at=NOW,
                    settings=self.settings(
                        Path(temporary)
                    ),
                )

    def test_region_bounds_filter_nodes(
        self,
    ) -> None:
        observations = [
            make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="c1111111",
                observed_at="2026-07-25T10:00:00Z",
                latitude=43.0,
                longitude=-8.0,
                position_updated_at=(
                    "2026-07-25T10:00:00Z"
                ),
            ),
            make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="d2222222",
                observed_at="2026-07-25T10:00:00Z",
                latitude=36.5,
                longitude=-10.5,
                position_updated_at=(
                    "2026-07-25T10:00:00Z"
                ),
            ),
            make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="e3333333",
                observed_at="2026-07-25T10:00:00Z",
                latitude=45.0,
                longitude=-8.0,
                position_updated_at=(
                    "2026-07-25T10:00:00Z"
                ),
            ),
            make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="f4444444",
                observed_at="2026-07-25T10:00:00Z",
            ),
        ]

        with tempfile.TemporaryDirectory() as temporary:
            documents = build_public_documents(
                observations,
                generated_at=NOW,
                settings=self.settings(Path(temporary)),
                region_bounds={
                    "south": 36.5,
                    "west": -10.5,
                    "north": 44.5,
                    "east": -3.5,
                },
            )

        nodes = documents["nodes.json"]["nodes"]

        self.assertEqual(
            {node["id"] for node in nodes},
            {
                "meshtastic:!c1111111",
                "meshtastic:!d2222222",
            },
        )
        self.assertEqual(
            documents["stats.json"]["totals"]["nodes"],
            2,
        )
        self.assertEqual(
            documents["stats.json"]["sources"][
                "meshview_es"
            ]["records_received"],
            4,
        )

    def test_default_region_filters_operational_areas(
        self,
    ) -> None:
        observations = [
            make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="c1111111",
                observed_at="2026-07-25T10:00:00Z",
                latitude=43.0,
                longitude=-8.0,
                position_updated_at=(
                    "2026-07-25T10:00:00Z"
                ),
            ),
            make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="d2222222",
                observed_at="2026-07-25T10:00:00Z",
                latitude=40.0,
                longitude=-6.0,
                position_updated_at=(
                    "2026-07-25T10:00:00Z"
                ),
            ),
            make_observation(
                source="meshcore_map",
                network="meshcore",
                source_id="02ab34cd",
                observed_at="2026-07-25T10:00:00Z",
                node_type="repeater",
                latitude=40.0,
                longitude=-8.0,
                position_updated_at=(
                    "2026-07-25T10:00:00Z"
                ),
            ),
            make_observation(
                source="meshcore_map",
                network="meshcore",
                source_id="03ab34cd",
                observed_at="2026-07-25T10:00:00Z",
                node_type="repeater",
                latitude=45.0,
                longitude=-8.0,
                position_updated_at=(
                    "2026-07-25T10:00:00Z"
                ),
            ),
        ]

        with tempfile.TemporaryDirectory() as temporary:
            documents = build_public_documents(
                observations,
                generated_at=NOW,
                settings=self.settings(Path(temporary)),
            )

        self.assertEqual(
            {
                node["id"]
                for node in documents["nodes.json"]["nodes"]
            },
            {
                "meshtastic:!c1111111",
                "meshcore:02ab34cd",
            },
        )
        self.assertEqual(
            documents["meta.json"]["region"],
            {
                "name": DEFAULT_REGION_NAME,
                "bounds": default_region_bounds(),
            },
        )
        self.assertEqual(
            documents["stats.json"]["sources"][
                "meshview_es"
            ]["records_received"],
            2,
        )
        self.assertEqual(
            documents["stats.json"]["sources"][
                "meshcore_map"
            ]["records_received"],
            2,
        )

    def test_supplied_source_statistics_are_used(
        self,
    ) -> None:
        supplied = {
            "meshview_es": {
                "last_success": (
                    "2026-07-25T11:58:00+00:00"
                ),
                "last_error_at": None,
                "last_error": None,
                "records_received": 85,
            },
            "malha_pt": {
                "last_success": (
                    "2026-07-25T11:57:00Z"
                ),
                "last_error_at": (
                    "2026-07-24T18:12:00Z"
                ),
                "last_error": "HTTP 502 temporal",
                "records_received": 46,
            },
            "ozulo_map": {
                "last_success": (
                    "2026-07-25T11:56:00Z"
                ),
                "last_error_at": None,
                "last_error": None,
                "records_received": 64,
            },
            "meshcore_map": {
                "last_success": (
                    "2026-07-25T11:59:00Z"
                ),
                "last_error_at": None,
                "last_error": None,
                "records_received": 52326,
            },
            "meshcore_hub": {
                "last_success": (
                    "2026-07-25T11:59:30Z"
                ),
                "last_error_at": None,
                "last_error": None,
                "records_received": 75,
            },
        }

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            documents = build_public_documents(
                self.observations(),
                generated_at=NOW,
                settings=self.settings(root),
                source_statistics=supplied,
            )

        self.assertEqual(
            documents["stats.json"]["sources"],
            {
                "meshview_es": {
                    "last_success": (
                        "2026-07-25T11:58:00Z"
                    ),
                    "last_error_at": None,
                    "last_error": None,
                    "records_received": 85,
                },
                "malha_pt": {
                    "last_success": (
                        "2026-07-25T11:57:00Z"
                    ),
                    "last_error_at": (
                        "2026-07-24T18:12:00Z"
                    ),
                    "last_error": (
                        "HTTP 502 temporal"
                    ),
                    "records_received": 46,
                },
                "ozulo_map": {
                "last_success": (
                    "2026-07-25T11:56:00Z"
                ),
                "last_error_at": None,
                "last_error": None,
                "records_received": 64,
            },
            "meshcore_map": {
                    "last_success": (
                        "2026-07-25T11:59:00Z"
                    ),
                    "last_error_at": None,
                    "last_error": None,
                    "records_received": 52326,
                },
            "meshcore_hub": {
                "last_success": (
                    "2026-07-25T11:59:30Z"
                ),
                "last_error_at": None,
                "last_error": None,
                "records_received": 75,
            },
            },
        )

    def test_expired_nodes_are_omitted(
        self,
    ) -> None:
        expired = make_observation(
            source="meshview_es",
            network="meshtastic",
            source_id="b1234567",
            observed_at="2026-06-01T12:00:00Z",
        )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            documents = build_public_documents(
                [expired],
                generated_at=NOW,
                settings=self.settings(root),
            )

        self.assertEqual(
            documents["nodes.json"]["nodes"],
            [],
        )
        self.assertEqual(
            documents["stats.json"]["totals"][
                "nodes"
            ],
            0,
        )
        self.assertEqual(
            documents["stats.json"]["sources"][
                "meshview_es"
            ]["records_received"],
            1,
        )

    def test_configuration_warnings_are_published(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            documents = build_public_documents(
                self.observations(),
                generated_at=NOW,
                settings=self.settings(root),
                configuration_warnings_source={
                    "updated": 1_753_446_000,
                    "nodes": [
                        {
                            "id": "!a35b4144",
                            "issues": [
                                {
                                    "key": "position_fixed",
                                    "severity": "high",
                                }
                            ],
                        }
                    ],
                },
            )

        warnings = documents[
            "configuration-warnings.json"
        ]

        self.assertIs(
            warnings["analysis"]["available"],
            True,
        )
        self.assertEqual(
            warnings["analysis"]["eligible_nodes"],
            1,
        )
        self.assertEqual(
            warnings["analysis"]["analyzed_nodes"],
            1,
        )
        self.assertEqual(
            warnings["nodes"][0]["id"],
            "meshtastic:!a35b4144",
        )

    def test_missing_configuration_analysis_is_explicit(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            documents = build_public_documents(
                self.observations(),
                generated_at=NOW,
                settings=self.settings(root),
            )

        warnings = documents[
            "configuration-warnings.json"
        ]

        self.assertIs(
            warnings["analysis"]["available"],
            False,
        )
        self.assertEqual(
            warnings["analysis"]["eligible_nodes"],
            1,
        )
        self.assertEqual(warnings["nodes"], [])

    def test_observer_receptions_are_published(
        self,
    ) -> None:
        reception = make_observer_reception(
            source="meshcore_hub",
            node_source_id="01" * 32,
            observer_source_id="ab" * 32,
            packet_hash="338ffb499235b61f",
            observed_at="2026-08-07T10:00:00Z",
            snr_db=-6.75,
            path_len=2,
        )

        later_reception = make_observer_reception(
            source="meshcore_hub",
            node_source_id="01" * 32,
            observer_source_id="ab" * 32,
            packet_hash="338FFB499235B61F",
            observed_at="2026-08-07T10:01:00Z",
            snr_db=3.5,
            path_len=3,
        )

        excluded = make_observer_reception(
            source="meshcore_hub",
            node_source_id="02" * 32,
            observer_source_id="cd" * 32,
            packet_hash="A1B2C3D4",
            observed_at="2026-08-07T10:02:00Z",
            snr_db=None,
            path_len=None,
        )

        with tempfile.TemporaryDirectory() as temporary:
            documents = build_public_documents(
                self.observations(),
                observer_receptions=[
                    later_reception,
                    reception,
                    excluded,
                ],
                generated_at=NOW,
                settings=self.settings(
                    Path(temporary)
                ),
                excluded_node_ids={
                    "meshcore:" + ("cd" * 32),
                },
            )

        self.assertEqual(
            documents["observer-receptions.json"],
            {
                "schema": "mesh-noroeste.data/v1",
                "generated_at": NOW,
                "receptions": [
                    {
                        "source": "meshcore_hub",
                        "network": "meshcore",
                        "node_id": (
                            "meshcore:" + ("01" * 32)
                        ),
                        "observer_id": (
                            "meshcore:" + ("ab" * 32)
                        ),
                        "packet_hash": "338FFB499235B61F",
                        "observed_at": (
                            "2026-08-07T10:00:00Z"
                        ),
                        "snr_db": -6.75,
                        "path_len": 2,
                    },
                    {
                        "source": "meshcore_hub",
                        "network": "meshcore",
                        "node_id": (
                            "meshcore:" + ("01" * 32)
                        ),
                        "observer_id": (
                            "meshcore:" + ("ab" * 32)
                        ),
                        "packet_hash": "338FFB499235B61F",
                        "observed_at": (
                            "2026-08-07T10:01:00Z"
                        ),
                        "snr_db": 3.5,
                        "path_len": 3,
                    }
                ],
            },
        )


    def test_written_documents_match_schemas(
        self,
    ) -> None:
        project_root = Path(__file__).resolve().parent.parent

        schema_files = {
            "nodes.json": (
                project_root
                / "schemas/nodes-v1.schema.json"
            ),
            "edges.json": (
                project_root
                / "schemas/edges-v1.schema.json"
            ),
            "neighbor-info.json": (
                project_root
                / "schemas/neighbor-info-v1.schema.json"
            ),
            "observer-receptions.json": (
                project_root
                / "schemas/observer-receptions-v1.schema.json"
            ),
            "stats.json": (
                project_root
                / "schemas/stats-v1.schema.json"
            ),
            "meta.json": (
                project_root
                / "schemas/meta-v1.schema.json"
            ),
            "configuration-warnings.json": (
                project_root
                / "schemas/configuration-warnings-v1.schema.json"
            ),
        }

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            edge = make_edge_observation(
                source="meshview_es",
                network="meshtastic",
                from_source_id="a35b4144",
                to_source_id="b1234567",
                edge_type="traceroute",
                directed=True,
                observed_at="2026-07-25T11:30:00Z",
            )

            documents = build_public_documents(
                self.observations(),
                edge_observations=[edge],
                generated_at=NOW,
                settings=self.settings(root),
            )

            output = root / "frontend" / "data"

            written = write_public_documents(
                output,
                documents,
            )

            self.assertEqual(
                [path.name for path in written],
                list(PUBLIC_DOCUMENT_NAMES),
            )

            manifest = json.loads(
                (
                    output
                    / PUBLIC_MANIFEST_NAME
                ).read_text(encoding="utf-8")
            )

            self.assertEqual(
                manifest["schema"],
                PUBLIC_MANIFEST_SCHEMA,
            )
            self.assertEqual(
                manifest["generated_at"],
                NOW,
            )
            self.assertEqual(
                set(manifest["documents"]),
                set(PUBLIC_DOCUMENT_NAMES),
            )

            temporary_files = (
                list(output.glob(".*.tmp"))
                + list(
                    (
                        output
                        / PUBLIC_GENERATIONS_DIRECTORY
                    ).glob(".tmp-*")
                )
            )

            self.assertEqual(
                temporary_files,
                [],
            )

            for filename, schema_path in (
                schema_files.items()
            ):
                document_path = (
                    output
                    / manifest["documents"][filename]
                )

                self.assertTrue(
                    document_path.is_file()
                )

                self.assertEqual(
                    stat.S_IMODE(
                        document_path.stat().st_mode
                    ),
                    0o644,
                )

                document = json.loads(
                    document_path.read_text(
                        encoding="utf-8"
                    )
                )

                schema = json.loads(
                    schema_path.read_text(
                        encoding="utf-8"
                    )
                )

                validator = Draft202012Validator(
                    schema,
                    format_checker=FormatChecker(),
                )

                errors = list(
                    validator.iter_errors(
                        document
                    )
                )

                self.assertEqual(
                    errors,
                    [],
                    msg=(
                        f"{filename}: "
                        + "; ".join(
                            error.message
                            for error in errors
                        )
                    ),
                )

    def test_failed_generation_keeps_previous_documents(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "public"

            old_documents = {
                filename: {
                    "generated_at": NOW,
                    "generation": "old",
                }
                for filename in PUBLIC_DOCUMENT_NAMES
            }

            write_public_documents(
                output,
                old_documents,
            )

            old_manifest = json.loads(
                (
                    output
                    / PUBLIC_MANIFEST_NAME
                ).read_text(encoding="utf-8")
            )

            new_documents = {
                filename: {
                    "generated_at": (
                        "2026-07-25T13:00:00Z"
                    ),
                    "generation": "new",
                }
                for filename in PUBLIC_DOCUMENT_NAMES
            }
            new_documents["stats.json"][
                "invalid"
            ] = object()

            with self.assertRaises(TypeError):
                write_public_documents(
                    output,
                    new_documents,
                )

            current_manifest = json.loads(
                (
                    output
                    / PUBLIC_MANIFEST_NAME
                ).read_text(encoding="utf-8")
            )

            self.assertEqual(
                current_manifest,
                old_manifest,
            )

            generations = {
                filename: json.loads(
                    (
                        output
                        / current_manifest[
                            "documents"
                        ][filename]
                    ).read_text(encoding="utf-8")
                )["generation"]
                for filename in PUBLIC_DOCUMENT_NAMES
            }

            self.assertEqual(
                set(generations.values()),
                {"old"},
            )

    def test_prune_failure_warns_after_publication(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "public"

            write_public_documents(
                output,
                {
                    filename: {
                        "generated_at": NOW,
                        "generation": "old",
                    }
                    for filename in PUBLIC_DOCUMENT_NAMES
                },
            )

            old_manifest = json.loads(
                (
                    output
                    / PUBLIC_MANIFEST_NAME
                ).read_text(encoding="utf-8")
            )

            new_generated_at = (
                "2026-07-25T13:00:00Z"
            )

            with patch(
                (
                    "mesh_noroeste.publication."
                    "_prune_public_generations"
                ),
                side_effect=OSError(
                    "fallo simulado no prune"
                ),
            ):
                with self.assertWarnsRegex(
                    RuntimeWarning,
                    (
                        "La publicación quedó activa, "
                        "pero no se pudieron limpiar"
                    ),
                ):
                    written = write_public_documents(
                        output,
                        {
                            filename: {
                                "generated_at": (
                                    new_generated_at
                                ),
                                "generation": "new",
                            }
                            for filename
                            in PUBLIC_DOCUMENT_NAMES
                        },
                    )

            current_manifest = json.loads(
                (
                    output
                    / PUBLIC_MANIFEST_NAME
                ).read_text(encoding="utf-8")
            )

            self.assertNotEqual(
                current_manifest["generation"],
                old_manifest["generation"],
            )
            self.assertEqual(
                current_manifest["generated_at"],
                new_generated_at,
            )
            self.assertTrue(
                all(path.is_file() for path in written)
            )

            generations = {
                candidate.name
                for candidate in (
                    output
                    / PUBLIC_GENERATIONS_DIRECTORY
                ).iterdir()
                if candidate.is_dir()
            }

            self.assertIn(
                old_manifest["generation"],
                generations,
            )
            self.assertIn(
                current_manifest["generation"],
                generations,
            )

    def test_old_generations_are_pruned_safely(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "public"

            for index in range(
                PUBLIC_GENERATIONS_TO_KEEP + 3
            ):
                generated_at = (
                    "2026-07-25T12:"
                    f"{index:02d}:00Z"
                )

                documents = {
                    filename: {
                        "generated_at": generated_at,
                        "index": index,
                    }
                    for filename in PUBLIC_DOCUMENT_NAMES
                }

                write_public_documents(
                    output,
                    documents,
                )

            manifest = json.loads(
                (
                    output
                    / PUBLIC_MANIFEST_NAME
                ).read_text(encoding="utf-8")
            )

            generations_path = (
                output
                / PUBLIC_GENERATIONS_DIRECTORY
            )
            generations = [
                candidate
                for candidate in generations_path.iterdir()
                if candidate.is_dir()
            ]

            self.assertEqual(
                len(generations),
                PUBLIC_GENERATIONS_TO_KEEP,
            )
            self.assertEqual(
                (
                    generations_path
                    / ".publication.lock"
                ).stat().st_mode & 0o777,
                0o600,
            )

            for filename in PUBLIC_DOCUMENT_NAMES:
                self.assertTrue(
                    (
                        output
                        / manifest["documents"][filename]
                    ).is_file()
                )


if __name__ == "__main__":
    unittest.main()
