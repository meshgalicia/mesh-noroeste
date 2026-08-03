"""Cliente HTTP limitado para obtener documentos JSON públicos."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_BYTES = 20 * 1024 * 1024
DEFAULT_USER_AGENT = "Mesh-Noroeste/0.1.0"


class FetchError(RuntimeError):
    """Error controlado al obtener o interpretar una fuente."""


@dataclass(frozen=True, slots=True)
class BinaryFetchResult:
    """Resultado de una descarga binaria."""

    payload: bytes
    requested_url: str
    final_url: str
    status: int
    content_type: str | None
    bytes_received: int


@dataclass(frozen=True, slots=True)
class JsonFetchResult:
    """Resultado de una descarga JSON."""

    document: Any
    requested_url: str
    final_url: str
    status: int
    content_type: str | None
    bytes_received: int


def _validated_url(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("La URL debe ser texto")

    normalized = value.strip()

    if not normalized:
        raise ValueError("La URL no puede estar vacía")

    parsed = urlsplit(normalized)

    if parsed.scheme.lower() != "https":
        raise ValueError(
            "Solo se admiten fuentes mediante HTTPS"
        )

    if parsed.hostname is None:
        raise ValueError(
            "La URL debe incluir un nombre de servidor"
        )

    if parsed.username is not None or parsed.password is not None:
        raise ValueError(
            "La URL no puede incluir credenciales"
        )

    if parsed.fragment:
        raise ValueError(
            "La URL de una fuente no puede incluir fragmentos"
        )

    return normalized


def _validated_timeout(value: float) -> float:
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


def _validated_max_bytes(value: int) -> int:
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


def _validated_user_agent(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(
            "El User-Agent debe ser texto"
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            "El User-Agent no puede estar vacío"
        )

    if "\r" in normalized or "\n" in normalized:
        raise ValueError(
            "El User-Agent no puede contener saltos de línea"
        )

    return normalized


def _validated_accept(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(
            "La cabecera Accept debe ser texto"
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            "La cabecera Accept no puede estar vacía"
        )

    if "\r" in normalized or "\n" in normalized:
        raise ValueError(
            "La cabecera Accept no puede contener "
            "saltos de línea"
        )

    return normalized


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
            "La respuesta supera el límite permitido: "
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
                "La respuesta HTTP no contiene bytes válidos"
            )

        total += len(chunk)

        if total > max_bytes:
            raise FetchError(
                "La respuesta supera el límite permitido "
                f"de {max_bytes} bytes"
            )

        chunks.append(chunk)

    return b"".join(chunks)


def fetch_bytes(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    user_agent: str = DEFAULT_USER_AGENT,
    accept: str = "application/octet-stream",
) -> BinaryFetchResult:
    """Obtiene un documento binario mediante HTTPS."""

    requested_url = _validated_url(url)
    normalized_timeout = _validated_timeout(timeout)
    normalized_max_bytes = _validated_max_bytes(
        max_bytes
    )
    normalized_user_agent = _validated_user_agent(
        user_agent
    )
    normalized_accept = _validated_accept(accept)

    request = Request(
        requested_url,
        headers={
            "Accept": normalized_accept,
            "User-Agent": normalized_user_agent,
        },
        method="GET",
    )

    try:
        with urlopen(
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
                    f"Respuesta HTTP inesperada: {status}"
                )

            payload = _read_limited(
                response,
                normalized_max_bytes,
            )

            content_type = response.headers.get(
                "Content-Type"
            )
            final_url = response.geturl()

            _validated_url(final_url)

    except HTTPError as exc:
        raise FetchError(
            f"Error HTTP {exc.code} al consultar "
            f"{requested_url}"
        ) from exc

    except URLError as exc:
        reason = getattr(exc, "reason", exc)

        raise FetchError(
            f"Error de red al consultar "
            f"{requested_url}: {reason}"
        ) from exc

    except TimeoutError as exc:
        raise FetchError(
            f"Tiempo de espera agotado al consultar "
            f"{requested_url}"
        ) from exc

    except OSError as exc:
        raise FetchError(
            f"Error del sistema al consultar "
            f"{requested_url}: {exc}"
        ) from exc

    return BinaryFetchResult(
        payload=payload,
        requested_url=requested_url,
        final_url=final_url,
        status=status,
        content_type=content_type,
        bytes_received=len(payload),
    )


def fetch_json(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    user_agent: str = DEFAULT_USER_AGENT,
) -> JsonFetchResult:
    """Obtiene y decodifica un documento JSON mediante HTTPS."""

    result = fetch_bytes(
        url,
        timeout=timeout,
        max_bytes=max_bytes,
        user_agent=user_agent,
        accept=(
            "application/json, "
            "application/geo+json, "
            "application/*+json"
        ),
    )

    try:
        text = result.payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FetchError(
            "La respuesta JSON no está codificada "
            "correctamente en UTF-8"
        ) from exc

    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FetchError(
            "La respuesta no contiene JSON válido: "
            f"línea {exc.lineno}, columna {exc.colno}: "
            f"{exc.msg}"
        ) from exc

    return JsonFetchResult(
        document=document,
        requested_url=result.requested_url,
        final_url=result.final_url,
        status=result.status,
        content_type=result.content_type,
        bytes_received=result.bytes_received,
    )
