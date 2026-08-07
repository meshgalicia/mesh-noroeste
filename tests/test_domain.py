"""Pruebas del modelo y consolidación de observaciones."""

from __future__ import annotations

import unittest

from mesh_noroeste.domain import (
    classify_temporal_status,
    make_edge_observation,
    make_neighbor_observation,
    make_observation,
    make_observer_reception,
    merge_observations,
)


NOW = "2026-07-25T12:00:00Z"


class ObservationTests(unittest.TestCase):
    def test_meshtastic_observation_is_normalized(
        self,
    ) -> None:
        observation = make_observation(
            source="meshview_es",
            network="Meshtastic",
            source_id="A35B4144",
            observed_at=NOW,
            short_name=" BRUMA ",
            latitude="43.1",
            longitude="-8.1",
            position_precision_bits="18",
            position_updated_at=NOW,
        )

        self.assertEqual(
            observation.id,
            "meshtastic:!a35b4144",
        )
        self.assertEqual(
            observation.source_id,
            "!a35b4144",
        )
        self.assertEqual(
            observation.short_name,
            "BRUMA",
        )
        self.assertEqual(
            observation.position_precision_bits,
            18,
        )

    def test_incompatible_source_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "no es una fuente MeshCore",
        ):
            make_observation(
                source="meshview_es",
                network="meshcore",
                source_id="02ab34cd",
                observed_at=NOW,
            )

    def test_meshcore_hub_observation_is_accepted(
        self,
    ) -> None:
        observation = make_observation(
            source="meshcore_hub",
            network="meshcore",
            source_id="02ab34cd",
            observed_at=NOW,
            node_type="repeater",
            is_observer=True,
        )

        self.assertEqual(
            observation.source,
            "meshcore_hub",
        )
        self.assertEqual(
            observation.id,
            "meshcore:02ab34cd",
        )
        self.assertIs(observation.is_observer, True)

    def test_meshtastic_observer_flag_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "no puede tener is_observer",
        ):
            make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="a35b4144",
                observed_at=NOW,
                is_observer=False,
            )

    def test_meshcore_hub_cannot_produce_meshtastic(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "no es una fuente Meshtastic",
        ):
            make_observation(
                source="meshcore_hub",
                network="meshtastic",
                source_id="a35b4144",
                observed_at=NOW,
            )

    def test_meshcore_hub_edge_is_accepted(
        self,
    ) -> None:
        observation = make_edge_observation(
            source="meshcore_hub",
            network="meshcore",
            from_source_id="02ab34cd",
            to_source_id="03ef5678",
            edge_type="observed",
            directed=False,
            observed_at=NOW,
            metrics={
                "snr_db": -4.25,
            },
        )

        self.assertEqual(
            observation.source,
            "meshcore_hub",
        )
        self.assertEqual(
            observation.metrics["snr_db"],
            -4.25,
        )

    def test_position_requires_timestamp(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "position_updated_at",
        ):
            make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="a35b4144",
                observed_at=NOW,
                latitude=43.1,
                longitude=-8.1,
            )

    def test_position_precision_requires_coordinates(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "requiere coordenadas",
        ):
            make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="a35b4144",
                observed_at=NOW,
                position_precision_bits=18,
            )

    def test_position_precision_above_32_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "no puede superar 32",
        ):
            make_observation(
                source="meshview_es",
                network="meshtastic",
                source_id="a35b4144",
                observed_at=NOW,
                latitude=43.1,
                longitude=-8.1,
                position_precision_bits=33,
                position_updated_at=NOW,
            )

    def test_meshcore_role_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "no puede tener role",
        ):
            make_observation(
                source="meshcore_map",
                network="meshcore",
                source_id="02ab34cd",
                observed_at=NOW,
                role="CLIENT",
            )

    def test_unknown_meshcore_type_is_added(
        self,
    ) -> None:
        observation = make_observation(
            source="meshcore_map",
            network="meshcore",
            source_id="02AB34CD",
            observed_at=NOW,
        )

        self.assertEqual(
            observation.node_type,
            "unknown",
        )


    def test_meshcore_radio_parameters_are_normalized(
        self,
    ) -> None:
        observation = make_observation(
            source="meshcore_map",
            network="meshcore",
            source_id=(
                "01000001536ea2117cf0050aace872f1"
                "cce17c4c06000000000000007c31b993"
            ),
            observed_at="2026-07-25T12:00:00Z",
            node_type="repeater",
            radio={
                "frequency_mhz": "869.618",
                "bandwidth_khz": "62.5",
                "spreading_factor": "8",
                "coding_rate": 8,
            },
        )

        self.assertEqual(
            observation.radio["frequency_mhz"],
            869.618,
        )
        self.assertEqual(
            observation.radio["bandwidth_khz"],
            62.5,
        )
        self.assertEqual(
            observation.radio["spreading_factor"],
            8,
        )
        self.assertEqual(
            observation.radio["coding_rate"],
            8,
        )


