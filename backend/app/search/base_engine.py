"""
Abstract base class for all search engine implementations.

Every engine inherits from ``BaseSearchEngine`` and only needs to implement:
  * ``name``          — str property  (e.g. ``"bing"``)
  * ``_fetch``        — issue the HTTP request, return raw HTML body
  * ``_parse``        — parse the HTML body into a list of SearchResult

All cross-cutting concerns — retry with exponential back-off, randomised
delay, anti-bot detection, per-engine semaphore, request header rotation —
are handled here so engines stay thin and focused on parsing.
"""

from __future__ import annotations

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from app.search.http_client import random_browser_headers
from app.search.models import BlockedResponseError, SearchResult, assert_not_blocked

logger = logging.getLogger(__name__)


class BaseSearchEngine(ABC):
    """
    Base class for all search engine scrapers.

    Parameters
    ----------
    client:
        A shared ``httpx.AsyncClient`` injected by the orchestrator.
        Using a shared client gives us connection pooling and keeps the
        number of open TCP connections predictable.
    semaphore:
        Optional asyncio semaphore to bound overall concurrency.  If
        ``None`` the engine acquires no lock before issuing a request.
    delay_min / delay_max:
        Seconds to wait before each request (jittered).
    max_retries:
        How many times to retry a failed or blocked request.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        semaphore: Optional[asyncio.Semaphore] = None,
        delay_min: float = 2.0,
        delay_max: float = 5.0,
        max_retries: int = 3,
    ) -> None:
        self._client = client
        self._semaphore = semaphore or asyncio.Semaphore(999)  # effectively unlimited
        self._delay_min = delay_min
        self._delay_max = delay_max
        self._max_retries = max_retries

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique lowercase identifier, e.g. ``"bing"``."""

    async def search(self, query: str, num_results: int = 10) -> list[SearchResult]:
        """
        Execute *query* and return up to *num_results* deduplicated results.

        Handles retries, delays, and anti-bot detection transparently.
        """
        async with self._semaphore:
            return await self._search_with_retry(query, num_results)

    # ------------------------------------------------------------------
    # Engine contract — subclasses implement these two methods only
    # ------------------------------------------------------------------

    @abstractmethod
    async def _fetch(self, query: str, num_results: int) -> str:
        """
        Issue the HTTP request and return the raw response body.

        Should raise ``httpx.HTTPError`` or ``BlockedResponseError`` on
        failure so the retry layer in ``_search_with_retry`` catches it.
        """

    @abstractmethod
    def _parse(self, html: str, query: str, num_results: int) -> list[SearchResult]:
        """
        Parse *html* into a list of ``SearchResult`` objects, capped at
        *num_results*.
        """

    # ------------------------------------------------------------------
    # Retry / delay logic (shared, not overrideable by subclasses)
    # ------------------------------------------------------------------

    async def _search_with_retry(
        self, query: str, num_results: int
    ) -> list[SearchResult]:
        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries):
            # Jittered delay — always wait, but back off further on retries
            base_delay = random.uniform(self._delay_min, self._delay_max)
            backoff = base_delay * (2 ** attempt)
            await asyncio.sleep(min(backoff, 30))   # cap at 30 s

            try:
                html = await self._fetch(query, num_results)
                assert_not_blocked(self.name, 200, html)  # raises BlockedResponseError
                results = self._parse(html, query, num_results)
                if attempt > 0:
                    logger.info(
                        "[%s] succeeded on attempt %d for query: %.60s",
                        self.name, attempt + 1, query,
                    )
                return results

            except BlockedResponseError as exc:
                last_error = exc
                logger.warning(
                    "[%s] anti-bot response on attempt %d/%d: %s — backing off",
                    self.name, attempt + 1, self._max_retries, exc.reason,
                )

            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(
                    "[%s] timeout on attempt %d/%d",
                    self.name, attempt + 1, self._max_retries,
                )

            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code
                logger.warning(
                    "[%s] HTTP %d on attempt %d/%d",
                    self.name, status, attempt + 1, self._max_retries,
                )
                if status in (403, 429):
                    # Hard block — don't hammer, wait longer
                    await asyncio.sleep(5 * (attempt + 1))

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "[%s] unexpected error on attempt %d/%d: %s",
                    self.name, attempt + 1, self._max_retries, exc,
                )

        logger.error(
            "[%s] all %d attempts failed for query: %.60s — last error: %s",
            self.name, self._max_retries, query, last_error,
        )
        return []

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _fresh_headers(self) -> dict[str, str]:
        """Return a fresh set of randomised browser headers."""
        return random_browser_headers()
