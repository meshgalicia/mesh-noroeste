"""Probas dunha iteración do colector live de O Zulo."""

from __future__ import annotations

from threading import Event, Lock
import unittest

from mesh_noroeste.domain import (
    MeshtasticLivePacket,
    MeshtasticLiveReception,
)
from mesh_noroeste.http_client import FetchError
from mesh_noroeste.ozulo_live_http import OzuloLivePage
from mesh_noroeste.ozulo_live_poll import (
    build_ozulo_packets_seen_url,
    poll_ozulo_live_once,
)


def live_packet(
    packet_id: int,
    from_source_id: str,
    imported_at_us: int,
) -> MeshtasticLivePacket:
    return MeshtasticLivePacket(
        source="ozulo_map",
        packet_id=packet_id,
        from_source_id=from_source_id,
        to_source_id="!ffffffff",
        portnum=3,
        channel="LongFast",
        imported_at_us=imported_at_us,
        long_name="Nodo",
        to_long_name=None,
        payload="",
    )


def live_reception(
    packet: MeshtasticLivePacket,
    gateway_source_id: str,
    imported_at_us: int,
) -> MeshtasticLiveReception:
    return MeshtasticLiveReception(
        source="ozulo_map",
        packet_id=packet.packet_id,
        from_source_id=packet.from_source_id,
        gateway_source_id=gateway_source_id,
        rx_time=1,
        hop_limit=2,
        hop_start=3,
        snr_db=5.0,
        rssi_dbm=-80.0,
        channel="LongFast",
        topic=None,
        imported_at_us=imported_at_us,
    )