class TemporalStatusTests(unittest.TestCase):
    def classify(self, last_seen: str) -> str | None:
        return classify_temporal_status(
            last_seen,
            now=NOW,
            active_hours=24,
            recent_days=7,
            historical_days=30,
        )

    def test_active_boundary(self) -> None:
        self.assertEqual(
            self.classify(
                "2026-07-24T12:00:00Z"
            ),
            "active",
        )

    def test_recent_boundary(self) -> None:
        self.assertEqual(
            self.classify(
                "2026-07-18T12:00:00Z"
            ),
            "recent",
        )

    def test_historical_boundary(self) -> None:
        self.assertEqual(
            self.classify(
                "2026-06-25T12:00:00Z"
            ),
            "historical",
        )

    def test_expired_node(self) -> None:
        self.assertIsNone(
            self.classify(
                "2026-06-24T12:00:00Z"
            )
        )

    def test_future_clock_skew_is_active(self) -> None:
        self.assertEqual(
            self.classify(
                "2026-07-25T12:05:00Z"
            ),
            "active",
        )


class MergeTests(unittest.TestCase):
    def test_sources_are_consolidated_without_null_loss(
        self,
    ) -> None:
        older = make_observation(
            source="meshview_es",
            network="meshtastic",
            source_id="a35b4144",
            observed_at="2026-07-25T10:00:00Z",
            first_seen="2026-07-20T09:00:00Z",
            short_name="BRUMA",
            long_name="Nombre anterior",
            role="CLIENT_MUTE",
            latitude=43.1,
            longitude=-8.1,
            altitude_m=120,
            position_precision_bits=14,
            position_updated_at=(
                "2026-07-25T09:50:00Z"
            ),
            metrics={
                "battery_percent": 80,
                "snr_db": 6.5,
            },
            radio={
                "channel": "LongFast",
                "hops_away": 2,
            },
        )

        newer = make_observation(
            source="malha_pt",
            network="meshtastic",
            source_id="!A35B4144",
            observed_at="2026-07-25T11:00:00Z",
            long_name="Nombre actualizado",
            hardware="HELTEC_V4",
            metrics={
                "battery_percent": None,
                "voltage_v": 4.1,
            },
            radio={
                "channel": None,
                "firmware": "2.x",
            },
        )

        node = merge_observations(
            [newer, older],
            now=NOW,
            active_hours=24,
            recent_days=7,
            historical_days=30,
        )

        self.assertIsNotNone(node)
        assert node is not None

        self.assertEqual(
            node["id"],
            "meshtastic:!a35b4144",
        )
        self.assertEqual(
            node["sources"],
            ["meshview_es", "malha_pt"],
        )
        self.assertEqual(
            node["source_ids"],
            {
                "meshview_es": "!a35b4144",
                "malha_pt": "!a35b4144",
            },
        )
        self.assertEqual(
            node["source_last_seen"],
            {
                "meshview_es": "2026-07-25T10:00:00Z",
                "malha_pt": "2026-07-25T11:00:00Z",
            },
        )
        self.assertEqual(
            node["short_name"],
            "BRUMA",
        )
        self.assertEqual(
            node["long_name"],
            "Nombre actualizado",
        )
        self.assertEqual(
            node["hardware"],
            "HELTEC_V4",
        )
        self.assertEqual(
            node["role"],
            "CLIENT_MUTE",
        )
        self.assertEqual(
            node["first_seen"],
            "2026-07-20T09:00:00Z",
        )
        self.assertEqual(
            node["last_seen"],
            "2026-07-25T11:00:00Z",
        )
        self.assertEqual(
            node["latitude"],
            43.1,
        )
        self.assertEqual(
            node["longitude"],
            -8.1,
        )
        self.assertEqual(
            node["altitude_m"],
            120.0,
        )
        self.assertEqual(
            node["position_precision_bits"],
            14,
        )
        self.assertEqual(
            node["metrics"]["battery_percent"],
            80.0,
        )
        self.assertEqual(
            node["metrics"]["voltage_v"],
            4.1,
        )
        self.assertEqual(
            node["radio"]["channel"],
            "LongFast",
        )
        self.assertEqual(
            node["radio"]["firmware"],
            "2.x",
        )
        self.assertTrue(
            node["status"]["active"]
        )
        self.assertTrue(
            node["status"]["has_position"]
        )

    def test_newest_position_wins_independently(
        self,
    ) -> None:
        newer_observation = make_observation(
            source="meshview_es",
            network="meshtastic",
            source_id="a35b4144",
            observed_at="2026-07-25T11:30:00Z",
            latitude=43.0,
            longitude=-8.0,
            position_precision_bits=18,
            position_updated_at=(
                "2026-07-25T09:00:00Z"
            ),
        )

        newer_position = make_observation(
            source="malha_pt",
            network="meshtastic",
            source_id="a35b4144",
            observed_at="2026-07-25T11:00:00Z",
            latitude=44.0,
            longitude=-9.0,
            position_precision_bits=13,
            position_updated_at=(
                "2026-07-25T10:30:00Z"
            ),
        )

        node = merge_observations(
            [newer_observation, newer_position],
            now=NOW,
            active_hours=24,
            recent_days=7,
            historical_days=30,
        )

        self.assertIsNotNone(node)
        assert node is not None

        self.assertEqual(node["latitude"], 44.0)
        self.assertEqual(node["longitude"], -9.0)
        self.assertEqual(
            node["position_updated_at"],
            "2026-07-25T10:30:00Z",
        )
        self.assertEqual(
            node["position_precision_bits"],
            13,
        )

    def test_different_nodes_cannot_be_merged(
        self,
    ) -> None:
        first = make_observation(
            source="meshview_es",
            network="meshtastic",
            source_id="a35b4144",
            observed_at=NOW,
        )

        second = make_observation(
            source="meshview_es",
            network="meshtastic",
            source_id="b1234567",
            observed_at=NOW,
        )

        with self.assertRaisesRegex(
            ValueError,
            "nodos diferentes",
        ):
            merge_observations(
                [first, second],
                now=NOW,
                active_hours=24,
                recent_days=7,
                historical_days=30,
            )

    def test_expired_node_is_not_published(
        self,
    ) -> None:
        observation = make_observation(
            source="meshview_es",
            network="meshtastic",
            source_id="a35b4144",
            observed_at="2026-06-01T12:00:00Z",
        )

        node = merge_observations(
            [observation],
            now=NOW,
            active_hours=24,
            recent_days=7,
            historical_days=30,
        )

        self.assertIsNone(node)


