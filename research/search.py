"""Bounded, explicit retrieval. Search snippets are evidence, never instructions."""

import ipaddress
import json
import socket
import time
from pathlib import Path
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from research.models import SearchResult


class SearchUnavailable(RuntimeError):
    pass


class SearchAdapter(Protocol):
    mode: str

    def search(self, query: str, limit: int) -> list[SearchResult]: ...


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if (
        parts.scheme not in ("http", "https")
        or not parts.hostname
        or parts.username
        or parts.password
    ):
        raise ValueError("Only HTTP(S) URLs without credentials are accepted")
    host = parts.hostname.lower().encode("idna").decode("ascii")
    if host == "localhost" or host.endswith((".local", ".internal")):
        raise ValueError("Local sources are disallowed")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address and not address.is_global:
        raise ValueError("Non-public sources are disallowed")
    port = parts.port
    if port and port not in (80, 443):
        raise ValueError("Nonstandard source ports are disallowed")
    authority = f"[{host}]" if ":" in host else host
    if port and not (
        (port == 80 and parts.scheme == "http") or (port == 443 and parts.scheme == "https")
    ):
        authority += f":{port}"
    query = urlencode(
        sorted(
            (k, v)
            for k, v in parse_qsl(parts.query)
            if not k.lower().startswith("utm_") and k.lower() not in ("fbclid", "gclid")
        )
    )
    return urlunsplit((parts.scheme.lower(), authority, parts.path or "/", query, ""))


class FixtureSearch:
    mode = "offline"

    def __init__(self, path: Path | None = None, case: str = "corroboration"):
        path = path or Path(__file__).with_name("fixtures.json")
        self.case = json.loads(path.read_text(encoding="utf-8"))[case]
        self.calls = 0

    def search(self, query: str, limit: int) -> list[SearchResult]:
        self.calls += 1
        if self.case.get("failure"):
            raise SearchUnavailable("Fixture retrieval unavailable")
        return [SearchResult(**row, query=query) for row in self.case["sources"][:limit]]


class SerperSearch:
    """Search API excerpts only; arbitrary webpage URLs are never fetched."""

    mode = "web"
    endpoint = "https://google.serper.dev/search"

    def __init__(self, api_key: str, client: httpx.Client | None = None, sleep=time.sleep):
        if not api_key.strip():
            raise SearchUnavailable("Web mode requires a Serper search key")
        self._api_key = api_key
        self.client = client or httpx.Client(timeout=20, follow_redirects=False)
        self._owns_client = client is None
        self.sleep = sleep

    def close(self):
        if self._owns_client:
            self.client.close()

    def search(self, query: str, limit: int) -> list[SearchResult]:
        for attempt in range(3):
            try:
                with self.client.stream(
                    "POST",
                    self.endpoint,
                    headers={"X-API-KEY": self._api_key},
                    json={"q": query, "num": min(limit, 10)},
                ) as response:
                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt < 2:
                            self.sleep(0.5 * 2**attempt)
                            continue
                    response.raise_for_status()
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        raw.extend(chunk)
                        if len(raw) > 1_000_000:
                            raise SearchUnavailable("Search response exceeded size limit")
                data = json.loads(raw)
                if not isinstance(data, dict) or not isinstance(data.get("organic", []), list):
                    raise ValueError("Invalid search result schema")
                results = []
                for row in data.get("organic", [])[:limit]:
                    if not isinstance(row, dict):
                        raise ValueError("Invalid search result row")
                    if not row.get("snippet"):
                        continue
                    try:
                        results.append(
                            SearchResult(
                                url=normalize_url(row["link"]),
                                title=row["title"],
                                excerpt=row["snippet"][:20000],
                                query=query,
                            )
                        )
                    except (ValueError, KeyError):
                        continue
                return results
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt < 2:
                    self.sleep(0.5 * 2**attempt)
                    continue
                raise SearchUnavailable("Search network unavailable") from None
            except (httpx.HTTPStatusError, ValueError, KeyError, TypeError):
                raise SearchUnavailable(
                    "Search returned an invalid or unsuccessful response"
                ) from None
        raise SearchUnavailable("Search exhausted retries")


def local_ollama_url(url: str) -> str:
    parts = urlsplit(url)
    if (
        parts.scheme != "http"
        or parts.hostname not in ("localhost", "127.0.0.1", "::1")
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
        or parts.path not in ("", "/")
    ):
        raise ValueError("Ollama must use a loopback HTTP endpoint")
    # Fixed loopback hosts prevent arbitrary endpoint access through UI configuration.
    if parts.hostname == "localhost":
        for result in socket.getaddrinfo("localhost", parts.port or 80):
            if not ipaddress.ip_address(result[4][0]).is_loopback:
                raise ValueError("localhost did not resolve to loopback")
    return url.rstrip("/")
