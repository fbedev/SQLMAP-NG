from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlparse

import httpx

from app.models.http import HttpInteraction, HttpMethod, HttpRequestLog, HttpResponseLog


@dataclass(slots=True)
class HttpRequestSpec:
    url: str
    method: HttpMethod = HttpMethod.GET
    params: Optional[Dict[str, str]] = None
    data: Optional[Dict[str, str]] = None
    json_body: Optional[Dict[str, Any]] = None
    raw_body: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    content_type: Optional[str] = None
    timeout: float = 10.0


@dataclass(slots=True)
class ExecutionOptions:
    safe_mode: bool = True
    allowed_hosts: Iterable[str] = field(default_factory=list)


class HttpExecutionError(Exception):
    """Wraps transport/runtime errors thrown by the HTTP client."""


def _validate_host(url: str, allowed_hosts: Iterable[str]) -> None:
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        raise HttpExecutionError("Target URL must include a hostname")

    allowed = set(host.lower() for host in allowed_hosts if host)
    if allowed and host.lower() not in allowed:
        raise HttpExecutionError(f"Host '{host}' is not within the approved scope")


def _enforce_safe_mode(spec: HttpRequestSpec, safe_mode: bool) -> None:
    if not safe_mode:
        return
    if spec.method not in {HttpMethod.GET, HttpMethod.HEAD}:
        raise HttpExecutionError("Safe mode allows only GET or HEAD requests")
    if spec.data or spec.json_body or spec.raw_body:
        raise HttpExecutionError("Safe mode disallows request bodies")


def _excerpt(text: bytes | str, limit: int) -> str:
    if isinstance(text, bytes):
        try:
            text = text.decode("utf-8", errors="replace")
        except Exception:  # pragma: no cover - defensive fallback
            text = text.decode("latin-1", errors="replace")
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def execute_request(spec: HttpRequestSpec, options: ExecutionOptions) -> HttpInteraction:
    _validate_host(spec.url, options.allowed_hosts)
    _enforce_safe_mode(spec, options.safe_mode)

    request_headers = {"User-Agent": "SQLMap-Pro/0.1"}
    if spec.headers:
        request_headers.update(spec.headers)
    if spec.content_type:
        request_headers.setdefault("Content-Type", spec.content_type)

    try:
        start = perf_counter()
        with httpx.Client(timeout=spec.timeout, follow_redirects=True) as client:
            response = client.request(
                method=spec.method.value,
                url=spec.url,
                params=spec.params,
                data=spec.data,
                json=spec.json_body,
                content=spec.raw_body.encode("utf-8") if spec.raw_body is not None else None,
                headers=request_headers,
            )
        elapsed_ms = (perf_counter() - start) * 1000
    except httpx.HTTPError as exc:  # pragma: no cover - network errors are runtime events
        raise HttpExecutionError(str(exc)) from exc

    if spec.json_body is not None:
        body_repr = _excerpt(httpx.dumps_json(spec.json_body), 512)
    elif spec.raw_body is not None:
        body_repr = _excerpt(spec.raw_body, 512)
    elif spec.data is not None:
        body_repr = _excerpt(urlencode(spec.data), 512)
    else:
        body_repr = None

    request_log = HttpRequestLog(
        method=spec.method,
        url=str(response.request.url),
        params=dict(spec.params or {}),
        headers={k: v for k, v in response.request.headers.items()},
        content_type=response.request.headers.get("content-type"),
        body_excerpt=body_repr,
    )

    response_log = HttpResponseLog(
        status_code=response.status_code,
        elapsed_ms=elapsed_ms,
        headers={k: v for k, v in response.headers.items()},
        body_excerpt=_excerpt(response.content, 2048),
    )

    return HttpInteraction(request=request_log, response=response_log)
