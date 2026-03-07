"""
Shared HTTP client with connection pooling, UA rotation, and proxy support.

A single AsyncClient is created per async context (task or app lifetime) and
reused for all search requests. Callers obtain it via the ``get_client()``
context manager or by managing ``SearchHttpClient`` directly.
"""

from __future__ import annotations

import random
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import httpx

# ---------------------------------------------------------------------------
# Browser fingerprint pools
# ---------------------------------------------------------------------------

_USER_AGENTS: list[str] = [
    # Chrome / Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Chrome / macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Chrome / Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    # Firefox / Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) "
    "Gecko/20100101 Firefox/119.0",
    # Firefox / Linux
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) "
    "Gecko/20100101 Firefox/118.0",
    # Safari / macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    # Edge / Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    # Mobile Chrome / Android
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
]

_ACCEPT_LANGUAGES: list[str] = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.8,en-US;q=0.7",
    "en-US,en;q=0.5",
    "en,en-US;q=0.8",
    "en-AU,en;q=0.9",
]


def random_browser_headers() -> dict[str, str]:
    """Return a randomised but realistic set of browser request headers."""
    return {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": random.choice(_ACCEPT_LANGUAGES),
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

def _build_transport(proxy: Optional[str]) -> Optional[httpx.AsyncHTTPTransport]:
    """Return an AsyncHTTPTransport configured for the given proxy, or None."""
    if not proxy:
        return None
    return httpx.AsyncHTTPTransport(proxy=proxy)


def build_client(
    timeout: int = 15,
    proxy: Optional[str] = None,
    follow_redirects: bool = True,
) -> httpx.AsyncClient:
    """
    Build a reusable ``httpx.AsyncClient`` with sane defaults.

    The client uses a connection pool (httpx default: 100 connections, 20 per
    host), so it should be created *once* and shared across many requests.
    """
    limits = httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100,
        keepalive_expiry=30,
    )
    transport = _build_transport(proxy)
    return httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=follow_redirects,
        limits=limits,
        transport=transport,
    )


# ---------------------------------------------------------------------------
# Lifecycle-managed context manager
# ---------------------------------------------------------------------------

@asynccontextmanager
async def get_client(
    timeout: int = 15,
    proxy: Optional[str] = None,
) -> AsyncIterator[httpx.AsyncClient]:
    """
    Async context manager that yields a shared client and closes it on exit.

    Usage::

        async with get_client() as client:
            resp = await client.get(url, headers=random_browser_headers())
    """
    client = build_client(timeout=timeout, proxy=proxy)
    try:
        yield client
    finally:
        await client.aclose()
