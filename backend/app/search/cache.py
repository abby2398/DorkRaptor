"""
Optional result cache for search queries.

Supports three backends, configured via ``Settings.CACHE_BACKEND``:

* ``"redis"``   — stores results in Redis as JSON blobs (requires REDIS_URL)
* ``"memory"``  — simple in-process TTL dict (no extra deps, reset on restart)
* ``"none"``    — caching disabled

The cache key is ``search:<engine>:<sha256(query)>`` so the same query on
different engines is stored independently.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import asdict
from typing import Optional

from app.search.models import SearchResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class SearchCache(ABC):
    """Interface all cache backends must implement."""

    @abstractmethod
    async def get(self, key: str) -> Optional[list[SearchResult]]:
        """Return cached results or None if missing / expired."""

    @abstractmethod
    async def set(self, key: str, results: list[SearchResult]) -> None:
        """Store results under *key*."""

    @abstractmethod
    async def close(self) -> None:
        """Release underlying resources."""

    # ------------------------------------------------------------------
    # Shared key builder
    # ------------------------------------------------------------------

    @staticmethod
    def make_key(engine: str, query: str) -> str:
        q_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        return f"search:{engine}:{q_hash}"


# ---------------------------------------------------------------------------
# No-op backend
# ---------------------------------------------------------------------------

class NullCache(SearchCache):
    async def get(self, key: str) -> None:
        return None

    async def set(self, key: str, results: list[SearchResult]) -> None:
        pass

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# In-memory TTL backend
# ---------------------------------------------------------------------------

class MemoryCache(SearchCache):
    """
    Thread-safe, in-process TTL cache backed by a plain dict.

    Entries are evicted lazily on access and proactively when the store
    exceeds *max_entries* (oldest-first eviction).
    """

    def __init__(self, ttl_seconds: int = 3600, max_entries: int = 2000) -> None:
        self._ttl = ttl_seconds
        self._max = max_entries
        # {key: (expires_at, payload)}
        self._store: dict[str, tuple[float, list[dict]]] = {}

    async def get(self, key: str) -> Optional[list[SearchResult]]:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, payload = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return [SearchResult(**r) for r in payload]

    async def set(self, key: str, results: list[SearchResult]) -> None:
        if len(self._store) >= self._max:
            self._evict()
        self._store[key] = (
            time.monotonic() + self._ttl,
            [r.to_dict() for r in results],
        )

    async def close(self) -> None:
        self._store.clear()

    def _evict(self) -> None:
        """Remove the oldest 10 % of entries to make room."""
        n = max(1, len(self._store) // 10)
        oldest = sorted(self._store.items(), key=lambda kv: kv[1][0])[:n]
        for k, _ in oldest:
            del self._store[k]


# ---------------------------------------------------------------------------
# Redis backend
# ---------------------------------------------------------------------------

class RedisCache(SearchCache):
    """
    Cache backed by Redis.  Uses the ``redis`` async client that is already
    a project dependency (redis==5.0.1 ships with async support).
    """

    def __init__(self, redis_url: str, ttl_seconds: int = 3600) -> None:
        self._url = redis_url
        self._ttl = ttl_seconds
        self._client = None  # lazily initialised

    async def _ensure_client(self):
        if self._client is None:
            import redis.asyncio as aioredis  # type: ignore
            self._client = await aioredis.from_url(self._url, decode_responses=True)

    async def get(self, key: str) -> Optional[list[SearchResult]]:
        try:
            await self._ensure_client()
            raw = await self._client.get(key)
            if raw is None:
                return None
            data = json.loads(raw)
            return [SearchResult(**r) for r in data]
        except Exception as exc:
            logger.warning("Redis cache get error: %s", exc)
            return None

    async def set(self, key: str, results: list[SearchResult]) -> None:
        try:
            await self._ensure_client()
            payload = json.dumps([r.to_dict() for r in results])
            await self._client.setex(key, self._ttl, payload)
        except Exception as exc:
            logger.warning("Redis cache set error: %s", exc)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_cache(backend: str, ttl: int, max_memory: int, redis_url: str) -> SearchCache:
    """
    Return the appropriate ``SearchCache`` implementation.

    ``backend`` is compared case-insensitively and must be one of
    ``"redis"``, ``"memory"``, or ``"none"``.
    """
    b = backend.lower()
    if b == "redis":
        logger.info("Search cache: Redis (ttl=%ds)", ttl)
        return RedisCache(redis_url=redis_url, ttl_seconds=ttl)
    if b == "memory":
        logger.info("Search cache: in-memory (ttl=%ds, max=%d)", ttl, max_memory)
        return MemoryCache(ttl_seconds=ttl, max_entries=max_memory)
    logger.info("Search cache: disabled")
    return NullCache()