class NeighborObservationTests(unittest.TestCase):
    def test_neighbor_info_is_normalized(self) -> None:
        observation = make_neighbor_observation(
            source=" OZULO_MAP ",
            from_source_id=2956739956,
            to_source_id=2905611713,
            observed_at="2026-08-04T08:41:13+00:00",
            snr_db="4.0",
        )

        self.assertEqual(observation.source, "ozulo_map")
        self.assertEqual(
            observation.from_source_id,
            "!b03c4574",
        )
        self.assertEqual(
            observation.to_source_id,
            "!ad301dc1",
        )
        self.assertEqual(
            observation.from_id,
            "meshtastic:!b03c4574",
        )
        self.assertEqual(
            observation.to_id,
            "meshtastic:!ad301dc1",
        )
        self.assertEqual(
            observation.id,
            (
                "meshtastic:neighbor_info:"
                "!b03c4574:!ad301dc1"
            ),
        )
        self.assertEqual(
            observation.observed_at,
            "2026-08-04T08:41:13Z",
        )
        self.assertEqual(observation.snr_db, 4.0)

    def test_neighbor_info_preserves_direction(self) -> None:
        observation = make_neighbor_observation(
            source="ozulo_map",
            from_source_id="b03c4574",
            to_source_id="16d157e4",
            observed_at=NOW,
            snr_db=6.5,
        )

        self.assertEqual(
            observation.from_source_id,
            "!b03c4574",
        )
        self.assertEqual(
            observation.to_source_id,
            "!16d157e4",
        )

    def test_neighbor_info_rejects_self_observation(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "propio nodo emisor",
        ):
            make_neighbor_observation(
                source="ozulo_map",
                from_source_id="b03c4574",
                to_source_id="!B03C4574",
                observed_at=NOW,
                snr_db=4.0,
            )

    def test_neighbor_info_requires_snr(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "snr_db é obrigatorio",
        ):
            make_neighbor_observation(
                source="ozulo_map",
                from_source_id="b03c4574",
                to_source_id="ad301dc1",
                observed_at=NOW,
                snr_db=None,
            )