class OzuloLivePollTests(unittest.TestCase):
    def test_packets_seen_url(self) -> None:
        self.assertEqual(
            build_ozulo_packets_seen_url(123),
            (
                "https://meshview.mesh.comunidadeozulo.org/"
                "api/packets_seen/123"
            ),
        )

    def test_invalid_packet_id_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "32 bits",
        ):
            build_ozulo_packets_seen_url(
                0x1_0000_0000
            )

    def test_poll_combines_packets_and_receptions(self) -> None:
        first = live_packet(
            10,
            "!00000001",
            100,
        )
        second = live_packet(
            20,
            "!00000002",
            200,
        )

        page = OzuloLivePage(
            packets=(first, second),
            next_cursor=200,
            saturated=False,
            requested_url="https://example.test/request",
            final_url="https://example.test/final",
            bytes_received=100,
        )

        page_calls = []
        reception_calls = []

        def page_fetcher(**kwargs):
            page_calls.append(kwargs)
            return page

        def reception_fetcher(packet, **kwargs):
            reception_calls.append((packet, kwargs))

            return (
                (
                    live_reception(
                        packet,
                        "!000000ff",
                        packet.imported_at_us + 1,
                    ),
                ),
                20,
            )

        batch = poll_ozulo_live_once(
            cursor=50,
            limit=10,
            packets_url="https://example.test/packets",
            packets_seen_base_url=(
                "https://example.test/packets_seen"
            ),
            page_fetcher=page_fetcher,
            reception_fetcher=reception_fetcher,
        )

        self.assertEqual(len(batch.observations), 2)
        self.assertEqual(
            batch.observations[0].packet,
            first,
        )
        self.assertEqual(
            batch.observations[1].packet,
            second,
        )
        self.assertEqual(
            batch.observations[0]
            .receptions[0]
            .from_source_id,
            "!00000001",
        )
        self.assertEqual(
            batch.observations[1]
            .receptions[0]
            .from_source_id,
            "!00000002",
        )
        self.assertEqual(batch.previous_cursor, 50)
        self.assertEqual(batch.next_cursor, 200)
        self.assertFalse(batch.saturated)
        self.assertFalse(batch.possible_gap)
        self.assertEqual(batch.bytes_received, 140)
        self.assertEqual(len(page_calls), 1)
        self.assertEqual(len(reception_calls), 2)

    def test_packets_seen_are_fetched_concurrently(
        self,
    ) -> None:
        first = live_packet(
            10,
            "!00000001",
            100,
        )
        second = live_packet(
            20,
            "!00000002",
            200,
        )

        page = OzuloLivePage(
            packets=(first, second),
            next_cursor=200,
            saturated=False,
            requested_url="https://example.test/request",
            final_url="https://example.test/final",
            bytes_received=100,
        )

        def page_fetcher(**kwargs):
            return page

        second_started = Event()
        lock = Lock()
        started: list[int] = []

        def reception_fetcher(packet, **kwargs):
            with lock:
                started.append(
                    packet.packet_id
                )

            if packet.packet_id == 20:
                second_started.set()

            if packet.packet_id == 10:
                if not second_started.wait(
                    timeout=2,
                ):
                    raise AssertionError(
                        "packets_seen executouse en serie"
                    )

            return (
                (
                    live_reception(
                        packet,
                        "!000000ff",
                        packet.imported_at_us + 1,
                    ),
                ),
                20,
            )

        batch = poll_ozulo_live_once(
            cursor=50,
            page_fetcher=page_fetcher,
            reception_fetcher=reception_fetcher,
        )

        self.assertCountEqual(
            started,
            [10, 20],
        )

        self.assertEqual(
            [
                observation.packet.packet_id
                for observation in batch.observations
            ],
            [10, 20],
        )

        self.assertEqual(
            batch.bytes_received,
            140,
        )

    def test_failed_packets_seen_does_not_abort_batch(
        self,
    ) -> None:
        first = live_packet(
            10,
            "!00000001",
            100,
        )
        second = live_packet(
            20,
            "!00000002",
            200,
        )

        page = OzuloLivePage(
            packets=(first, second),
            next_cursor=200,
            saturated=False,
            requested_url="https://example.test/request",
            final_url="https://example.test/final",
            bytes_received=100,
        )

        def page_fetcher(**kwargs):
            return page

        calls = []

        def reception_fetcher(packet, **kwargs):
            calls.append(packet.packet_id)

            if packet.packet_id == 10:
                raise FetchError(
                    "Error HTTP 502 de proba"
                )

            return (
                (
                    live_reception(
                        packet,
                        "!000000ff",
                        packet.imported_at_us + 1,
                    ),
                ),
                20,
            )

        with self.assertLogs(
            "mesh_noroeste.ozulo_live_poll",
            level="WARNING",
        ) as captured:
            batch = poll_ozulo_live_once(
                cursor=50,
                page_fetcher=page_fetcher,
                reception_fetcher=reception_fetcher,
            )

        self.assertEqual(
            calls,
            [10, 20],
        )
        self.assertEqual(
            len(batch.observations),
            2,
        )
        self.assertEqual(
            batch.observations[0].receptions,
            (),
        )
        self.assertEqual(
            len(batch.observations[1].receptions),
            1,
        )
        self.assertEqual(
            batch.next_cursor,
            200,
        )
        self.assertEqual(
            batch.bytes_received,
            120,
        )
        self.assertTrue(
            any(
                "packet_id=10" in message
                for message in captured.output
            )
        )

    def test_saturation_is_propagated_as_possible_gap(
        self,
    ) -> None:
        page = OzuloLivePage(
            packets=(),
            next_cursor=100,
            saturated=True,
            requested_url="https://example.test/request",
            final_url="https://example.test/final",
            bytes_received=10,
        )

        def page_fetcher(**kwargs):
            return page

        def reception_fetcher(packet, **kwargs):
            raise AssertionError(
                "Non debe consultar recepcións sen paquetes"
            )

        batch = poll_ozulo_live_once(
            cursor=100,
            page_fetcher=page_fetcher,
            reception_fetcher=reception_fetcher,
        )

        self.assertTrue(batch.saturated)
        self.assertTrue(batch.possible_gap)
        self.assertEqual(batch.next_cursor, 100)

    def test_empty_page_produces_empty_batch(self) -> None:
        page = OzuloLivePage(
            packets=(),
            next_cursor=500,
            saturated=False,
            requested_url="https://example.test/request",
            final_url="https://example.test/final",
            bytes_received=10,
        )

        def page_fetcher(**kwargs):
            return page

        def reception_fetcher(packet, **kwargs):
            raise AssertionError(
                "Non debe consultar packets_seen"
            )

        batch = poll_ozulo_live_once(
            cursor=500,
            page_fetcher=page_fetcher,
            reception_fetcher=reception_fetcher,
        )

        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.previous_cursor, 500)
        self.assertEqual(batch.next_cursor, 500)
        self.assertFalse(batch.possible_gap)
        self.assertEqual(batch.bytes_received, 10)


if __name__ == "__main__":
    unittest.main()
