"""
SearchOrchestrator
==================

The single entry point for all multi-engine search operations.

Responsibilities
----------------
* Own the lifecycle of the shared ``httpx.AsyncClient`` (startup / shutdown)
* Instantiate only the engines listed in ``Settings.enabled_engines_list``
* Manage a global semaphore to cap total concurrent HTTP requests
* Fan out a query to all enabled engines concurrently
* Merge, deduplicate, and score results from multiple engines
* Cache per-engine results so repeated queries are free

Lifecycle
---------
The orchestrator is designed to be used as an async context manager so the
underlying HTTP client and cache are closed cleanly::

    async with SearchOrchestrator() as orc:
        results = await orc.search_all_engines("site:example.com ext:env")

Alternatively, call ``startup()`` / ``shutdown()`` explicitly when managing
the lifecycle yourself (e.g. inside a Celery task that uses ``asynccontextmanager``).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.core.config import settings
from app.search.cache import SearchCache, build_cache
from app.search.engines import ENGINE_REGISTRY, BaseSearchEngine
from app.search.http_client import build_client
from app.search.models import SearchResult

import httpx

logger = logging.getLogger(__name__)


class SearchOrchestrator:
    """
    Fan-out search orchestrator with shared client, registry-driven engine
    selection, caching, and cross-engine scoring.
    """

    def __init__(
        self,
        enabled_engines: Optional[list[str]] = None,
        concurrency: Optional[int] = None,
        num_results: Optional[int] = None,
    ) -> None:
        # Accept overrides for testability; fall back to global settings
        self._engine_names: list[str] = (
            enabled_engines
            if enabled_engines is not None
            else settings.enabled_engines_list
        )
        self._concurrency: int = concurrency or settings.SEARCH_CONCURRENCY
        self._num_results: int = num_results or settings.RESULTS_PER_ENGINE

        # Set at startup
        self._client: Optional[httpx.AsyncClient] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._engines: list[BaseSearchEngine] = []
        self._cache: Optional[SearchCache] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def startup(self) -> None:
        """Initialise resources.  Call once before any searches."""
        self._client = build_client(
            timeout=settings.REQUEST_TIMEOUT,
            proxy=settings.HTTP_PROXY,
        )
        self._semaphore = asyncio.Semaphore(self._concurrency)
        self._cache = build_cache(
            backend=settings.CACHE_BACKEND,
            ttl=settings.CACHE_TTL_SECONDS,
            max_memory=settings.CACHE_MAX_MEMORY_ENTRIES,
            redis_url=settings.REDIS_URL,
        )
        self._engines = self._build_engines()
        logger.info(
            "SearchOrchestrator started — engines: [%s], concurrency: %d, cache: %s",
            ", ".join(e.name for e in self._engines),
            self._concurrency,
            settings.CACHE_BACKEND,
        )

    async def shutdown(self) -> None:
        """Release resources.  Call when done."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._cache:
            await self._cache.close()
            self._cache = None

    async def __aenter__(self) -> "SearchOrchestrator":
        await self.startup()
        return self

    async def __aexit__(self, *_) -> None:
        await self.shutdown()

    # ------------------------------------------------------------------
    # Public search API
    # ------------------------------------------------------------------

    async def search_all_engines(
        self, query: str, num_results: Optional[int] = None
    ) -> list[SearchResult]:
        """
        Run *query* on all enabled engines concurrently.

        Returns a merged, deduplicated list sorted by descending *score*
        (results that appear in multiple engines rank higher).
        """
        n = num_results or self._num_results
        tasks = [
            self._search_engine_cached(engine, query, n)
            for engine in self._engines
        ]
        per_engine: list[list[SearchResult] | BaseException] = await asyncio.gather(
            *tasks, return_exceptions=True
        )

        return self._merge_and_score(per_engine)

    async def search_engine(
        self, engine_name: str, query: str, num_results: Optional[int] = None
    ) -> list[SearchResult]:
        """
        Run *query* on a single named engine.

        Useful when the caller wants results from one specific engine or when
        doing GitHub-specific searches via Bing.
        """
        n = num_results or self._num_results
        engine = self._get_engine(engine_name)
        if engine is None:
            logger.warning("Engine '%s' is not enabled or unknown", engine_name)
            return []
        return await self._search_engine_cached(engine, query, n)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_engines(self) -> list[BaseSearchEngine]:
        """Instantiate enabled engines, sharing the single client and semaphore."""
        engines: list[BaseSearchEngine] = []
        for name in self._engine_names:
            cls = ENGINE_REGISTRY.get(name)
            if cls is None:
                logger.warning("Unknown engine '%s' in ENABLED_ENGINES — skipping", name)
                continue
            engines.append(
                cls(
                    client=self._client,
                    semaphore=self._semaphore,
                    delay_min=settings.SEARCH_DELAY_MIN,
                    delay_max=settings.SEARCH_DELAY_MAX,
                    max_retries=settings.MAX_RETRIES,
                )
            )
        if not engines:
            logger.error("No valid search engines configured — results will be empty")
        return engines

    def _get_engine(self, name: str) -> Optional[BaseSearchEngine]:
        for e in self._engines:
            if e.name == name:
                return e
        return None

    async def _search_engine_cached(
        self, engine: BaseSearchEngine, query: str, num_results: int
    ) -> list[SearchResult]:
        """Return cached results if available, otherwise fetch and cache."""
        cache_key = SearchCache.make_key(engine.name, query)

        if self._cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.debug("[%s] cache hit for: %.60s", engine.name, query)
                return cached[:num_results]

        results = await engine.search(query, num_results)

        if self._cache and results:
            await self._cache.set(cache_key, results)

        return results

    @staticmethod
    def _merge_and_score(
        per_engine: list[list[SearchResult] | BaseException],
    ) -> list[SearchResult]:
        """
        Merge results from multiple engines, deduplicate by URL fingerprint,
        and boost the score for URLs that appear in more than one engine.

        Sort order: descending score, then original discovery order.
        """
        # fingerprint → best SearchResult seen so far
        seen: dict[str, SearchResult] = {}

        for engine_results in per_engine:
            if isinstance(engine_results, BaseException):
                # Already logged inside the engine — swallow here
                continue
            for result in engine_results:
                fp = result.url_fingerprint
                if fp in seen:
                    seen[fp].score += 1
                    # Keep the richer snippet
                    if len(result.snippet) > len(seen[fp].snippet):
                        seen[fp].snippet = result.snippet
                else:
                    seen[fp] = result

        merged = list(seen.values())
        merged.sort(key=lambda r: r.score, reverse=True)
        return merged