class ObserverReceptionTests(unittest.TestCase):
    def test_valid_reception_is_normalized(
        self,
    ) -> None:
        reception = make_observer_reception(
            source=" meshcore_hub ",
            node_source_id="01" * 32,
            observer_source_id="AB" * 32,
            packet_hash=" 338ffb499235b61f ",
            observed_at="2026-08-07T07:10:57.369025Z",
            snr_db=-6.75,
            path_len=2,
        )

        self.assertEqual(
            reception.node_id,
            "meshcore:" + ("01" * 32),
        )
        self.assertEqual(
            reception.observer_id,
            "meshcore:" + ("ab" * 32),
        )
        self.assertEqual(
            reception.packet_hash,
            "338FFB499235B61F",
        )
        self.assertEqual(
            reception.observed_at,
            "2026-08-07T07:10:57Z",
        )
        self.assertEqual(reception.snr_db, -6.75)
        self.assertEqual(reception.path_len, 2)
        self.assertEqual(
            reception.id,
            (
                "meshcore:observer_reception:"
                + ("01" * 32)
                + ":"
                + ("ab" * 32)
                + ":338FFB499235B61F:"
                + "2026-08-07T07:10:57Z"
            ),
        )

    def test_missing_optional_metrics_are_valid(
        self,
    ) -> None:
        reception = make_observer_reception(
            source="meshcore_hub",
            node_source_id="01" * 32,
            observer_source_id="02" * 32,
            packet_hash="A1B2C3D4",
            observed_at=NOW,
        )

        self.assertIsNone(reception.snr_db)
        self.assertIsNone(reception.path_len)

    def test_non_hub_source_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "só poden proceder de meshcore_hub",
        ):
            make_observer_reception(
                source="meshcore_map",
                node_source_id="01" * 32,
                observer_source_id="02" * 32,
                packet_hash="A1B2C3D4",
                observed_at=NOW,
            )

    def test_negative_path_length_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "path_len no puede ser menor que 0",
        ):
            make_observer_reception(
                source="meshcore_hub",
                node_source_id="01" * 32,
                observer_source_id="02" * 32,
                packet_hash="A1B2C3D4",
                observed_at=NOW,
                path_len=-1,
            )

    def test_empty_packet_hash_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "packet_hash non pode estar baleiro",
        ):
            make_observer_reception(
                source="meshcore_hub",
                node_source_id="01" * 32,
                observer_source_id="02" * 32,
                packet_hash="   ",
                observed_at=NOW,
            )


