"""Pruebas de la persistencia SQLite."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
import re
import sqlite3
import tempfile
import unittest

from mesh_noroeste import storage as storage_module
from mesh_noroeste.domain import (
    make_edge_observation,
    make_neighbor_observation,
    make_observation,
    make_observer_reception,
    merge_observations,
)
from mesh_noroeste.storage import (
    ObservationStore,
    SCHEMA_VERSION,
)


class ObservationStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )

        root = Path(
            self.temporary_directory.name
        )

        self.database_path = (
            root
            / "state"
            / "mesh-noroeste.db"
        )

        self.store = ObservationStore(
            self.database_path
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def meshtastic_observation(
        self,
        *,
        source: str = "meshview_es",
        observed_at: str = "2026-07-25T10:00:00Z",
    ):
        return make_observation(
            source=source,
            network="meshtastic",
            source_id="a35b4144",
            observed_at=observed_at,
            first_seen="2026-07-20T09:00:00Z",
            short_name="BRUMA",
            long_name="Bruma Connection",
            hardware="HELTEC_V4",
            role="CLIENT_MUTE",
            latitude=43.1,
            longitude=-8.1,
            altitude_m=120,
            position_precision_bits=14,
            position_updated_at=observed_at,
            metrics={
                "battery_percent": 76,
                "voltage_v": 4.02,
                "snr_db": 7.25,
                "rssi_dbm": -91,
            },
            radio={
                "channel": "LongFast",
                "firmware": "2.x",
                "hops_away": 2,
                "mqtt_gateway": False,
            },
        )

    def test_initialize_creates_valid_database(
        self,
    ) -> None:
        self.store.initialize()

        self.assertTrue(
            self.database_path.is_file()
        )
        self.assertEqual(
            self.store.schema_version(),
            SCHEMA_VERSION,
        )
        self.assertEqual(
            self.store.quick_check(),
            "ok",
        )
        self.assertEqual(
            self.store.journal_mode().lower(),
            "wal",
        )

    def test_observation_round_trip(self) -> None:
        observation = self.meshtastic_observation()

        inserted = self.store.save(
            [observation]
        )

        loaded = self.store.load(
            observation.id
        )

        self.assertEqual(inserted, 1)
        self.assertEqual(loaded, [observation])
        self.assertEqual(self.store.count(), 1)

    def test_duplicate_observation_is_ignored(
        self,
    ) -> None:
        observation = self.meshtastic_observation()

        first_insert = self.store.save(
            [observation]
        )
        second_insert = self.store.save(
            [observation]
        )

        self.assertEqual(first_insert, 1)
        self.assertEqual(second_insert, 0)
        self.assertEqual(self.store.count(), 1)

    def test_same_node_accepts_multiple_sources(
        self,
    ) -> None:
        meshview = self.meshtastic_observation(
            source="meshview_es",
            observed_at="2026-07-25T10:00:00Z",
        )

        malha = self.meshtastic_observation(
            source="malha_pt",
            observed_at="2026-07-25T11:00:00Z",
        )

        inserted = self.store.save(
            [malha, meshview]
        )

        loaded = self.store.load(
            meshview.id
        )

        self.assertEqual(inserted, 2)
        self.assertEqual(len(loaded), 2)
        self.assertEqual(
            [item.source for item in loaded],
            ["meshview_es", "malha_pt"],
        )
        self.assertEqual(
            self.store.count(),
            2,
        )

    def test_load_all_returns_every_observation(
        self,
    ) -> None:
        later_meshtastic = self.meshtastic_observation(
            source="malha_pt",
            observed_at="2026-07-25T11:00:00Z",
        )

        earlier_meshtastic = self.meshtastic_observation(
            source="meshview_es",
            observed_at="2026-07-25T10:00:00Z",
        )

        meshcore = make_observation(
            source="meshcore_map",
            network="meshcore",
            source_id="02ab34cd",
            observed_at="2026-07-25T09:00:00Z",
            node_type="repeater",
        )

        inserted = self.store.save(
            [
                later_meshtastic,
                meshcore,
                earlier_meshtastic,
            ]
        )

        loaded = self.store.load_all()

        self.assertEqual(inserted, 3)
        self.assertEqual(
            loaded,
            [
                meshcore,
                earlier_meshtastic,
                later_meshtastic,
            ],
        )


    def test_load_for_publication_preserves_consolidation(
        self,
    ) -> None:
        old_details = make_observation(
            source="meshview_es",
            network="meshtastic",
            source_id="a35b4144",
            observed_at="2026-07-20T09:00:00Z",
            first_seen="2026-07-10T08:00:00Z",
            short_name="BRUMA",
            role="CLIENT_MUTE",
            metrics={
                "battery_percent": 80,
                "snr_db": 4.5,
            },
            radio={
                "channel": "LongFast",
                "firmware": "2.5.0",
            },
        )
        irrelevant_history = make_observation(
            source="meshview_es",
            network="meshtastic",
            source_id="a35b4144",
            observed_at="2026-07-21T09:00:00Z",
        )
        latest_meshview = make_observation(
            source="meshview_es",
            network="meshtastic",
            source_id="a35b4144",
            observed_at="2026-07-25T10:00:00Z",
            latitude=43.1,
            longitude=-8.1,
            position_updated_at="2026-07-25T09:30:00Z",
        )
        latest_node = make_observation(
            source="malha_pt",
            network="meshtastic",
            source_id="a35b4144",
            observed_at="2026-07-25T11:00:00Z",
            long_name="Bruma actualizada",
            metrics={
                "voltage_v": 4.1,
            },
        )

        observations = [
            latest_node,
            irrelevant_history,
            old_details,
            latest_meshview,
        ]

        self.assertEqual(
            self.store.save(observations),
            4,
        )

        complete = self.store.load_all()
        reduced = self.store.load_for_publication()

        self.assertEqual(len(complete), 4)
        self.assertEqual(len(reduced), 3)
        self.assertNotIn(irrelevant_history, reduced)

        complete_node = merge_observations(
            complete,
            now="2026-07-25T12:00:00Z",
            active_hours=24,
            recent_days=7,
            historical_days=30,
        )
        reduced_node = merge_observations(
            reduced,
            now="2026-07-25T12:00:00Z",
            active_hours=24,
            recent_days=7,
            historical_days=30,
        )

        self.assertEqual(reduced_node, complete_node)

    def test_load_for_publication_keeps_nodes_separate(
        self,
    ) -> None:
        first = self.meshtastic_observation()
        second = make_observation(
            source="meshcore_map",
            network="meshcore",
            source_id="02ab34cd",
            observed_at="2026-07-25T11:00:00Z",
            node_type="repeater",
        )

        self.assertEqual(
            self.store.save([first, second]),
            2,
        )
        self.assertEqual(
            self.store.load_for_publication(),
            [second, first],
        )

    def test_load_for_publication_on_empty_database(
        self,
    ) -> None:
        self.assertEqual(
            self.store.load_for_publication(),
            [],
        )

    def test_load_all_on_empty_database(
        self,
    ) -> None:
        self.assertEqual(
            self.store.load_all(),
            [],
        )

    def test_different_nodes_remain_separate(
        self,
    ) -> None:
        first = self.meshtastic_observation()

        second = make_observation(
            source="meshcore_map",
            network="meshcore",
            source_id="02ab34cd",
            observed_at="2026-07-25T11:00:00Z",
            node_type="repeater",
        )

        inserted = self.store.save(
            [first, second]
        )

        self.assertEqual(inserted, 2)
        self.assertEqual(self.store.count(), 2)
        self.assertEqual(
            self.store.load(first.id),
            [first],
        )
        self.assertEqual(
            self.store.load(second.id),
            [second],
        )


class EdgeObservationStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        self.database_path = (
            Path(self.temporary_directory.name)
            / "edge-observations.db"
        )
        self.store = ObservationStore(
            self.database_path
        )

    def traceroute(
        self,
        *,
        observed_at: str = "2026-07-25T12:00:00Z",
    ):
        return make_edge_observation(
            source="malha_pt",
            network="meshtastic",
            from_source_id="a35b4144",
            to_source_id="c7654321",
            edge_type="traceroute",
            directed=True,
            observed_at=observed_at,
            metrics={
                "snr_db": 7.5,
            },
        )

    def test_edge_round_trip(self) -> None:
        edge = self.traceroute()

        inserted = self.store.save_edges([edge])
        loaded = self.store.load_all_edges()

        self.assertEqual(inserted, 1)
        self.assertEqual(loaded, [edge])
        self.assertEqual(
            self.store.count_edges(),
            1,
        )

    def test_duplicate_edge_is_ignored(self) -> None:
        edge = self.traceroute()

        first = self.store.save_edges([edge])
        second = self.store.save_edges([edge])

        self.assertEqual(first, 1)
        self.assertEqual(second, 0)
        self.assertEqual(
            self.store.count_edges(),
            1,
        )

    def test_same_edge_accepts_new_observation(
        self,
    ) -> None:
        earlier = self.traceroute(
            observed_at="2026-07-25T11:00:00Z",
        )
        later = self.traceroute(
            observed_at="2026-07-25T12:00:00Z",
        )

        inserted = self.store.save_edges(
            [later, earlier]
        )

        self.assertEqual(inserted, 2)
        self.assertEqual(
            self.store.load_all_edges(),
            [earlier, later],
        )

    def test_replace_edges_updates_only_received_ids(
        self,
    ) -> None:
        previous = make_edge_observation(
            source="meshview_es",
            network="meshtastic",
            from_source_id="a35b4144",
            to_source_id="b1234567",
            edge_type="traceroute",
            directed=True,
            observed_at="2026-07-25T11:00:00Z",
        )
        omitted = make_edge_observation(
            source="meshview_es",
            network="meshtastic",
            from_source_id="a35b4144",
            to_source_id="d1111111",
            edge_type="traceroute",
            directed=True,
            observed_at="2026-07-25T11:30:00Z",
        )
        current = make_edge_observation(
            source="meshview_es",
            network="meshtastic",
            from_source_id="a35b4144",
            to_source_id="b1234567",
            edge_type="traceroute",
            directed=True,
            observed_at="2026-07-25T12:00:00Z",
            metrics={"snr_db": 7.5},
        )
        malha = self.traceroute()

        self.store.save_edges(
            [previous, omitted, malha]
        )

        inserted = self.store.replace_edges(
            "meshview_es",
            [current],
        )
        loaded = self.store.load_all_edges()

        self.assertEqual(inserted, 1)
        self.assertCountEqual(
            [
                edge
                for edge in loaded
                if edge.source == "meshview_es"
            ],
            [omitted, current],
        )
        self.assertEqual(
            [
                edge
                for edge in loaded
                if edge.source == "malha_pt"
            ],
            [malha],
        )

    def test_replace_edges_accepts_empty_snapshot(
        self,
    ) -> None:
        meshview = make_edge_observation(
            source="meshview_es",
            network="meshtastic",
            from_source_id="a35b4144",
            to_source_id="b1234567",
            edge_type="neighbor",
            directed=False,
            observed_at="2026-07-25T11:00:00Z",
        )
        malha = self.traceroute()

        self.store.save_edges([meshview, malha])

        inserted = self.store.replace_edges(
            "meshview_es",
            [],
        )

        self.assertEqual(inserted, 0)
        self.assertCountEqual(
            self.store.load_all_edges(),
            [meshview, malha],
        )

    def test_empty_edge_store(self) -> None:
        self.assertEqual(
            self.store.load_all_edges(),
            [],
        )
        self.assertEqual(
            self.store.count_edges(),
            0,
        )

    def test_non_edge_object_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "EdgeObservation",
        ):
            self.store.save_edges(
                [object()]  # type: ignore[list-item]
            )


class NeighborObservationStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        self.store = ObservationStore(
            Path(self.temporary_directory.name)
            / "neighbor-observations.db"
        )

    def observation(
        self,
        *,
        observed_at: str = "2026-08-04T08:41:13Z",
        snr_db: float = 4.0,
    ):
        return make_neighbor_observation(
            source="ozulo_map",
            from_source_id="b03c4574",
            to_source_id="ad301dc1",
            observed_at=observed_at,
            snr_db=snr_db,
        )

    def test_neighbor_round_trip(self) -> None:
        observation = self.observation()

        inserted = self.store.save_neighbors(
            [observation]
        )

        self.assertEqual(inserted, 1)
        self.assertEqual(
            self.store.load_all_neighbors(),
            [observation],
        )
        self.assertEqual(
            self.store.count_neighbors(),
            1,
        )

    def test_duplicate_neighbor_is_ignored(self) -> None:
        observation = self.observation()

        self.assertEqual(
            self.store.save_neighbors([observation]),
            1,
        )
        self.assertEqual(
            self.store.save_neighbors([observation]),
            0,
        )
        self.assertEqual(
            self.store.count_neighbors(),
            1,
        )

    def test_neighbor_history_is_preserved(self) -> None:
        earlier = self.observation(
            observed_at="2026-08-04T07:00:00Z",
            snr_db=1.0,
        )
        later = self.observation(
            observed_at="2026-08-04T08:00:00Z",
            snr_db=6.5,
        )

        self.assertEqual(
            self.store.save_neighbors([later, earlier]),
            2,
        )
        self.assertEqual(
            self.store.load_all_neighbors(),
            [earlier, later],
        )

    def test_empty_neighbor_store(self) -> None:
        self.assertEqual(
            self.store.load_all_neighbors(),
            [],
        )
        self.assertEqual(
            self.store.count_neighbors(),
            0,
        )

    def test_non_neighbor_object_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "NeighborObservation",
        ):
            self.store.save_neighbors(
                [object()]  # type: ignore[list-item]
            )


class ObserverReceptionStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        self.store = ObservationStore(
            Path(self.temporary_directory.name)
            / "observer-receptions.db"
        )

    def reception(
        self,
        *,
        packet_hash: str = "338FFB499235B61F",
        observed_at: str = "2026-08-07T07:10:57Z",
        snr_db: float | None = -6.75,
        path_len: int | None = 2,
    ):
        return make_observer_reception(
            source="meshcore_hub",
            node_source_id="01" * 32,
            observer_source_id="ab" * 32,
            packet_hash=packet_hash,
            observed_at=observed_at,
            snr_db=snr_db,
            path_len=path_len,
        )

    def test_observer_reception_round_trip(self) -> None:
        reception = self.reception()

        self.assertEqual(
            self.store.save_observer_receptions(
                [reception]
            ),
            1,
        )
        self.assertEqual(
            self.store.load_all_observer_receptions(),
            [reception],
        )
        self.assertEqual(
            self.store.count_observer_receptions(),
            1,
        )

    def test_duplicate_reception_is_ignored(self) -> None:
        reception = self.reception()

        self.assertEqual(
            self.store.save_observer_receptions(
                [reception]
            ),
            1,
        )
        self.assertEqual(
            self.store.save_observer_receptions(
                [reception]
            ),
            0,
        )

    def test_same_packet_and_observer_at_different_times_is_preserved(
        self,
    ) -> None:
        first = self.reception()
        second = self.reception(
            observed_at="2026-08-08T07:10:57Z",
            snr_db=-2.5,
        )

        self.assertEqual(
            self.store.save_observer_receptions(
                [second, first]
            ),
            2,
        )
        self.assertEqual(
            self.store.load_all_observer_receptions(),
            [first, second],
        )

    def test_same_packet_from_two_observers_is_preserved(
        self,
    ) -> None:
        first = self.reception()
        second = make_observer_reception(
            source="meshcore_hub",
            node_source_id="01" * 32,
            observer_source_id="cd" * 32,
            packet_hash=first.packet_hash,
            observed_at="2026-08-07T07:10:58Z",
            snr_db=3.5,
        )

        self.assertEqual(
            self.store.save_observer_receptions(
                [second, first]
            ),
            2,
        )
        self.assertEqual(
            self.store.load_all_observer_receptions(),
            [first, second],
        )

    def test_same_observer_can_receive_different_packets(
        self,
    ) -> None:
        first = self.reception()
        second = self.reception(
            packet_hash="6875CFA7269E0AE0",
            observed_at="2026-08-07T07:11:57Z",
        )

        self.assertEqual(
            self.store.save_observer_receptions(
                [second, first]
            ),
            2,
        )
        self.assertEqual(
            self.store.load_all_observer_receptions(),
            [first, second],
        )

    def test_empty_observer_reception_store(self) -> None:
        self.assertEqual(
            self.store.load_all_observer_receptions(),
            [],
        )
        self.assertEqual(
            self.store.count_observer_receptions(),
            0,
        )

    def test_non_reception_object_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "ObserverReception",
        ):
            self.store.save_observer_receptions(
                [object()]  # type: ignore[list-item]
            )


class SchemaMigrationTests(unittest.TestCase):
    def test_version_one_database_is_migrated(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = (
                Path(directory) / "migration.db"
            )
            store = ObservationStore(database_path)

            node = make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="a35b4144",
                observed_at="2026-07-25T10:00:00Z",
            )

            store.save([node])

            with closing(
                sqlite3.connect(database_path)
            ) as connection:
                with connection:
                    connection.execute(
                        "DROP TABLE edge_observations"
                    )
                    connection.execute(
                        "PRAGMA user_version = 1"
                    )

            store.initialize()

            self.assertEqual(
                store.schema_version(),
                SCHEMA_VERSION,
            )
            self.assertEqual(
                store.load_all(),
                [node],
            )
            self.assertEqual(
                store.load_all_edges(),
                [],
            )
            self.assertEqual(
                store.quick_check(),
                "ok",
            )

            edge = make_edge_observation(
                source="malha_pt",
                network="meshtastic",
                from_source_id="a35b4144",
                to_source_id="b1234567",
                edge_type="traceroute",
                directed=True,
                observed_at="2026-07-25T11:00:00Z",
            )

            self.assertEqual(
                store.save_edges([edge]),
                1,
            )
            self.assertEqual(
                store.load_all_edges(),
                [edge],
            )

    def test_version_two_database_adds_position_precision(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = (
                Path(directory) / "migration-v2.db"
            )
            store = ObservationStore(database_path)

            legacy = make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="a35b4144",
                observed_at="2026-07-25T10:00:00Z",
                latitude=43.1,
                longitude=-8.1,
                position_precision_bits=14,
                position_updated_at="2026-07-25T10:00:00Z",
            )

            store.save([legacy])

            with closing(
                sqlite3.connect(database_path)
            ) as connection:
                with connection:
                    connection.execute(
                        """
                        ALTER TABLE node_observations
                        DROP COLUMN position_precision_bits
                        """
                    )
                    connection.execute(
                        "PRAGMA user_version = 2"
                    )

            store.initialize()

            with closing(
                sqlite3.connect(database_path)
            ) as connection:
                columns = {
                    row[1]
                    for row in connection.execute(
                        """
                        PRAGMA table_info(
                            node_observations
                        )
                        """
                    )
                }

            self.assertIn(
                "position_precision_bits",
                columns,
            )
            self.assertEqual(
                store.schema_version(),
                SCHEMA_VERSION,
            )
            self.assertIsNone(
                store.load_all()[0].position_precision_bits
            )

            precise = make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="a35b4144",
                observed_at="2026-07-25T11:00:00Z",
                latitude=43.1,
                longitude=-8.1,
                position_precision_bits=18,
                position_updated_at="2026-07-25T11:00:00Z",
            )

            self.assertEqual(store.save([precise]), 1)
            self.assertEqual(
                store.load_all()[-1].position_precision_bits,
                18,
            )
            self.assertEqual(store.quick_check(), "ok")

    def test_version_three_database_adds_ozulo_source(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = (
                Path(directory) / "migration-v3.db"
            )
            store = ObservationStore(database_path)

            existing_node = make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="a35b4144",
                observed_at="2026-07-25T10:00:00Z",
            )
            existing_edge = make_edge_observation(
                source="malha_pt",
                network="meshtastic",
                from_source_id="a35b4144",
                to_source_id="b1234567",
                edge_type="traceroute",
                directed=True,
                observed_at="2026-07-25T10:01:00Z",
            )

            store.save([existing_node])
            store.save_edges([existing_edge])

            existing_run = store.begin_source_run(
                "meshview_es",
                "2026-07-25T09:59:00Z",
            )
            store.finish_source_run(
                existing_run,
                finished_at="2026-07-25T10:02:00Z",
                success=True,
                records_received=1,
            )

            with closing(
                sqlite3.connect(database_path)
            ) as connection:
                connection.row_factory = sqlite3.Row

                with connection:
                    for table in (
                        "node_observations",
                        "edge_observations",
                        "source_runs",
                    ):
                        row = connection.execute(
                            """
                            SELECT sql
                            FROM sqlite_master
                            WHERE type = 'table'
                              AND name = ?
                            """,
                            (table,),
                        ).fetchone()

                        self.assertIsNotNone(row)
                        assert row is not None

                        create_sql = row["sql"]
                        temporary = f"{table}_v3"

                        legacy_sql = create_sql.replace(
                            "'ozulo_map',",
                            "",
                            1,
                        )
                        legacy_sql = legacy_sql.replace(
                            f"CREATE TABLE {table}",
                            f"CREATE TABLE {temporary}",
                            1,
                        )

                        columns = [
                            item["name"]
                            for item in connection.execute(
                                f"PRAGMA table_info({table})"
                            )
                        ]
                        column_list = ", ".join(
                            f'"{column}"'
                            for column in columns
                        )

                        connection.execute(legacy_sql)
                        connection.execute(
                            f"""
                            INSERT INTO "{temporary}" (
                                {column_list}
                            )
                            SELECT
                                {column_list}
                            FROM "{table}"
                            """
                        )
                        connection.execute(
                            f'DROP TABLE "{table}"'
                        )
                        connection.execute(
                            f"""
                            ALTER TABLE "{temporary}"
                            RENAME TO "{table}"
                            """
                        )

                    connection.execute(
                        "PRAGMA user_version = 3"
                    )

            store.initialize()

            self.assertEqual(
                store.schema_version(),
                SCHEMA_VERSION,
            )
            self.assertEqual(
                store.load_all(),
                [existing_node],
            )
            self.assertEqual(
                store.load_all_edges(),
                [existing_edge],
            )
            self.assertEqual(
                store.source_statistics()[
                    "meshview_es"
                ]["records_received"],
                1,
            )

            with closing(
                sqlite3.connect(database_path)
            ) as connection:
                table_sql = {
                    row[0]: row[1]
                    for row in connection.execute(
                        """
                        SELECT name, sql
                        FROM sqlite_master
                        WHERE type = 'table'
                          AND name IN (
                              'node_observations',
                              'edge_observations',
                              'source_runs'
                          )
                        """
                    )
                }

            for sql in table_sql.values():
                self.assertIn("'ozulo_map'", sql)

            ozulo_node = make_observation(
                source="ozulo_map",
                network="meshtastic",
                source_id="0406a2f0",
                observed_at="2026-07-29T11:16:57Z",
            )
            ozulo_edge = make_edge_observation(
                source="ozulo_map",
                network="meshtastic",
                from_source_id="0406a2f0",
                to_source_id="1ba27088",
                edge_type="traceroute",
                directed=True,
                observed_at="2026-07-29T11:16:57Z",
            )

            self.assertEqual(
                store.save([ozulo_node]),
                1,
            )
            self.assertEqual(
                store.save_edges([ozulo_edge]),
                1,
            )

            ozulo_run = store.begin_source_run(
                "ozulo_map",
                "2026-07-29T12:00:00Z",
            )
            store.finish_source_run(
                ozulo_run,
                finished_at="2026-07-29T12:01:00Z",
                success=True,
                records_received=2,
            )

            self.assertEqual(
                store.source_statistics()["ozulo_map"],
                {
                    "last_success": (
                        "2026-07-29T12:01:00Z"
                    ),
                    "last_error_at": None,
                    "last_error": None,
                    "records_received": 2,
                },
            )
            self.assertEqual(store.quick_check(), "ok")

    def test_version_four_database_adds_retention_cursors(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = (
                Path(directory) / "migration-v4.db"
            )
            store = ObservationStore(database_path)

            old_node = make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="a35b4144",
                observed_at="2026-05-01T10:00:00Z",
            )
            old_edge = make_edge_observation(
                source="malha_pt",
                network="meshtastic",
                from_source_id="a35b4144",
                to_source_id="b1234567",
                edge_type="traceroute",
                directed=True,
                observed_at="2026-05-01T11:00:00Z",
            )

            self.assertEqual(
                store.save([old_node]),
                1,
            )
            self.assertEqual(
                store.save_edges([old_edge]),
                1,
            )

            with closing(
                sqlite3.connect(database_path)
            ) as connection:
                with connection:
                    connection.execute(
                        "DROP TABLE node_observation_cursors"
                    )
                    connection.execute(
                        "DROP TABLE edge_observation_cursors"
                    )
                    connection.execute(
                        "PRAGMA user_version = 4"
                    )

            store.initialize()

            self.assertEqual(
                store.schema_version(),
                SCHEMA_VERSION,
            )

            with closing(
                sqlite3.connect(database_path)
            ) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        """
                        SELECT name
                        FROM sqlite_master
                        WHERE type = 'table'
                        """
                    )
                }
                node_cursors = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM node_observation_cursors
                    """
                ).fetchone()[0]
                edge_cursors = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM edge_observation_cursors
                    """
                ).fetchone()[0]

            self.assertIn(
                "node_observation_cursors",
                tables,
            )
            self.assertIn(
                "edge_observation_cursors",
                tables,
            )
            self.assertEqual(node_cursors, 1)
            self.assertEqual(edge_cursors, 1)

            deleted = store.prune(
                "2026-07-01T00:00:00Z"
            )

            self.assertEqual(
                deleted["node_observations"],
                1,
            )
            self.assertEqual(
                deleted["edge_observations"],
                1,
            )
            self.assertEqual(
                store.load_all(),
                [],
            )
            self.assertEqual(
                store.load_all_edges(),
                [],
            )
            self.assertEqual(
                store.save([old_node]),
                0,
            )
            self.assertEqual(
                store.save_edges([old_edge]),
                0,
            )
            self.assertEqual(store.quick_check(), "ok")

    def test_version_six_database_adds_meshcore_hub(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = (
                Path(directory) / "migration-v6.db"
            )
            store = ObservationStore(database_path)

            existing_node = make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="a35b4144",
                observed_at="2026-08-05T08:00:00Z",
            )
            existing_edge = make_edge_observation(
                source="malha_pt",
                network="meshtastic",
                from_source_id="a35b4144",
                to_source_id="b1234567",
                edge_type="traceroute",
                directed=True,
                observed_at="2026-08-05T08:01:00Z",
            )

            self.assertEqual(
                store.save([existing_node]),
                1,
            )
            self.assertEqual(
                store.save_edges([existing_edge]),
                1,
            )

            existing_run = store.begin_source_run(
                "meshview_es",
                "2026-08-05T07:59:00Z",
            )
            store.finish_source_run(
                existing_run,
                finished_at="2026-08-05T08:02:00Z",
                success=True,
                records_received=1,
            )

            with closing(
                sqlite3.connect(database_path)
            ) as connection:
                connection.row_factory = sqlite3.Row

                with connection:
                    for table in (
                        "node_observations",
                        "edge_observations",
                        "node_observation_cursors",
                        "edge_observation_cursors",
                        "source_runs",
                    ):
                        row = connection.execute(
                            """
                            SELECT sql
                            FROM sqlite_master
                            WHERE type = 'table'
                              AND name = ?
                            """,
                            (table,),
                        ).fetchone()

                        self.assertIsNotNone(row)
                        assert row is not None

                        legacy_sql, replacements = re.subn(
                            r",\s*'meshcore_hub'",
                            "",
                            row["sql"],
                            count=1,
                        )

                        self.assertEqual(replacements, 1)

                        temporary = f"{table}_v6"
                        quoted_table = (
                            storage_module._quote_identifier(
                                table
                            )
                        )
                        quoted_temporary = (
                            storage_module._quote_identifier(
                                temporary
                            )
                        )

                        temporary_sql, renamed = (
                            storage_module
                            ._CREATE_TABLE_HEAD
                            .subn(
                                (
                                    "CREATE TABLE "
                                    f"{quoted_temporary}"
                                ),
                                legacy_sql,
                                count=1,
                            )
                        )

                        self.assertEqual(renamed, 1)
                        connection.execute(temporary_sql)

                        columns = [
                            item["name"]
                            for item in connection.execute(
                                (
                                    "PRAGMA table_info("
                                    f"{quoted_table}"
                                    ")"
                                )
                            )
                        ]
                        column_list = ", ".join(
                            storage_module
                            ._quote_identifier(column)
                            for column in columns
                        )

                        connection.execute(
                            f"""
                            INSERT INTO {quoted_temporary} (
                                {column_list}
                            )
                            SELECT
                                {column_list}
                            FROM {quoted_table}
                            """
                        )
                        connection.execute(
                            f"DROP TABLE {quoted_table}"
                        )
                        connection.execute(
                            f"""
                            ALTER TABLE {quoted_temporary}
                            RENAME TO {quoted_table}
                            """
                        )

                    connection.execute(
                        "PRAGMA user_version = 6"
                    )

            store.initialize()

            self.assertEqual(
                store.schema_version(),
                SCHEMA_VERSION,
            )
            self.assertEqual(
                store.load_all(),
                [existing_node],
            )
            self.assertEqual(
                store.load_all_edges(),
                [existing_edge],
            )

            with closing(
                sqlite3.connect(database_path)
            ) as connection:
                table_sql = {
                    row[0]: row[1]
                    for row in connection.execute(
                        """
                        SELECT name, sql
                        FROM sqlite_master
                        WHERE type = 'table'
                          AND name IN (
                              'node_observations',
                              'edge_observations',
                              'node_observation_cursors',
                              'edge_observation_cursors',
                              'source_runs'
                          )
                        """
                    )
                }
                cursor_index = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM sqlite_master
                    WHERE type = 'index'
                      AND name = ?
                    """,
                    (
                        "idx_edge_observation_"
                        "cursors_endpoints",
                    ),
                ).fetchone()[0]

            self.assertEqual(len(table_sql), 5)
            self.assertEqual(cursor_index, 1)

            for sql in table_sql.values():
                self.assertIn(
                    "'meshcore_hub'",
                    sql,
                )

            hub_node = make_observation(
                source="meshcore_hub",
                network="meshcore",
                source_id="a" * 64,
                observed_at="2026-08-05T09:00:00Z",
                node_type="client",
                is_observer=True,
            )
            hub_edge = make_edge_observation(
                source="meshcore_hub",
                network="meshcore",
                from_source_id="a" * 64,
                to_source_id="b" * 64,
                edge_type="observed",
                directed=True,
                observed_at="2026-08-05T09:01:00Z",
                metrics={
                    "snr_db": 8.5,
                },
            )

            self.assertEqual(
                store.save([hub_node]),
                1,
            )
            self.assertEqual(
                store.load(hub_node.id),
                [hub_node],
            )
            self.assertEqual(
                store.save_edges([hub_edge]),
                1,
            )

            hub_run = store.begin_source_run(
                "meshcore_hub",
                "2026-08-05T08:59:00Z",
            )
            store.finish_source_run(
                hub_run,
                finished_at="2026-08-05T09:02:00Z",
                success=True,
                records_received=2,
            )

            self.assertEqual(
                store.source_statistics()[
                    "meshcore_hub"
                ],
                {
                    "last_success": (
                        "2026-08-05T09:02:00Z"
                    ),
                    "last_error_at": None,
                    "last_error": None,
                    "records_received": 2,
                },
            )
            self.assertEqual(store.quick_check(), "ok")

    def test_unknown_schema_version_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = (
                Path(directory) / "future.db"
            )

            with closing(
                sqlite3.connect(database_path)
            ) as connection:
                with connection:
                    connection.execute(
                        "PRAGMA user_version = 99"
                    )

            store = ObservationStore(database_path)

            with self.assertRaisesRegex(
                RuntimeError,
                "Versión SQLite incompatible",
            ):
                store.initialize()



    def test_version_nine_database_updates_reception_identity(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = (
                Path(directory) / "migration-v9.db"
            )
            store = ObservationStore(database_path)

            first = make_observer_reception(
                source="meshcore_hub",
                node_source_id="01" * 32,
                observer_source_id="02" * 32,
                packet_hash="338FFB499235B61F",
                observed_at="2026-08-07T07:10:57Z",
                snr_db=-6.75,
            )

            self.assertEqual(
                store.save_observer_receptions([first]),
                1,
            )

            with closing(
                sqlite3.connect(database_path)
            ) as connection:
                with connection:
                    connection.execute(
                        """
                        CREATE TABLE observer_receptions_v9 (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            source TEXT NOT NULL
                                CHECK (
                                    source = 'meshcore_hub'
                                ),
                            node_source_id TEXT NOT NULL,
                            observer_source_id TEXT NOT NULL,
                            packet_hash TEXT NOT NULL,
                            observed_at TEXT NOT NULL,
                            snr_db REAL,
                            path_len INTEGER
                                CHECK (
                                    path_len IS NULL
                                    OR path_len >= 0
                                ),
                            inserted_at TEXT NOT NULL,
                            UNIQUE (
                                source,
                                node_source_id,
                                observer_source_id,
                                packet_hash
                            )
                        )
                        """
                    )
                    connection.execute(
                        """
                        INSERT INTO observer_receptions_v9
                        SELECT *
                        FROM observer_receptions
                        """
                    )
                    connection.execute(
                        "DROP TABLE observer_receptions"
                    )
                    connection.execute(
                        """
                        ALTER TABLE observer_receptions_v9
                        RENAME TO observer_receptions
                        """
                    )
                    connection.execute(
                        "PRAGMA user_version = 9"
                    )

            store.initialize()

            second = make_observer_reception(
                source="meshcore_hub",
                node_source_id="01" * 32,
                observer_source_id="02" * 32,
                packet_hash="338FFB499235B61F",
                observed_at="2026-08-08T07:10:57Z",
                snr_db=-2.5,
            )

            self.assertEqual(
                store.save_observer_receptions([second]),
                1,
            )
            self.assertEqual(
                store.load_all_observer_receptions(),
                [first, second],
            )
            self.assertEqual(
                store.schema_version(),
                SCHEMA_VERSION,
            )
            self.assertEqual(store.quick_check(), "ok")

    def test_version_eight_database_adds_observer_receptions(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = (
                Path(directory) / "migration-v8.db"
            )
            store = ObservationStore(database_path)

            existing = make_observation(
                source="meshcore_hub",
                network="meshcore",
                source_id="01" * 32,
                observed_at="2026-08-07T07:00:00Z",
                is_observer=False,
            )

            self.assertEqual(store.save([existing]), 1)

            with closing(
                sqlite3.connect(database_path)
            ) as connection:
                with connection:
                    connection.execute(
                        "DROP TABLE observer_receptions"
                    )
                    connection.execute(
                        "PRAGMA user_version = 8"
                    )

            store.initialize()

            self.assertEqual(
                store.schema_version(),
                SCHEMA_VERSION,
            )
            self.assertEqual(
                store.load_all(),
                [existing],
            )
            self.assertEqual(
                store.load_all_observer_receptions(),
                [],
            )

            reception = make_observer_reception(
                source="meshcore_hub",
                node_source_id="01" * 32,
                observer_source_id="02" * 32,
                packet_hash="338FFB499235B61F",
                observed_at="2026-08-07T07:10:57Z",
                snr_db=-6.75,
            )

            self.assertEqual(
                store.save_observer_receptions(
                    [reception]
                ),
                1,
            )
            self.assertEqual(
                store.load_all_observer_receptions(),
                [reception],
            )
            self.assertEqual(store.quick_check(), "ok")


class NodePurgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database_path = (
            self.root / "mesh-noroeste.db"
        )
        self.store = ObservationStore(
            self.database_path
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def node(
        self,
        source_id: str,
        *,
        source: str = "malha_pt",
        observed_at: str = "2026-07-25T12:00:00Z",
    ):
        return make_observation(
            source=source,
            network="meshtastic",
            source_id=source_id,
            observed_at=observed_at,
        )

    def edge(
        self,
        from_source_id: str,
        to_source_id: str,
    ):
        return make_edge_observation(
            source="malha_pt",
            network="meshtastic",
            from_source_id=from_source_id,
            to_source_id=to_source_id,
            edge_type="traceroute",
            directed=True,
            observed_at="2026-07-25T12:05:00Z",
        )

    def neighbor(
        self,
        from_source_id: str,
        to_source_id: str,
        *,
        observed_at: str = "2026-07-25T12:06:00Z",
    ):
        return make_neighbor_observation(
            source="ozulo_map",
            from_source_id=from_source_id,
            to_source_id=to_source_id,
            observed_at=observed_at,
            snr_db=4.0,
        )

    def test_purge_removes_all_sources_and_incident_edges(
        self,
    ) -> None:
        target_malha = self.node(
            "a35b4144",
            source="malha_pt",
            observed_at="2026-07-25T12:00:00Z",
        )
        target_meshview = self.node(
            "!A35B4144",
            source="meshview_es",
            observed_at="2026-07-25T12:01:00Z",
        )
        node_b = self.node(
            "b1234567",
            observed_at="2026-07-25T12:02:00Z",
        )
        node_c = self.node(
            "c7654321",
            observed_at="2026-07-25T12:03:00Z",
        )
        incident = self.edge(
            "a35b4144",
            "b1234567",
        )
        unrelated = self.edge(
            "b1234567",
            "c7654321",
        )

        self.assertEqual(
            self.store.save([
                target_malha,
                target_meshview,
                node_b,
                node_c,
            ]),
            4,
        )
        self.assertEqual(
            self.store.save_edges([
                incident,
                unrelated,
            ]),
            2,
        )

        result = self.store.purge_node(
            " MESHTASTIC:!A35B4144 "
        )

        self.assertEqual(
            result.node_observations_deleted,
            2,
        )
        self.assertEqual(
            result.edge_observations_deleted,
            1,
        )
        self.assertEqual(
            self.store.load(
                "meshtastic:!a35b4144"
            ),
            [],
        )
        self.assertEqual(
            [
                observation.id
                for observation in self.store.load_all()
            ],
            [
                "meshtastic:!b1234567",
                "meshtastic:!c7654321",
            ],
        )

        remaining_edges = (
            self.store.load_all_edges()
        )

        self.assertEqual(
            len(remaining_edges),
            1,
        )
        self.assertEqual(
            remaining_edges[0].from_id,
            "meshtastic:!b1234567",
        )
        self.assertEqual(
            remaining_edges[0].to_id,
            "meshtastic:!c7654321",
        )

    def test_purge_removes_incident_neighbor_observations(
        self,
    ) -> None:
        target = self.node("a35b4144")
        node_b = self.node("b1234567")
        node_c = self.node("c7654321")

        incoming = self.neighbor(
            "b1234567",
            "a35b4144",
        )
        outgoing = self.neighbor(
            "a35b4144",
            "c7654321",
        )
        unrelated = self.neighbor(
            "b1234567",
            "c7654321",
            observed_at="2026-07-25T12:07:00Z",
        )

        self.assertEqual(
            self.store.save([
                target,
                node_b,
                node_c,
            ]),
            3,
        )
        self.assertEqual(
            self.store.save_neighbors([
                incoming,
                outgoing,
                unrelated,
            ]),
            3,
        )

        self.store.purge_node(
            "meshtastic:!a35b4144"
        )

        self.assertEqual(
            self.store.load_all_neighbors(),
            [unrelated],
        )

    def test_purge_missing_node_returns_zero_counts(
        self,
    ) -> None:
        result = self.store.purge_node(
            "meshtastic:!a35b4144"
        )

        self.assertEqual(
            result.node_observations_deleted,
            0,
        )
        self.assertEqual(
            result.edge_observations_deleted,
            0,
        )

    def test_purge_validates_canonical_identifier(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "canonical_id debe ser texto",
        ):
            self.store.purge_node(123)

        with self.assertRaisesRegex(
            ValueError,
            "prefijo de red",
        ):
            self.store.purge_node("!a35b4144")

        with self.assertRaisesRegex(
            ValueError,
            "Red no admitida",
        ):
            self.store.purge_node(
                "otra:!a35b4144"
            )

    def test_purge_removes_associated_cursors(
        self,
    ) -> None:
        target = self.node("a35b4144")
        other = self.node("b1234567")
        incident = self.edge(
            "a35b4144",
            "b1234567",
        )

        self.assertEqual(
            self.store.save([target, other]),
            2,
        )
        self.assertEqual(
            self.store.save_edges([incident]),
            1,
        )

        self.store.purge_node(
            "meshtastic:!a35b4144"
        )

        with closing(
            sqlite3.connect(
                self.database_path
            )
        ) as connection:
            node_cursors = connection.execute(
                """
                SELECT COUNT(*)
                FROM node_observation_cursors
                WHERE canonical_id =
                    'meshtastic:!a35b4144'
                """
            ).fetchone()[0]
            edge_cursors = connection.execute(
                """
                SELECT COUNT(*)
                FROM edge_observation_cursors
                WHERE network = 'meshtastic'
                  AND (
                      from_source_id = '!a35b4144'
                      OR to_source_id = '!a35b4144'
                  )
                """
            ).fetchone()[0]

        self.assertEqual(node_cursors, 0)
        self.assertEqual(edge_cursors, 0)

    def test_purge_is_atomic_when_node_delete_fails(
        self,
    ) -> None:
        target = self.node("a35b4144")
        other = self.node("b1234567")
        incident = self.edge(
            "a35b4144",
            "b1234567",
        )

        self.assertEqual(
            self.store.save([target, other]),
            2,
        )
        self.assertEqual(
            self.store.save_edges([incident]),
            1,
        )

        connection = sqlite3.connect(
            self.database_path
        )

        try:
            connection.execute(
                """
                CREATE TRIGGER block_target_node_delete
                BEFORE DELETE ON node_observations
                WHEN OLD.canonical_id =
                    'meshtastic:!a35b4144'
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'borrado bloqueado'
                    );
                END
                """
            )
            connection.commit()
        finally:
            connection.close()

        with self.assertRaisesRegex(
            sqlite3.IntegrityError,
            "borrado bloqueado",
        ):
            self.store.purge_node(
                "meshtastic:!a35b4144"
            )

        self.assertEqual(
            len(
                self.store.load(
                    "meshtastic:!a35b4144"
                )
            ),
            1,
        )
        self.assertEqual(
            self.store.count_edges(),
            1,
        )


class RetentionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        self.store = ObservationStore(
            Path(self.temporary_directory.name)
            / "retention.db"
        )

    def node(
        self,
        *,
        source: str,
        source_id: str,
        observed_at: str,
    ):
        return make_observation(
            source=source,
            network=(
                "meshcore"
                if source == "meshcore_map"
                else "meshtastic"
            ),
            source_id=source_id,
            observed_at=observed_at,
        )

    def test_prune_deletes_all_expired_nodes_and_uses_cursor(
        self,
    ) -> None:
        expired = [
            self.node(
                source="meshcore_map",
                source_id="01ab",
                observed_at="2026-05-01T10:00:00Z",
            ),
            self.node(
                source="meshcore_map",
                source_id="01ab",
                observed_at="2026-05-02T10:00:00Z",
            ),
        ]
        supporting_old = self.node(
            source="meshview_es",
            source_id="a35b4144",
            observed_at="2026-05-01T10:00:00Z",
        )
        current = self.node(
            source="malha_pt",
            source_id="a35b4144",
            observed_at="2026-07-25T10:00:00Z",
        )

        self.store.save(
            expired + [supporting_old, current]
        )

        deleted = self.store.prune(
            "2026-07-01T00:00:00Z"
        )

        self.assertEqual(
            deleted["node_observations"],
            3,
        )
        self.assertEqual(
            self.store.load_all(),
            [current],
        )

        self.assertEqual(
            self.store.save([expired[1]]),
            0,
        )
        self.assertEqual(
            self.store.load_all(),
            [current],
        )


    def test_prune_deletes_all_expired_edges_and_uses_cursor(
        self,
    ) -> None:
        old = make_edge_observation(
            source="malha_pt",
            network="meshtastic",
            from_source_id="a35b4144",
            to_source_id="b1234567",
            edge_type="traceroute",
            directed=True,
            observed_at="2026-05-01T10:00:00Z",
        )
        latest_old = make_edge_observation(
            source="malha_pt",
            network="meshtastic",
            from_source_id="a35b4144",
            to_source_id="b1234567",
            edge_type="traceroute",
            directed=True,
            observed_at="2026-05-02T10:00:00Z",
        )
        single_old = make_edge_observation(
            source="malha_pt",
            network="meshtastic",
            from_source_id="a35b4144",
            to_source_id="c7654321",
            edge_type="traceroute",
            directed=True,
            observed_at="2026-05-03T10:00:00Z",
        )
        recent = make_edge_observation(
            source="malha_pt",
            network="meshtastic",
            from_source_id="a35b4144",
            to_source_id="d1111111",
            edge_type="traceroute",
            directed=True,
            observed_at="2026-07-25T10:00:00Z",
        )

        self.store.save_edges(
            [old, latest_old, single_old, recent]
        )

        deleted = self.store.prune(
            "2026-07-01T00:00:00Z"
        )

        self.assertEqual(
            deleted["edge_observations"],
            3,
        )
        self.assertEqual(
            self.store.load_all_edges(),
            [recent],
        )
        self.assertEqual(
            self.store.save_edges([latest_old]),
            0,
        )
        self.assertEqual(
            self.store.load_all_edges(),
            [recent],
        )


    def test_replace_edges_does_not_restore_pruned_snapshot(
        self,
    ) -> None:
        old_edge = make_edge_observation(
            source="ozulo_map",
            network="meshtastic",
            from_source_id="a35b4144",
            to_source_id="b1234567",
            edge_type="traceroute",
            directed=True,
            observed_at="2026-05-01T10:00:00Z",
        )

        self.assertEqual(
            self.store.replace_edges(
                "ozulo_map",
                [old_edge],
            ),
            1,
        )

        deleted = self.store.prune(
            "2026-07-01T00:00:00Z"
        )

        self.assertEqual(
            deleted["edge_observations"],
            1,
        )
        self.assertEqual(
            self.store.load_all_edges(),
            [],
        )
        self.assertEqual(
            self.store.replace_edges(
                "ozulo_map",
                [old_edge],
            ),
            0,
        )
        self.assertEqual(
            self.store.load_all_edges(),
            [],
        )

    def test_prune_preserves_latest_success_and_error(
        self,
    ) -> None:
        run_ids = []

        for started_at, success in (
            ("2026-05-01T10:00:00Z", True),
            ("2026-05-02T10:00:00Z", True),
            ("2026-05-03T10:00:00Z", False),
            ("2026-05-04T10:00:00Z", False),
        ):
            run_id = self.store.begin_source_run(
                "malha_pt",
                started_at,
            )
            self.store.finish_source_run(
                run_id,
                finished_at=started_at,
                success=success,
                records_received=(
                    1 if success else 0
                ),
                error_message=(
                    None
                    if success
                    else "Error de prueba"
                ),
            )
            run_ids.append(run_id)

        unfinished = self.store.begin_source_run(
            "malha_pt",
            "2026-05-05T10:00:00Z",
        )

        deleted = self.store.prune(
            "2026-07-01T00:00:00Z"
        )

        self.assertEqual(
            deleted["source_runs"],
            3,
        )

        with closing(
            sqlite3.connect(
                self.store.database_path
            )
        ) as connection:
            remaining = {
                row[0]
                for row in connection.execute(
                    "SELECT id FROM source_runs"
                )
            }

        self.assertEqual(
            remaining,
            {
                run_ids[1],
                run_ids[3],
            },
        )
        self.assertNotIn(unfinished, remaining)


class ConnectionLifecycleTests(unittest.TestCase):
    def test_open_connection_is_closed_after_context(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = (
                Path(directory) / "connection.db"
            )

            with storage_module._open_connection(
                database_path
            ) as connection:
                result = connection.execute(
                    "SELECT 1"
                ).fetchone()[0]

                self.assertEqual(result, 1)

            with self.assertRaisesRegex(
                sqlite3.ProgrammingError,
                "closed database",
            ):
                connection.execute("SELECT 1")


class SourceRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        self.store = ObservationStore(
            Path(self.temporary_directory.name)
            / "source-runs.db"
        )

    def test_successful_run_is_reported(
        self,
    ) -> None:
        run_id = self.store.begin_source_run(
            "meshcore_map",
            "2026-07-25T11:58:00Z",
        )

        self.store.finish_source_run(
            run_id,
            finished_at="2026-07-25T12:00:00Z",
            success=True,
            records_received=52326,
        )

        statistics = self.store.source_statistics()

        self.assertEqual(
            statistics["meshcore_map"],
            {
                "last_success": "2026-07-25T12:00:00Z",
                "last_error_at": None,
                "last_error": None,
                "records_received": 52326,
            },
        )

    def test_failure_preserves_previous_success(
        self,
    ) -> None:
        successful_run = self.store.begin_source_run(
            "malha_pt",
            "2026-07-25T10:00:00Z",
        )
        self.store.finish_source_run(
            successful_run,
            finished_at="2026-07-25T10:01:00Z",
            success=True,
            records_received=46,
        )

        failed_run = self.store.begin_source_run(
            "malha_pt",
            "2026-07-25T11:00:00Z",
        )
        self.store.finish_source_run(
            failed_run,
            finished_at="2026-07-25T11:01:00Z",
            success=False,
            error_message="HTTP 502 temporal",
        )

        statistics = self.store.source_statistics()

        self.assertEqual(
            statistics["malha_pt"],
            {
                "last_success": "2026-07-25T10:01:00Z",
                "last_error_at": "2026-07-25T11:01:00Z",
                "last_error": "HTTP 502 temporal",
                "records_received": 46,
            },
        )

    def test_unfinished_run_is_ignored(
        self,
    ) -> None:
        self.store.begin_source_run(
            "meshview_es",
            "2026-07-25T12:00:00Z",
        )

        self.assertEqual(
            self.store.source_statistics()[
                "meshview_es"
            ],
            {
                "last_success": None,
                "last_error_at": None,
                "last_error": None,
                "records_received": 0,
            },
        )

    def test_completion_validation(
        self,
    ) -> None:
        run_id = self.store.begin_source_run(
            "meshcore_map",
            "2026-07-25T12:00:00Z",
        )

        with self.assertRaisesRegex(
            ValueError,
            "correcta no puede incluir",
        ):
            self.store.finish_source_run(
                run_id,
                finished_at="2026-07-25T12:01:00Z",
                success=True,
                error_message="error incoherente",
            )

        with self.assertRaisesRegex(
            ValueError,
            "fallida debe incluir",
        ):
            self.store.finish_source_run(
                run_id,
                finished_at="2026-07-25T12:01:00Z",
                success=False,
            )

        with self.assertRaisesRegex(
            ValueError,
            "anterior",
        ):
            self.store.finish_source_run(
                run_id,
                finished_at="2026-07-25T11:59:00Z",
                success=False,
                error_message="fallo",
            )

    def test_finished_run_cannot_be_finished_again(
        self,
    ) -> None:
        run_id = self.store.begin_source_run(
            "meshcore_map",
            "2026-07-25T12:00:00Z",
        )

        self.store.finish_source_run(
            run_id,
            finished_at="2026-07-25T12:01:00Z",
            success=True,
            records_received=10,
        )

        with self.assertRaisesRegex(
            ValueError,
            "ya está finalizada",
        ):
            self.store.finish_source_run(
                run_id,
                finished_at="2026-07-25T12:02:00Z",
                success=True,
                records_received=10,
            )


if __name__ == "__main__":
    unittest.main()
