"""Acceso HTTP específico a Malha con cookies y caché."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from http.cookiejar import (
    LoadError,
    MozillaCookieJar,
)
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPCookieProcessor,
    Request,
    build_opener,
)

from mesh_noroeste.http_client import (
    DEFAULT_MAX_BYTES,
    FetchError,
)


MALHA_PT_URL = (
    "https://malha.meshtastic.pt/api/locations"
)
MALHA_TIMEOUT_SECONDS = 60.0
MALHA_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/138.0.0.0 Safari/537.36"
)
MALHA_ACCEPT_LANGUAGE = (
    "pt-PT,pt;q=0.9,en;q=0.8"
)


@dataclass(frozen=True, slots=True)
class MalhaFetchResult:
    """Resultado de una descarga validada de Malha."""

    document: Mapping[str, Any]
    requested_url: str
    final_url: str
    status: int
    content_type: str | None
    bytes_received: int
    attempts: int
    cookie_path: Path
    cache_path: Path


def _validated_url(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("La URL debe ser texto")

    normalized = value.strip()

    if not normalized:
        raise ValueError("La URL no puede estar vacía")

    parsed = urlsplit(normalized)

    if parsed.scheme.lower() != "https":
        raise ValueError(
            "Solo se admite Malha mediante HTTPS"
        )

    if parsed.hostname is None:
        raise ValueError(
            "La URL debe incluir un servidor"
        )

    if (
        parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(
            "La URL no puede incluir credenciales"
        )

    if parsed.fragment:
        raise ValueError(
            "La URL no puede incluir fragmentos"
        )

    return normalized


def _positive_timeout(value: float) -> float:
    if isinstance(value, bool):
        raise ValueError(
            "El tiempo de espera no puede ser booleano"
        )

    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "El tiempo de espera debe ser numérico"
        ) from exc

    if not math.isfinite(normalized) or normalized <= 0:
        raise ValueError(
            "El tiempo de espera debe ser mayor que cero"
        )

    return normalized


def _positive_max_bytes(value: int) -> int:
    if isinstance(value, bool):
        raise ValueError(
            "El límite de tamaño no puede ser booleano"
        )

    if not isinstance(value, int):
        raise TypeError(
            "El límite de tamaño debe ser un entero"
        )

    if value < 1:
        raise ValueError(
            "El límite de tamaño debe ser mayor que cero"
        )

    return value


def _validated_path(
    value: Path | str,
    description: str,
) -> Path:
    try:
        path = Path(value).expanduser().resolve()
    except TypeError as exc:
        raise TypeError(
            f"{description} debe ser una ruta"
        ) from exc

    if path.exists() and not path.is_file():
        raise ValueError(
            f"{description} no puede ser un directorio"
        )

    return path


def _content_length(response: Any) -> int | None:
    raw_value = response.headers.get("Content-Length")

    if raw_value is None:
        return None

    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return None

    if parsed < 0:
        return None

    return parsed


def _read_limited(
    response: Any,
    max_bytes: int,
) -> bytes:
    content_length = _content_length(response)

    if (
        content_length is not None
        and content_length > max_bytes
    ):
        raise FetchError(
            "La respuesta de Malha supera el límite: "
            f"{content_length} bytes frente a {max_bytes}"
        )

    chunks: list[bytes] = []
    total = 0

    while True:
        chunk = response.read(
            min(64 * 1024, max_bytes - total + 1)
        )

        if not chunk:
            break

        if not isinstance(chunk, bytes):
            raise FetchError(
                "La respuesta de Malha no contiene "
                "bytes válidos"
            )

        total += len(chunk)

        if total > max_bytes:
            raise FetchError(
                "La respuesta de Malha supera el límite "
                f"de {max_bytes} bytes"
            )

        chunks.append(chunk)

    return b"".join(chunks)


def _decode_document(
    payload: bytes,
) -> Mapping[str, Any]:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FetchError(
            "La respuesta de Malha no está codificada "
            "correctamente en UTF-8"
        ) from exc

    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FetchError(
            "La respuesta de Malha no contiene JSON "
            f"válido: línea {exc.lineno}, "
            f"columna {exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(document, Mapping):
        raise FetchError(
            "La raíz JSON de Malha debe ser un objeto"
        )

    if not isinstance(
        document.get("locations"),
        list,
    ):
        raise FetchError(
            "Malha debe incluir una lista 'locations'"
        )

    if not isinstance(
        document.get("traceroute_links"),
        list,
    ):
        raise FetchError(
            "Malha debe incluir una lista "
            "'traceroute_links'"
        )

    return document


def _temporary_path(
    destination: Path,
) -> Path:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    os.close(descriptor)

    return Path(temporary_name)


def _write_cache_atomically(
    cache_path: Path,
    payload: bytes,
) -> None:
    temporary_path = _temporary_path(cache_path)

    try:
        with temporary_path.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        temporary_path.chmod(0o644)
        os.replace(temporary_path, cache_path)

    except OSError as exc:
        raise FetchError(
            f"No se pudo guardar la caché de Malha: {exc}"
        ) from exc

    finally:
        temporary_path.unlink(missing_ok=True)


def _load_cookie_jar(
    cookie_path: Path,
) -> MozillaCookieJar:
    jar = MozillaCookieJar(str(cookie_path))

    if not cookie_path.exists():
        return jar

    try:
        jar.load(
            ignore_discard=True,
            ignore_expires=True,
        )
    except (LoadError, OSError) as exc:
        raise FetchError(
            "No se pudo leer el archivo de cookies "
            f"de Malha: {exc}"
        ) from exc

    return jar


def _save_cookie_jar(
    jar: MozillaCookieJar,
    cookie_path: Path,
) -> None:
    temporary_path = _temporary_path(cookie_path)

    try:
        jar.save(
            str(temporary_path),
            ignore_discard=True,
            ignore_expires=True,
        )
        temporary_path.chmod(0o600)
        os.replace(temporary_path, cookie_path)

    except OSError as exc:
        raise FetchError(
            "No se pudo guardar el archivo de cookies "
            f"de Malha: {exc}"
        ) from exc

    finally:
        temporary_path.unlink(missing_ok=True)


def _build_cookie_opener(
    jar: MozillaCookieJar,
) -> Any:
    return build_opener(
        HTTPCookieProcessor(jar)
    )


def load_malha_pt_cache(
    cache_path: Path | str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> Mapping[str, Any]:
    """Lee y valida la última caché persistente de Malha."""

    resolved_cache_path = _validated_path(
        cache_path,
        "La ruta de caché",
    )
    normalized_max_bytes = _positive_max_bytes(
        max_bytes
    )

    if not resolved_cache_path.is_file():
        raise FetchError(
            "No existe una caché válida de Malha en "
            f"{resolved_cache_path}"
        )

    try:
        size = resolved_cache_path.stat().st_size

        if size > normalized_max_bytes:
            raise FetchError(
                "La caché de Malha supera el límite: "
                f"{size} bytes frente a "
                f"{normalized_max_bytes}"
            )

        payload = resolved_cache_path.read_bytes()

    except OSError as exc:
        raise FetchError(
            f"No se pudo leer la caché de Malha: {exc}"
        ) from exc

    return _decode_document(payload)


def fetch_malha_pt(
    *,
    cookie_path: Path | str,
    cache_path: Path | str,
    url: str = MALHA_PT_URL,
    timeout: float = MALHA_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    user_agent: str = MALHA_USER_AGENT,
    accept_language: str = MALHA_ACCEPT_LANGUAGE,
) -> MalhaFetchResult:
    """Descarga Malha, conserva cookies y actualiza la caché."""

    requested_url = _validated_url(url)
    normalized_timeout = _positive_timeout(timeout)
    normalized_max_bytes = _positive_max_bytes(
        max_bytes
    )
    resolved_cookie_path = _validated_path(
        cookie_path,
        "La ruta de cookies",
    )
    resolved_cache_path = _validated_path(
        cache_path,
        "La ruta de caché",
    )

    if not isinstance(user_agent, str):
        raise TypeError("El User-Agent debe ser texto")

    normalized_user_agent = user_agent.strip()

    if (
        not normalized_user_agent
        or "\r" in normalized_user_agent
        or "\n" in normalized_user_agent
    ):
        raise ValueError(
            "El User-Agent no es válido"
        )

    if not isinstance(accept_language, str):
        raise TypeError(
            "Accept-Language debe ser texto"
        )

    normalized_accept_language = (
        accept_language.strip()
    )

    if (
        not normalized_accept_language
        or "\r" in normalized_accept_language
        or "\n" in normalized_accept_language
    ):
        raise ValueError(
            "Accept-Language no es válido"
        )

    jar = _load_cookie_jar(
        resolved_cookie_path
    )
    opener = _build_cookie_opener(jar)

    request = Request(
        requested_url,
        headers={
            "Accept": "application/json",
            "Accept-Language": (
                normalized_accept_language
            ),
            "User-Agent": normalized_user_agent,
        },
        method="GET",
    )

    for attempt in (1, 2):
        try:
            with opener.open(
                request,
                timeout=normalized_timeout,
            ) as response:
                status = getattr(
                    response,
                    "status",
                    response.getcode(),
                )

                if not 200 <= status < 300:
                    raise FetchError(
                        "Respuesta HTTP inesperada de "
                        f"Malha: {status}"
                    )

                payload = _read_limited(
                    response,
                    normalized_max_bytes,
                )
                final_url = response.geturl()
                _validated_url(final_url)
                content_type = response.headers.get(
                    "Content-Type"
                )

            document = _decode_document(payload)

            _save_cookie_jar(
                jar,
                resolved_cookie_path,
            )
            _write_cache_atomically(
                resolved_cache_path,
                payload,
            )

            return MalhaFetchResult(
                document=document,
                requested_url=requested_url,
                final_url=final_url,
                status=status,
                content_type=content_type,
                bytes_received=len(payload),
                attempts=attempt,
                cookie_path=resolved_cookie_path,
                cache_path=resolved_cache_path,
            )

        except HTTPError as exc:
            code = exc.code

            try:
                _save_cookie_jar(
                    jar,
                    resolved_cookie_path,
                )
            finally:
                exc.close()

            if code == 403 and attempt == 1:
                continue

            raise FetchError(
                f"Error HTTP {code} al consultar "
                f"{requested_url}"
            ) from exc

        except URLError as exc:
            reason = getattr(exc, "reason", exc)

            raise FetchError(
                "Error de red al consultar Malha: "
                f"{reason}"
            ) from exc

        except TimeoutError as exc:
            raise FetchError(
                "Tiempo de espera agotado al consultar "
                "Malha"
            ) from exc

        except OSError as exc:
            raise FetchError(
                "Error del sistema al consultar Malha: "
                f"{exc}"
            ) from exc

    raise AssertionError(
        "El bucle de descarga de Malha terminó "
        "sin resultado"
    )