class EdgeObservationTests(unittest.TestCase):
    def test_traceroute_is_normalized(self) -> None:
        edge = make_edge_observation(
            source=" MALHA_PT ",
            network="Meshtastic",
            from_source_id=0xA35B4144,
            to_source_id="C7654321",
            edge_type=" TRACEROUTE ",
            directed=True,
            observed_at="2026-07-25T12:00:00+00:00",
            metrics={
                "snr_db": "7.5",
                "rssi_dbm": -98,
            },
        )

        self.assertEqual(edge.source, "malha_pt")
        self.assertEqual(edge.network, "meshtastic")
        self.assertEqual(
            edge.from_source_id,
            "!a35b4144",
        )
        self.assertEqual(
            edge.to_source_id,
            "!c7654321",
        )
        self.assertEqual(
            edge.from_id,
            "meshtastic:!a35b4144",
        )
        self.assertEqual(
            edge.to_id,
            "meshtastic:!c7654321",
        )
        self.assertEqual(
            edge.id,
            (
                "meshtastic:traceroute:"
                "!a35b4144:!c7654321"
            ),
        )
        self.assertEqual(
            edge.observed_at,
            "2026-07-25T12:00:00Z",
        )
        self.assertEqual(
            edge.metrics,
            {
                "snr_db": 7.5,
                "rssi_dbm": -98.0,
            },
        )

    def test_undirected_edge_orders_endpoints(
        self,
    ) -> None:
        edge = make_edge_observation(
            source="meshview_es",
            network="meshtastic",
            from_source_id="b1234567",
            to_source_id="a35b4144",
            edge_type="neighbor",
            directed=False,
            observed_at=NOW,
        )

        self.assertEqual(
            edge.from_source_id,
            "!a35b4144",
        )
        self.assertEqual(
            edge.to_source_id,
            "!b1234567",
        )
        self.assertEqual(
            edge.id,
            (
                "meshtastic:neighbor:"
                "!a35b4144:!b1234567"
            ),
        )

    def test_direction_rules_are_enforced(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "neighbor no puede ser dirigida",
        ):
            make_edge_observation(
                source="meshview_es",
                network="meshtastic",
                from_source_id="a35b4144",
                to_source_id="b1234567",
                edge_type="neighbor",
                directed=True,
                observed_at=NOW,
            )

        with self.assertRaisesRegex(
            ValueError,
            "traceroute debe ser dirigida",
        ):
            make_edge_observation(
                source="malha_pt",
                network="meshtastic",
                from_source_id="a35b4144",
                to_source_id="b1234567",
                edge_type="traceroute",
                directed=False,
                observed_at=NOW,
            )

    def test_self_link_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "consigo mismo",
        ):
            make_edge_observation(
                source="malha_pt",
                network="meshtastic",
                from_source_id="a35b4144",
                to_source_id="!A35B4144",
                edge_type="traceroute",
                directed=True,
                observed_at=NOW,
            )

    def test_incompatible_source_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "no es una fuente MeshCore",
        ):
            make_edge_observation(
                source="malha_pt",
                network="meshcore",
                from_source_id="02ab34cd",
                to_source_id="03ef5678",
                edge_type="observed",
                directed=False,
                observed_at=NOW,
            )

    def test_invalid_metric_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "snr_db debe ser finito",
        ):
            make_edge_observation(
                source="malha_pt",
                network="meshtastic",
                from_source_id="a35b4144",
                to_source_id="b1234567",
                edge_type="traceroute",
                directed=True,
                observed_at=NOW,
                metrics={
                    "snr_db": float("nan"),
                },
            )


if __name__ == "__main__":
    unittest.main()
