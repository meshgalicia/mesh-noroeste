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
