"""Probas do acceso incremental ao live de O Zulo."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from mesh_noroeste.http_client import JsonFetchResult
from mesh_noroeste.ozulo_live_http import (
    build_ozulo_live_packets_url,
    fetch_ozulo_live_page,
)


def packet(
    *,
    packet_id: int,
    imported_at_us: int,
    from_node_id: int,
) -> dict[str, object]:
    return {
        "id": packet_id,
        "import_time_us": imported_at_us,
        "channel": "LongFast",
        "from_node_id": from_node_id,
        "to_node_id": 0xFFFFFFFF,
        "portnum": 3,
        "long_name": "Nodo",
        "payload": "",
        "to_long_name": "",
    }


class OzuloLiveHttpTests(unittest.TestCase):
    def test_builds_initial_url(self) -> None:
        self.assertEqual(
            build_ozulo_live_packets_url(
                limit=1000
            ),
            (
                "https://meshview.mesh.comunidadeozulo.org/"
                "api/packets?limit=1000"
            ),
        )

    def test_builds_incremental_url(self) -> None:
        self.assertEqual(
            build_ozulo_live_packets_url(
                cursor=123456,
                limit=250,
            ),
            (
                "https://meshview.mesh.comunidadeozulo.org/"
                "api/packets?since=123456&limit=250"
            ),
        )

    def test_replaces_existing_cursor_and_limit(self) -> None:
        url = build_ozulo_live_packets_url(
            (
                "https://example.test/api/packets"
                "?foo=bar&since=1&limit=2"
            ),
            cursor=10,
            limit=20,
        )

        self.assertEqual(
            url,
            (
                "https://example.test/api/packets"
                "?foo=bar&since=10&limit=20"
            ),
        )

    def test_packets_are_returned_oldest_first(self) -> None:
        document = {
            "latest_import_time": 300,
            "packets": [
                packet(
                    packet_id=3,
                    imported_at_us=300,
                    from_node_id=3,
                ),
                packet(
                    packet_id=1,
                    imported_at_us=100,
                    from_node_id=1,
                ),
                packet(
                    packet_id=2,
                    imported_at_us=200,
                    from_node_id=2,
                ),
            ],
        }

        fetched = JsonFetchResult(
            document=document,
            requested_url="https://example.test/requested",
            final_url="https://example.test/final",
            status=200,
            content_type="application/json",
            bytes_received=123,
        )

        with patch(
            "mesh_noroeste.ozulo_live_http.fetch_json",
            return_value=fetched,
        ):
            page = fetch_ozulo_live_page(
                cursor=50,
                url="https://example.test/api/packets",
            )

        self.assertEqual(
            [
                item.imported_at_us
                for item in page.packets
            ],
            [100, 200, 300],
        )
        self.assertEqual(page.next_cursor, 300)
        self.assertEqual(page.bytes_received, 123)

    def test_full_page_is_marked_as_saturated(self) -> None:
        document = {
            "latest_import_time": 200,
            "packets": [
                packet(
                    packet_id=2,
                    imported_at_us=200,
                    from_node_id=2,
                ),
                packet(
                    packet_id=1,
                    imported_at_us=100,
                    from_node_id=1,
                ),
            ],
        }

        fetched = JsonFetchResult(
            document=document,
            requested_url="https://example.test/requested",
            final_url="https://example.test/final",
            status=200,
            content_type="application/json",
            bytes_received=100,
        )

        with patch(
            "mesh_noroeste.ozulo_live_http.fetch_json",
            return_value=fetched,
        ):
            page = fetch_ozulo_live_page(
                cursor=50,
                limit=2,
                url="https://example.test/api/packets",
            )

        self.assertTrue(page.saturated)
        self.assertEqual(page.next_cursor, 200)

    def test_partial_page_is_not_saturated(self) -> None:
        fetched = JsonFetchResult(
            document={
                "latest_import_time": 100,
                "packets": [
                    packet(
                        packet_id=1,
                        imported_at_us=100,
                        from_node_id=1,
                    )
                ],
            },
            requested_url="https://example.test/requested",
            final_url="https://example.test/final",
            status=200,
            content_type="application/json",
            bytes_received=50,
        )

        with patch(
            "mesh_noroeste.ozulo_live_http.fetch_json",
            return_value=fetched,
        ):
            page = fetch_ozulo_live_page(
                cursor=50,
                limit=2,
                url="https://example.test/api/packets",
            )

        self.assertFalse(page.saturated)

    def test_empty_page_keeps_cursor(self) -> None:
        fetched = JsonFetchResult(
            document={
                "latest_import_time": None,
                "packets": [],
            },
            requested_url="https://example.test/requested",
            final_url="https://example.test/final",
            status=200,
            content_type="application/json",
            bytes_received=20,
        )

        with patch(
            "mesh_noroeste.ozulo_live_http.fetch_json",
            return_value=fetched,
        ):
            page = fetch_ozulo_live_page(
                cursor=500,
                url="https://example.test/api/packets",
            )

        self.assertEqual(page.packets, ())
        self.assertEqual(page.next_cursor, 500)

    def test_non_advancing_page_is_rejected(self) -> None:
        fetched = JsonFetchResult(
            document={
                "latest_import_time": 100,
                "packets": [
                    packet(
                        packet_id=1,
                        imported_at_us=100,
                        from_node_id=1,
                    )
                ],
            },
            requested_url="https://example.test/requested",
            final_url="https://example.test/final",
            status=200,
            content_type="application/json",
            bytes_received=20,
        )

        with patch(
            "mesh_noroeste.ozulo_live_http.fetch_json",
            return_value=fetched,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "non avanzou",
            ):
                fetch_ozulo_live_page(
                    cursor=100,
                    url="https://example.test/api/packets",
                )

    def test_limit_above_api_cap_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "entre 1 e 1000",
        ):
            build_ozulo_live_packets_url(
                limit=1001
            )


if __name__ == "__main__":
    unittest.main()
