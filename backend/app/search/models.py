"""
Core data models and shared utilities for the search layer.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

@dataclass
class SearchResult:
    """A single normalised search result from any engine."""

    url: str
    title: str
    snippet: str
    engine: str
    query: str
    # How many engines returned this same URL (filled in by the orchestrator)
    score: int = 1

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------

    @property
    def url_fingerprint(self) -> str:
        """
        Canonical URL fingerprint used for deduplication.

        Strips the scheme, strips trailing slashes, and lowercases the host so
        that ``http://Example.com/page`` and ``https://example.com/page/`` hash
        to the same key.
        """
        parsed = urlparse(self.url.lower().rstrip("/"))
        normalised = f"{parsed.netloc}{parsed.path}"
        if parsed.query:
            normalised += f"?{parsed.query}"
        return normalised

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "engine": self.engine,
            "query": self.query,
            "score": self.score,
        }


# ---------------------------------------------------------------------------
# Anti-bot detection
# ---------------------------------------------------------------------------

# Patterns that indicate an anti-bot / CAPTCHA page rather than real results.
_CAPTCHA_PATTERNS: list[re.Pattern] = [
    re.compile(r"captcha", re.I),
    re.compile(r"are you a (robot|human)", re.I),
    re.compile(r"unusual traffic", re.I),
    re.compile(r"automated (queries|requests)", re.I),
    re.compile(r"verify you.{0,20}human", re.I),
    re.compile(r"i.{0,5}m not a robot", re.I),
    re.compile(r"security check", re.I),
    re.compile(r"please enable javascript", re.I),
    re.compile(r"cf-browser-verification", re.I),   # Cloudflare
    re.compile(r"_Incapsula_Resource", re.I),        # Imperva
    re.compile(r"DDoS protection by", re.I),
]

# Minimum number of characters we expect in a real HTML response.
_MIN_CONTENT_LENGTH = 500


class BlockedResponseError(Exception):
    """Raised when an engine response looks like an anti-bot page."""

    def __init__(self, engine: str, status: int, reason: str) -> None:
        self.engine = engine
        self.status = status
        self.reason = reason
        super().__init__(f"[{engine}] blocked (HTTP {status}): {reason}")


def assert_not_blocked(engine: str, status_code: int, body: str) -> None:
    """
    Raise ``BlockedResponseError`` when the response looks like a block page.

    Called by each engine's ``_fetch`` method after receiving a 200-ish
    response so that the retry layer can treat it the same as a hard error.
    """
    if status_code == 429:
        raise BlockedResponseError(engine, status_code, "rate limited (429)")

    if status_code not in (200, 202):
        raise BlockedResponseError(engine, status_code, f"unexpected status {status_code}")

    if len(body) < _MIN_CONTENT_LENGTH:
        raise BlockedResponseError(engine, status_code, "response body suspiciously short")

    for pattern in _CAPTCHA_PATTERNS:
        if pattern.search(body):
            raise BlockedResponseError(engine, status_code, f"CAPTCHA/bot-detection pattern: {pattern.pattern}")
