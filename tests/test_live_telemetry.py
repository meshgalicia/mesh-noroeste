"""Probas do parser Telemetry usado polo live."""

from __future__ import annotations

import unittest

from mesh_noroeste.live_telemetry import (
    parse_live_telemetry_payload,
)


class LiveTelemetryTests(unittest.TestCase):
    def test_device_metrics_are_parsed(self) -> None:
        result = parse_live_telemetry_payload(
            "time: 1787134073\n"
            "device_metrics {\n"
            "  battery_level: 88\n"
            "  voltage: 4.039\n"
            "  channel_utilization: 13.341667\n"
            "  air_util_tx: 2.1988335\n"
            "  uptime_seconds: 1726483\n"
            "}\n"
        )

        self.assertEqual(
            result.time,
            1787134073,
        )

        self.assertEqual(
            result.device_metrics,
            {
                "battery_level": 88,
                "voltage": 4.039,
                "channel_utilization": 13.341667,
                "air_util_tx": 2.1988335,
                "uptime_seconds": 1726483,
            },
        )

        self.assertIsNone(
            result.environment_metrics
        )
        self.assertIsNone(
            result.power_metrics
        )
        self.assertTrue(result.has_metrics)


    def test_environment_metrics_are_parsed(
        self,
    ) -> None:
        result = parse_live_telemetry_payload(
            "time: 1787133718\n"
            "environment_metrics {\n"
            "  temperature: 24.552584\n"
            "  relative_humidity: 65.47269\n"
            "  barometric_pressure: 990.1126\n"
            "  gas_resistance: 241.68044\n"
            "  iaq: 142\n"
            "}\n"
        )

        self.assertEqual(
            result.environment_metrics,
            {
                "temperature": 24.552584,
                "relative_humidity": 65.47269,
                "barometric_pressure": 990.1126,
                "gas_resistance": 241.68044,
                "iaq": 142,
            },
        )


    def test_environment_voltage_current_and_lux(
        self,
    ) -> None:
        result = parse_live_telemetry_payload(
            "environment_metrics {\n"
            "  temperature: 24.44\n"
            "  voltage: 3.976\n"
            "  current: 17.2\n"
            "  lux: 100.0\n"
            "}\n"
        )

        self.assertEqual(
            result.environment_metrics,
            {
                "temperature": 24.44,
                "voltage": 3.976,
                "current": 17.2,
                "lux": 100.0,
            },
        )


    def test_power_metrics_are_parsed(self) -> None:
        result = parse_live_telemetry_payload(
            "time: 1770357231\n"
            "power_metrics {\n"
            "  ch1_voltage: 4.064\n"
            "  ch1_current: 12.8\n"
            "  ch2_voltage: 4.064\n"
            "  ch2_current: -11.6\n"
            "  ch3_voltage: 14.104\n"
            "  ch3_current: 8.4\n"
            "}\n"
        )

        self.assertEqual(
            result.power_metrics,
            {
                "ch1_voltage": 4.064,
                "ch1_current": 12.8,
                "ch2_voltage": 4.064,
                "ch2_current": -11.6,
                "ch3_voltage": 14.104,
                "ch3_current": 8.4,
            },
        )


    def test_unknown_fields_are_not_published(
        self,
    ) -> None:
        result = parse_live_telemetry_payload(
            "time: 123\n"
            "device_metrics {\n"
            "  battery_level: 50\n"
            "  secret_future_field: 999\n"
            "}\n"
        )

        self.assertEqual(
            result.device_metrics,
            {
                "battery_level": 50,
            },
        )


    def test_empty_payload_is_valid(self) -> None:
        result = parse_live_telemetry_payload("")

        self.assertIsNone(result.time)
        self.assertIsNone(result.device_metrics)
        self.assertIsNone(
            result.environment_metrics
        )
        self.assertIsNone(result.power_metrics)
        self.assertFalse(result.has_metrics)


    def test_unrelated_payload_is_not_invented(
        self,
    ) -> None:
        result = parse_live_telemetry_payload(
            "foo: 123\nbar: text\n"
        )

        self.assertFalse(result.has_metrics)


    def test_non_text_payload_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "payload debe ser texto",
        ):
            parse_live_telemetry_payload(
                None  # type: ignore[arg-type]
            )


if __name__ == "__main__":
    unittest.main()
