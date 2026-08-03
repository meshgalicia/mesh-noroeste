"""Pruebas del acceso HTTP y caché de Malha."""
from __future__ import annotations

from email.message import Message
from io import BytesIO
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from mesh_noroeste.http_client import FetchError
from mesh_noroeste.malha_http import (
    MALHA_ACCEPT_LANGUAGE,
    MALHA_PT_URL,
    MALHA_USER_AGENT,
    fetch_malha_pt,
    load_malha_pt_cache,
)


def document_bytes() -> bytes:
    return json.dumps(
        {
            "locations": [],
            "traceroute_links": [],
            "packet_links": [],
        },
        separators=(",", ":"),
    ).encode("utf-8")


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
        final_url: str = MALHA_PT_URL,
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


class FakeOpener:
    def __init__(
        self,
        outcomes: list[object],
    ) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[object] = []
        self.timeouts: list[float] = []

    def open(
        self,
        request,
        *,
        timeout: float,
    ):
        self.requests.append(request)
        self.timeouts.append(timeout)

        outcome = self.outcomes.pop(0)

        if isinstance(outcome, BaseException):
            raise outcome

        return outcome


def forbidden_error() -> HTTPError:
    return HTTPError(
        MALHA_PT_URL,
        403,
        "Forbidden",
        Message(),
        BytesIO(b"<html>challenge</html>"),
    )


