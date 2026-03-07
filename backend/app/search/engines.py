"""
Concrete search engine implementations.

Each class is thin: it only knows how to talk to one specific search engine
and how to parse its HTML.  All retry/delay/anti-bot logic lives in
``BaseSearchEngine``.

Adding a new engine is as simple as:
    1. Create a class that inherits BaseSearchEngine
    2. Implement ``name``, ``_fetch``, and ``_parse``
    3. Register it in the ENGINE_REGISTRY dict at the bottom of this file
"""

from __future__ import annotations

import re
from urllib.parse import unquote

from bs4 import BeautifulSoup

from app.search.base_engine import BaseSearchEngine
from app.search.models import BlockedResponseError, SearchResult, assert_not_blocked


# ---------------------------------------------------------------------------
# Bing
# ---------------------------------------------------------------------------

class BingEngine(BaseSearchEngine):
    """Bing web search via HTML scraping."""

    BASE_URL = "https://www.bing.com/search"

    @property
    def name(self) -> str:
        return "bing"

    async def _fetch(self, query: str, num_results: int) -> str:
        params = {
            "q": query,
            "count": min(num_results, 50),
            "setlang": "en",
            "cc": "US",
            "form": "QBLH",
        }
        resp = await self._client.get(
            self.BASE_URL,
            params=params,
            headers=self._fresh_headers(),
        )
        # Raise so the retry layer catches non-200 responses
        resp.raise_for_status()
        body = resp.text
        # Run anti-bot check at the HTTP level (status already checked above)
        assert_not_blocked(self.name, resp.status_code, body)
        return body

    def _parse(self, html: str, query: str, num_results: int) -> list[SearchResult]:
        soup = BeautifulSoup(html, "lxml")
        results: list[SearchResult] = []

        for li in soup.select("li.b_algo"):
            a_tag = li.select_one("h2 a")
            snippet_tag = li.select_one(".b_caption p, p")

            if not a_tag:
                continue

            url = a_tag.get("href", "")
            if not url.startswith("http"):
                continue

            title = a_tag.get_text(strip=True)
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

            results.append(
                SearchResult(url=url, title=title, snippet=snippet, engine=self.name, query=query)
            )
            if len(results) >= num_results:
                break

        return results


# ---------------------------------------------------------------------------
# DuckDuckGo
# ---------------------------------------------------------------------------

class DuckDuckGoEngine(BaseSearchEngine):
    """DuckDuckGo HTML endpoint (no JS required)."""

    BASE_URL = "https://html.duckduckgo.com/html/"

    @property
    def name(self) -> str:
        return "duckduckgo"

    async def _fetch(self, query: str, num_results: int) -> str:
        data = {"q": query, "b": "", "kl": "us-en"}
        resp = await self._client.post(
            self.BASE_URL,
            data=data,
            headers=self._fresh_headers(),
        )
        resp.raise_for_status()
        body = resp.text
        assert_not_blocked(self.name, resp.status_code, body)
        return body

    def _parse(self, html: str, query: str, num_results: int) -> list[SearchResult]:
        soup = BeautifulSoup(html, "lxml")
        results: list[SearchResult] = []

        for div in soup.select(".result__body, .web-result"):
            title_tag = div.select_one(".result__a, .result__title a")
            snippet_tag = div.select_one(".result__snippet, .result__body p")

            if not title_tag:
                continue

            href = title_tag.get("href", "")
            url = self._extract_ddg_url(href, div)
            if not url:
                continue

            title = title_tag.get_text(strip=True)
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

            results.append(
                SearchResult(url=url, title=title, snippet=snippet, engine=self.name, query=query)
            )
            if len(results) >= num_results:
                break

        return results

    @staticmethod
    def _extract_ddg_url(href: str, container) -> str:
        """
        DDG wraps real URLs in a redirect.  Try to extract the original URL
        from the ``uddg`` query-string param, falling back to the visible URL.
        """
        m = re.search(r"uddg=([^&]+)", href)
        if m:
            url = unquote(m.group(1))
            if url.startswith("http"):
                return url

        # Fallback: visible URL element
        url_tag = container.select_one(".result__url, .result__extras__url")
        if url_tag:
            url = url_tag.get_text(strip=True)
            if not url.startswith("http"):
                url = "https://" + url
            return url

        return ""


# ---------------------------------------------------------------------------
# Google
# ---------------------------------------------------------------------------

class GoogleEngine(BaseSearchEngine):
    """
    Google web search via HTML scraping.

    Google aggressively blocks scrapers so this engine is disabled by default
    (not listed in ``ENABLED_ENGINES``).  It is included for completeness and
    for use when a proxy is configured.
    """

    BASE_URL = "https://www.google.com/search"

    @property
    def name(self) -> str:
        return "google"

    async def _fetch(self, query: str, num_results: int) -> str:
        params = {
            "q": query,
            "num": min(num_results, 10),
            "hl": "en",
            "gl": "us",
        }
        resp = await self._client.get(
            self.BASE_URL,
            params=params,
            headers=self._fresh_headers(),
        )
        resp.raise_for_status()
        body = resp.text
        assert_not_blocked(self.name, resp.status_code, body)
        return body

    def _parse(self, html: str, query: str, num_results: int) -> list[SearchResult]:
        soup = BeautifulSoup(html, "lxml")
        results: list[SearchResult] = []

        for div in soup.select("div.g, div[data-sokoban-container]"):
            h3 = div.select_one("h3")
            a_tag = div.select_one("a[href]")
            snippet_tag = div.select_one(".VwiC3b, .s3v9rd, span[style]")

            if not (h3 and a_tag):
                continue

            href = a_tag.get("href", "")
            url = self._extract_google_url(href)
            if not url:
                continue

            title = h3.get_text(strip=True)
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

            results.append(
                SearchResult(url=url, title=title, snippet=snippet, engine=self.name, query=query)
            )
            if len(results) >= num_results:
                break

        return results

    @staticmethod
    def _extract_google_url(href: str) -> str:
        if href.startswith("/url?q="):
            url = href.split("/url?q=")[1].split("&")[0]
            url = unquote(url)
        elif href.startswith("http"):
            url = href
        else:
            return ""

        if "google.com" in url:
            return ""

        return url


# ---------------------------------------------------------------------------
# Engine registry
# ---------------------------------------------------------------------------

# Maps lowercase engine name → engine *class* (not instance).
# To add a new engine: create a class above and add it here.
ENGINE_REGISTRY: dict[str, type[BaseSearchEngine]] = {
    "bing": BingEngine,
    "duckduckgo": DuckDuckGoEngine,
    "google": GoogleEngine,
}
