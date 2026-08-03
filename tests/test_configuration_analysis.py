"""Pruebas del analizador propio de configuración."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mesh_noroeste import configuration_analysis


class ConfigurationAnalysisTests(unittest.TestCase):
    def metadata(
        self,
        *,
        node_id: int = 0x0123ABCD,
        hardware: str = "HELTEC_V4",
        role: str = "CLIENT",
        firmware: str = "2.7.16",
    ) -> configuration_analysis.NodeMetadata:
        return configuration_analysis.NodeMetadata(
            node_id=node_id,
            public_id=f"!{node_id:08x}",
            hardware=hardware,
            role=role,
            firmware=firmware,
        )

    def packet(
        self,
        portnum: int,
        *,
        timestamp: int,
        payload: str = "",
        destination: int = (
            configuration_analysis.BROADCAST_ID
        ),
    ) -> dict[str, object]:
        return {
            "id": timestamp,
            "portnum": portnum,
            "import_time_us": timestamp * 1_000_000,
            "payload": payload,
            "to_node_id": destination,
        }

    def test_https_base_url_is_required(self) -> None:
        self.assertEqual(
            configuration_analysis.validated_base_url(
                "https://example.org/"
            ),
            "https://example.org",
        )

        with self.assertRaises(ValueError):
            configuration_analysis.validated_base_url(
                "http://example.org"
            )

    def test_nodes_are_validated(self) -> None:
        nodes = configuration_analysis.parse_nodes({
            "nodes": [{
                "id": "!0123abcd",
                "node_id": 0x0123ABCD,
                "hw_model": "HELTEC_V4",
                "role": "CLIENT_MUTE",
                "firmware": "2.7.26",
            }]
        })

        self.assertEqual(len(nodes), 1)
        self.assertEqual(
            nodes[0].public_id,
            "!0123abcd",
        )

    def test_mismatched_identifier_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            configuration_analysis
            .ConfigurationAnalysisError,
            "no corresponde",
        ):
            configuration_analysis.parse_nodes({
                "nodes": [{
                    "id": "!ffffffff",
                    "node_id": 0x0123ABCD,
                }]
            })

    def test_fixed_position_and_fields_warn(
        self,
    ) -> None:
        payload = (
            "latitude_i: 431000000\n"
            "longitude_i: -81000000\n"
            "ground_speed: 0\n"
            "ground_track: 0"
        )
        packets = [
            self.packet(
                configuration_analysis.PORTS[
                    "position"
                ],
                timestamp=index,
                payload=payload,
            )
            for index in range(1, 9)
        ]

        result = (
            configuration_analysis.analyse_packets(
                self.metadata(),
                packets,
            )
        )
        warnings = {
            warning["key"]: warning["severity"]
            for warning in result["issues"]
        }

        self.assertEqual(
            warnings["position_fixed"],
            "high",
        )
        self.assertEqual(
            warnings["position_flags"],
            "medium",
        )

    def test_mobile_hardware_warns_for_client(
        self,
    ) -> None:
        result = (
            configuration_analysis.analyse_packets(
                self.metadata(
                    hardware="TRACKER_T1000_E",
                    role="CLIENT",
                ),
                [],
            )
        )

        self.assertIn(
            {
                "key": "client_mute_mobile",
                "severity": "medium",
            },
            result["issues"],
        )

    def test_client_base_new_firmware_warns(
        self,
    ) -> None:
        result = (
            configuration_analysis.analyse_packets(
                self.metadata(
                    role="CLIENT_BASE",
                    firmware="2.7.17",
                ),
                [],
            )
        )

        self.assertIn(
            {
                "key": "client_base_fw",
                "severity": "medium",
            },
            result["issues"],
        )

    def test_irregular_nodeinfo_is_not_reported(
        self,
    ) -> None:
        packets = [
            self.packet(
                configuration_analysis.PORTS[
                    "nodeinfo"
                ],
                timestamp=timestamp,
            )
            for timestamp in (
                1,
                61,
                181,
                601,
                1_801,
                7_201,
                21_601,
            )
        ]

        result = (
            configuration_analysis.analyse_packets(
                self.metadata(),
                packets,
            )
        )

        self.assertNotIn(
            "nodeinfo",
            {
                warning["key"]
                for warning in result["issues"]
            },
        )

    def test_regular_nodeinfo_is_reported(
        self,
    ) -> None:
        packets = [
            self.packet(
                configuration_analysis.PORTS[
                    "nodeinfo"
                ],
                timestamp=index * 3_600,
            )
            for index in range(7)
        ]

        result = (
            configuration_analysis.analyse_packets(
                self.metadata(),
                packets,
            )
        )

        self.assertIn(
            {
                "key": "nodeinfo",
                "severity": "high",
            },
            result["issues"],
        )

    def test_hop_limit_does_not_create_own_warning(
        self,
    ) -> None:
        result = (
            configuration_analysis.analyse_packets(
                self.metadata(),
                [],
                traceroute_hop_start=7,
            )
        )

        self.assertNotIn(
            "hop_limit_high",
            {
                warning["key"]
                for warning in result["issues"]
            },
        )

    def test_mobile_specific_role_is_accepted(
        self,
    ) -> None:
        result = (
            configuration_analysis.analyse_packets(
                self.metadata(
                    hardware="TRACKER_T1000_E",
                    role="TRACKER",
                ),
                [],
            )
        )

        self.assertNotIn(
            "client_mute_mobile",
            {
                warning["key"]
                for warning in result["issues"]
            },
        )

    def test_build_document_uses_all_nodes(
        self,
    ) -> None:
        nodes = (
            self.metadata(node_id=1),
            self.metadata(node_id=2),
        )

        def fake_analyse(
            metadata: configuration_analysis.NodeMetadata,
            **_: object,
        ) -> dict[str, object]:
            return {
                "id": metadata.public_id,
                "issues": [],
            }

        with patch.object(
            configuration_analysis,
            "analyse_node",
            side_effect=fake_analyse,
        ):
            document = (
                configuration_analysis.build_document(
                    nodes,
                    base_url="https://example.org",
                    timeout=1.0,
                    workers=2,
                    max_packets=100,
                    now=1_785_266_203,
                )
            )

        self.assertEqual(
            document["updated"],
            1_785_266_203,
        )
        self.assertEqual(
            [record["id"] for record in document["nodes"]],
            ["!00000001", "!00000002"],
        )

    def test_run_analysis_filters_excluded_nodes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exclusions = root / "exclusions.json"
            output = root / "analysis.json"

            exclusions.write_text(
                '{"exclusions":['
                '{"canonical_id":"meshtastic:!00000002"}'
                ']}',
                encoding="utf-8",
            )

            source = {
                "nodes": [
                    {"node_id": 1, "id": "!00000001"},
                    {"node_id": 2, "id": "!00000002"},
                ],
            }
            received: list[str] = []

            def fake_build(nodes, **_):
                received.extend(
                    node.public_id for node in nodes
                )
                return {"updated": 123, "nodes": []}

            with (
                patch.dict(
                    os.environ,
                    {"MESH_EXCLUSIONS_PATH": str(exclusions)},
                ),
                patch.object(
                    configuration_analysis,
                    "_fetch_document",
                    return_value=source,
                ),
                patch.object(
                    configuration_analysis,
                    "build_document",
                    side_effect=fake_build,
                ),
            ):
                configuration_analysis.run_analysis(
                    base_url="https://example.org",
                    output_path=output,
                )

            self.assertEqual(received, ["!00000001"])
            self.assertTrue(output.is_file())

    def test_atomic_write_replaces_document(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "analysis.json"
            path.write_text(
                '{"old":true}',
                encoding="utf-8",
            )

            configuration_analysis.atomic_write(
                path,
                {
                    "updated": 123,
                    "nodes": [],
                },
            )

            self.assertEqual(
                json.loads(
                    path.read_text(encoding="utf-8")
                ),
                {
                    "updated": 123,
                    "nodes": [],
                },
            )


if __name__ == "__main__":
    unittest.main()
