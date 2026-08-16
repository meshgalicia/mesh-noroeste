"""Probas do parser RouteDiscovery usado polo live."""

from __future__ import annotations

import unittest

from mesh_noroeste.live_traceroute import (
    parse_live_traceroute_payload,
)


class LiveTracerouteTests(unittest.TestCase):
    def test_complete_payload_is_preserved(self) -> None:
        result = parse_live_traceroute_payload(
            "route: 2551349043\n"
            "route: 67544660\n"
            "snr_towards: -32\n"
            "snr_towards: 11\n"
            "route_back: 1228080921\n"
            "route_back: 3287164068\n"
            "snr_back: 9\n"
            "snr_back: -12\n"
        )

        self.assertEqual(
            result.route,
            (
                "!98127f33",
                "!0406a654",
            ),
        )
        self.assertEqual(
            result.route_back,
            (
                "!49330719",
                "!c3ee24a4",
            ),
        )
        self.assertEqual(
            result.snr_towards,
            (-32, 11),
        )
        self.assertEqual(
            result.snr_back,
            (9, -12),
        )
        self.assertTrue(result.has_route)

    def test_empty_traceroute_response_is_valid(self) -> None:
        result = parse_live_traceroute_payload("")

        self.assertEqual(result.route, ())
        self.assertEqual(result.route_back, ())
        self.assertEqual(result.snr_towards, ())
        self.assertEqual(result.snr_back, ())
        self.assertFalse(result.has_route)

    def test_unrelated_payload_fields_are_ignored(self) -> None:
        result = parse_live_traceroute_payload(
            "foo: 123\n"
            "route: 1\n"
            "bar: text\n"
        )

        self.assertEqual(
            result.route,
            ("!00000001",),
        )

    def test_out_of_range_node_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "fóra de rango",
        ):
            parse_live_traceroute_payload(
                "route: 4294967296"
            )

    def test_non_text_payload_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "payload debe ser texto",
        ):
            parse_live_traceroute_payload(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()


class LiveTraceroutePathTests(unittest.TestCase):
    def test_builds_towards_and_back_separately(self) -> None:
        from mesh_noroeste.live_traceroute import (
            build_live_traceroute_path,
        )

        payload = parse_live_traceroute_payload(
            "route: 2914283415\n"
            "route: 1770352240\n"
            "snr_towards: -17\n"
            "snr_towards: -15\n"
            "snr_towards: -8\n"
            "route_back: 2997341484\n"
            "route_back: 2914283415\n"
            "route_back: 1384609890\n"
            "route_back: 2697754764\n"
            "snr_back: 25\n"
            "snr_back: -39\n"
            "snr_back: -39\n"
            "snr_back: -27\n"
        )

        result = build_live_traceroute_path(
            from_source_id="!33f5c519",
            to_source_id="!f9afbe04",
            payload=payload,
        )

        self.assertEqual(
            result.towards,
            (
                "!33f5c519",
                "!adb46f97",
                "!69856e70",
                "!f9afbe04",
            ),
        )

        self.assertEqual(
            result.back,
            (
                "!f9afbe04",
                "!b2a7cd2c",
                "!adb46f97",
                "!52877862",
                "!a0cc788c",
                "!33f5c519",
            ),
        )

        self.assertEqual(
            result.snr_towards,
            (-17, -15, -8),
        )
        self.assertEqual(
            result.snr_back,
            (25, -39, -39, -27),
        )

    def test_route_only_does_not_invent_return_path(
        self,
    ) -> None:
        from mesh_noroeste.live_traceroute import (
            build_live_traceroute_path,
        )

        payload = parse_live_traceroute_payload(
            "route: 2697754764\n"
            "snr_towards: -12\n"
        )

        result = build_live_traceroute_path(
            from_source_id="!a5b8f696",
            to_source_id="!69856e70",
            payload=payload,
        )

        self.assertEqual(
            result.towards,
            (
                "!a5b8f696",
                "!a0cc788c",
                "!69856e70",
            ),
        )
        self.assertEqual(result.back, ())
        self.assertTrue(result.has_towards)
        self.assertFalse(result.has_back)

    def test_empty_payload_does_not_invent_any_path(
        self,
    ) -> None:
        from mesh_noroeste.live_traceroute import (
            build_live_traceroute_path,
        )

        payload = parse_live_traceroute_payload("")

        result = build_live_traceroute_path(
            from_source_id="!da5f9d10",
            to_source_id="!e58d9a13",
            payload=payload,
        )

        self.assertEqual(result.towards, ())
        self.assertEqual(result.back, ())
        self.assertFalse(result.has_towards)
        self.assertFalse(result.has_back)

    def test_same_origin_and_destination_is_rejected(
        self,
    ) -> None:
        from mesh_noroeste.live_traceroute import (
            build_live_traceroute_path,
        )

        payload = parse_live_traceroute_payload(
            "route: 1"
        )

        with self.assertRaisesRegex(
            ValueError,
            "deben ser distintos",
        ):
            build_live_traceroute_path(
                from_source_id="!00000001",
                to_source_id="!00000001",
                payload=payload,
            )
