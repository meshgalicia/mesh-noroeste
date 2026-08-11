"""Pruebas del cliente HTTP JSON."""

from __future__ import annotations

from email.message import Message
from io import BytesIO
import unittest
from unittest.mock import patch
from urllib.error import URLError
from urllib.request import Request

from mesh_noroeste.http_client import (
    _SafeRedirectHandler,
    FetchError,
    fetch_bytes,
    fetch_json,
)


class FakeResponse:
    def __init__(
        self,
        payload: bytes,
        *,
        status: int = 200,
        content_type: str | None = (
            "application/json; charset=utf-8"
        ),
        content_length: int | None = None,
        final_url: str = (
            "https://example.test/data.json"
        ),
    ) -> None:
        self.status = status
        self._stream = BytesIO(payload)
        self._final_url = final_url
        self.headers = Message()

        if content_type is not None:
            self.headers["Content-Type"] = content_type

        if content_length is not None:
            self.headers["Content-Length"] = str(
                content_length
            )

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    def getcode(self) -> int:
        return self.status

    def geturl(self) -> str:
        return self._final_url

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(
        self,
        exception_type,
        exception,
        traceback,
    ) -> None:
        return None


class HttpClientTests(unittest.TestCase):
    def test_valid_json_is_returned(self) -> None:
        response = FakeResponse(
            b'\xef\xbb\xbf{"nodes": [1, 2, 3]}',
            content_length=23,
        )

        with patch(
            "mesh_noroeste.http_client.urlopen",
            return_value=response,
        ) as mocked_open:
            result = fetch_json(
                "https://example.test/data.json",
                timeout=5,
                max_bytes=1024,
                user_agent="Mesh-Noroeste-Test/1.0",
            )

        self.assertEqual(
            result.document,
            {"nodes": [1, 2, 3]},
        )
        self.assertEqual(result.status, 200)
        self.assertEqual(
            result.final_url,
            "https://example.test/data.json",
        )
        self.assertEqual(
            result.content_type,
            "application/json; charset=utf-8",
        )
        self.assertEqual(
            result.bytes_received,
            len(b'\xef\xbb\xbf{"nodes": [1, 2, 3]}'),
        )

        request = mocked_open.call_args.args[0]

        self.assertEqual(
            request.get_header("User-agent"),
            "Mesh-Noroeste-Test/1.0",
        )

    def test_authorization_header_is_forwarded(
        self,
    ) -> None:
        response = FakeResponse(
            b"{}",
            content_length=2,
        )

        with patch(
            "mesh_noroeste.http_client.urlopen",
            return_value=response,
        ) as mocked_open:
            fetch_json(
                "https://example.test/data.json",
                headers={
                    "Authorization": "Bearer abc123",
                },
            )

        request = mocked_open.call_args.args[0]

        self.assertEqual(
            request.get_header("Authorization"),
            "Bearer abc123",
        )

    def test_cross_host_redirect_drops_authorization(
        self,
    ) -> None:
        redirect = _SafeRedirectHandler()

        original = Request(
            "https://hub.mesh.gal/api/v1/nodes",
            headers={
                "Authorization": "Bearer segredo-de-proba",
            },
        )

        redirected = redirect.redirect_request(
            original,
            None,
            302,
            "Found",
            {},
            "https://example.org/roubado",
        )

        self.assertIsNotNone(redirected)
        assert redirected is not None

        self.assertIsNone(
            redirected.get_header("Authorization")
        )

    def test_multiple_headers_are_forwarded(
        self,
    ) -> None:
        response = FakeResponse(
            b"{}",
            content_length=2,
        )

        with patch(
            "mesh_noroeste.http_client.urlopen",
            return_value=response,
        ) as mocked_open:
            fetch_json(
                "https://example.test/data.json",
                headers={
                    "Authorization": "Bearer token",
                    "Accept": "application/vnd.meshcore+json",
                    "X-Test": "Mesh-Noroeste",
                },
            )

        request = mocked_open.call_args.args[0]

        self.assertEqual(
            request.get_header("Authorization"),
            "Bearer token",
        )
        self.assertEqual(
            request.get_header("Accept"),
            "application/vnd.meshcore+json",
        )
        self.assertEqual(
            request.get_header("X-test"),
            "Mesh-Noroeste",
        )

    def test_headers_are_forwarded_by_fetch_bytes(
        self,
    ) -> None:
        response = FakeResponse(
            b"payload",
            content_length=7,
        )

        with patch(
            "mesh_noroeste.http_client.urlopen",
            return_value=response,
        ) as mocked_open:
            fetch_bytes(
                "https://example.test/data.bin",
                headers={
                    "Authorization": "Bearer binary-token",
                },
            )

        request = mocked_open.call_args.args[0]

        self.assertEqual(
            request.get_header("Authorization"),
            "Bearer binary-token",
        )

    def test_header_name_with_newline_is_rejected(
        self,
    ) -> None:
        with patch(
            "mesh_noroeste.http_client.urlopen",
        ) as mocked_open:
            with self.assertRaisesRegex(
                ValueError,
                "cabecera HTTP",
            ):
                fetch_json(
                    "https://example.test/data.json",
                    headers={
                        "Bad\nHeader": "value",
                    },
                )

        mocked_open.assert_not_called()

    def test_header_value_with_newline_is_rejected(
        self,
    ) -> None:
        with patch(
            "mesh_noroeste.http_client.urlopen",
        ) as mocked_open:
            with self.assertRaisesRegex(
                ValueError,
                "cabecera HTTP",
            ):
                fetch_json(
                    "https://example.test/data.json",
                    headers={
                        "Authorization": (
                            "Bearer abc\r\n"
                            "X-Test: injected"
                        ),
                    },
                )

        mocked_open.assert_not_called()

    def test_non_https_url_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Solo se admiten fuentes mediante HTTPS",
        ):
            fetch_json(
                "http://example.test/data.json"
            )

    def test_credentials_in_url_are_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "no puede incluir credenciales",
        ):
            fetch_json(
                "https://user:secret@example.test/data"
            )

    def test_content_length_limit_is_enforced(
        self,
    ) -> None:
        response = FakeResponse(
            b"{}",
            content_length=5000,
        )

        with patch(
            "mesh_noroeste.http_client.urlopen",
            return_value=response,
        ):
            with self.assertRaisesRegex(
                FetchError,
                "supera el límite permitido",
            ):
                fetch_json(
                    "https://example.test/data.json",
                    max_bytes=100,
                )

    def test_streamed_size_limit_is_enforced(
        self,
    ) -> None:
        response = FakeResponse(
            b"{" + (b"x" * 200) + b"}",
            content_length=None,
        )

        with patch(
            "mesh_noroeste.http_client.urlopen",
            return_value=response,
        ):
            with self.assertRaisesRegex(
                FetchError,
                "supera el límite permitido",
            ):
                fetch_json(
                    "https://example.test/data.json",
                    max_bytes=100,
                )

    def test_invalid_json_is_rejected(self) -> None:
        response = FakeResponse(
            b"<html>error</html>"
        )

        with patch(
            "mesh_noroeste.http_client.urlopen",
            return_value=response,
        ):
            with self.assertRaisesRegex(
                FetchError,
                "no contiene JSON válido",
            ):
                fetch_json(
                    "https://example.test/data.json"
                )

    def test_network_error_is_wrapped(self) -> None:
        with patch(
            "mesh_noroeste.http_client.urlopen",
            side_effect=URLError(
                "servidor inaccesible"
            ),
        ):
            with self.assertRaisesRegex(
                FetchError,
                "Error de red",
            ):
                fetch_json(
                    "https://example.test/data.json"
                )


    def test_binary_payload_is_not_decoded(
        self,
    ) -> None:
        payload = bytes.fromhex(
            "81a2706bc4020102"
        )
        response = FakeResponse(
            payload,
            content_type="application/msgpack",
            content_length=len(payload),
        )

        with patch(
            "mesh_noroeste.http_client.urlopen",
            return_value=response,
        ) as mocked_open:
            result = fetch_bytes(
                "https://example.test/nodes",
                max_bytes=1024,
                accept="application/msgpack",
            )

        self.assertEqual(result.payload, payload)
        self.assertEqual(
            result.content_type,
            "application/msgpack",
        )
        self.assertEqual(
            result.bytes_received,
            len(payload),
        )

        request = mocked_open.call_args.args[0]

        self.assertEqual(
            request.get_header("Accept"),
            "application/msgpack",
        )

    def test_binary_accept_rejects_newlines(
        self,
    ) -> None:
        malicious_accept = (
            "application/msgpack"
            + chr(13)
            + chr(10)
            + "X-Test: injected"
        )

        with patch(
            "mesh_noroeste.http_client.urlopen",
        ) as mocked_open:
            with self.assertRaisesRegex(
                ValueError,
                "Accept no puede contener",
            ):
                fetch_bytes(
                    "https://example.test/nodes",
                    accept=malicious_accept,
                )

        mocked_open.assert_not_called()

    def test_binary_stream_limit_is_enforced(
        self,
    ) -> None:
        response = FakeResponse(
            b"x" * 101,
            content_length=None,
        )

        with patch(
            "mesh_noroeste.http_client.urlopen",
            return_value=response,
        ):
            with self.assertRaisesRegex(
                FetchError,
                "supera el límite permitido",
            ):
                fetch_bytes(
                    "https://example.test/nodes",
                    max_bytes=100,
                )


if __name__ == "__main__":
    unittest.main()