class MalhaHttpTests(unittest.TestCase):
    def paths(
        self,
        root: Path,
    ) -> tuple[Path, Path]:
        return (
            root / "cache" / "malha.cookies",
            root / "cache" / "malha.json",
        )

    def test_valid_response_updates_cache_and_cookies(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cookie_path, cache_path = self.paths(root)
            payload = document_bytes()

            opener = FakeOpener(
                [
                    FakeResponse(
                        payload,
                        content_length=len(payload),
                    )
                ]
            )

            with patch(
                "mesh_noroeste.malha_http."
                "_build_cookie_opener",
                return_value=opener,
            ):
                result = fetch_malha_pt(
                    cookie_path=cookie_path,
                    cache_path=cache_path,
                )

            self.assertEqual(
                result.document["locations"],
                [],
            )
            self.assertEqual(result.attempts, 1)
            self.assertEqual(
                result.bytes_received,
                len(payload),
            )
            self.assertEqual(
                cache_path.read_bytes(),
                payload,
            )
            self.assertTrue(cookie_path.is_file())

            self.assertEqual(
                stat.S_IMODE(
                    cache_path.stat().st_mode
                ),
                0o644,
            )
            self.assertEqual(
                stat.S_IMODE(
                    cookie_path.stat().st_mode
                ),
                0o600,
            )

            request = opener.requests[0]

            self.assertEqual(
                request.get_header("Accept"),
                "application/json",
            )
            self.assertEqual(
                request.get_header(
                    "Accept-language"
                ),
                MALHA_ACCEPT_LANGUAGE,
            )
            self.assertEqual(
                request.get_header("User-agent"),
                MALHA_USER_AGENT,
            )
            self.assertEqual(
                opener.timeouts,
                [60.0],
            )

    def test_forbidden_response_is_retried_once(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cookie_path, cache_path = self.paths(root)
            payload = document_bytes()

            opener = FakeOpener(
                [
                    forbidden_error(),
                    FakeResponse(payload),
                ]
            )

            with patch(
                "mesh_noroeste.malha_http."
                "_build_cookie_opener",
                return_value=opener,
            ):
                result = fetch_malha_pt(
                    cookie_path=cookie_path,
                    cache_path=cache_path,
                )

            self.assertEqual(result.attempts, 2)
            self.assertEqual(len(opener.requests), 2)
            self.assertEqual(
                cache_path.read_bytes(),
                payload,
            )

    def test_second_forbidden_response_fails(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cookie_path, cache_path = self.paths(root)
            old_payload = document_bytes()
            cache_path.parent.mkdir(parents=True)
            cache_path.write_bytes(old_payload)

            opener = FakeOpener(
                [
                    forbidden_error(),
                    forbidden_error(),
                ]
            )

            with patch(
                "mesh_noroeste.malha_http."
                "_build_cookie_opener",
                return_value=opener,
            ):
                with self.assertRaisesRegex(
                    FetchError,
                    "Error HTTP 403",
                ):
                    fetch_malha_pt(
                        cookie_path=cookie_path,
                        cache_path=cache_path,
                    )

            self.assertEqual(
                cache_path.read_bytes(),
                old_payload,
            )
            self.assertEqual(len(opener.requests), 2)

    def test_invalid_json_preserves_existing_cache(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cookie_path, cache_path = self.paths(root)
            old_payload = document_bytes()
            cache_path.parent.mkdir(parents=True)
            cache_path.write_bytes(old_payload)

            opener = FakeOpener(
                [
                    FakeResponse(
                        b"<html>error</html>"
                    )
                ]
            )

            with patch(
                "mesh_noroeste.malha_http."
                "_build_cookie_opener",
                return_value=opener,
            ):
                with self.assertRaisesRegex(
                    FetchError,
                    "no contiene JSON válido",
                ):
                    fetch_malha_pt(
                        cookie_path=cookie_path,
                        cache_path=cache_path,
                    )

            self.assertEqual(
                cache_path.read_bytes(),
                old_payload,
            )

    def test_incomplete_document_is_not_cached(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cookie_path, cache_path = self.paths(root)

            opener = FakeOpener(
                [
                    FakeResponse(
                        b'{"locations":[]}'
                    )
                ]
            )

            with patch(
                "mesh_noroeste.malha_http."
                "_build_cookie_opener",
                return_value=opener,
            ):
                with self.assertRaisesRegex(
                    FetchError,
                    "traceroute_links",
                ):
                    fetch_malha_pt(
                        cookie_path=cookie_path,
                        cache_path=cache_path,
                    )

            self.assertFalse(cache_path.exists())

    def test_size_limit_preserves_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cookie_path, cache_path = self.paths(root)
            old_payload = document_bytes()
            cache_path.parent.mkdir(parents=True)
            cache_path.write_bytes(old_payload)

            opener = FakeOpener(
                [
                    FakeResponse(
                        b"x" * 101,
                        content_length=101,
                    )
                ]
            )

            with patch(
                "mesh_noroeste.malha_http."
                "_build_cookie_opener",
                return_value=opener,
            ):
                with self.assertRaisesRegex(
                    FetchError,
                    "supera el límite",
                ):
                    fetch_malha_pt(
                        cookie_path=cookie_path,
                        cache_path=cache_path,
                        max_bytes=100,
                    )

            self.assertEqual(
                cache_path.read_bytes(),
                old_payload,
            )

    def test_valid_cache_is_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cache_path = (
                Path(temporary) / "malha.json"
            )
            cache_path.write_bytes(document_bytes())

            document = load_malha_pt_cache(
                cache_path
            )

            self.assertEqual(document["locations"], [])
            self.assertEqual(
                document["traceroute_links"],
                [],
            )

    def test_missing_cache_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cache_path = (
                Path(temporary) / "missing.json"
            )

            with self.assertRaisesRegex(
                FetchError,
                "No existe una caché válida",
            ):
                load_malha_pt_cache(cache_path)

    def test_corrupt_cookie_file_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cookie_path, cache_path = self.paths(root)
            cookie_path.parent.mkdir(parents=True)
            cookie_path.write_text(
                "esto no es un archivo Netscape",
                encoding="utf-8",
            )

            with patch(
                "mesh_noroeste.malha_http."
                "_build_cookie_opener",
            ) as mocked_builder:
                with self.assertRaisesRegex(
                    FetchError,
                    "archivo de cookies",
                ):
                    fetch_malha_pt(
                        cookie_path=cookie_path,
                        cache_path=cache_path,
                    )

            mocked_builder.assert_not_called()

    def test_non_https_url_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cookie_path, cache_path = self.paths(root)

            with self.assertRaisesRegex(
                ValueError,
                "mediante HTTPS",
            ):
                fetch_malha_pt(
                    cookie_path=cookie_path,
                    cache_path=cache_path,
                    url=(
                        "http://malha.meshtastic.pt/"
                        "api/locations"
                    ),
                )


if __name__ == "__main__":
    unittest.main()
