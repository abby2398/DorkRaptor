"""
DorkRaptor Search Engine Service
Handles multi-engine search with rate limiting, UA rotation, and retry logic
"""

import asyncio
import random
import logging
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urlencode
import re

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.8,en-US;q=0.7",
    "en-US,en;q=0.5",
    "en,en-US;q=0.8",
]


def get_random_headers() -> Dict[str, str]:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": random.choice(ACCEPT_LANGUAGES),
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
    }


class SearchResult:
    def __init__(self, url: str, title: str, snippet: str, engine: str, query: str):
        self.url = url
        self.title = title
        self.snippet = snippet
        self.engine = engine
        self.query = query

    def to_dict(self):
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "engine": self.engine,
            "query": self.query,
        }


class BingSearchEngine:
    """Bing search engine scraper"""

    BASE_URL = "https://www.bing.com/search"

    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        results = []
        params = {
            "q": query,
            "count": min(num_results, 50),
            "setlang": "en",
            "cc": "US",
        }

        try:
            async with httpx.AsyncClient(
                timeout=settings.REQUEST_TIMEOUT,
                follow_redirects=True,
                headers=get_random_headers(),
            ) as client:
                resp = await client.get(self.BASE_URL, params=params)
                if resp.status_code == 200:
                    results = self._parse_results(resp.text, query)
        except Exception as e:
            logger.warning(f"Bing search error for query '{query}': {e}")

        return results

    def _parse_results(self, html: str, query: str) -> List[SearchResult]:
        results = []
        soup = BeautifulSoup(html, "html.parser")

        for result in soup.select("li.b_algo")[:10]:
            title_tag = result.select_one("h2 a")
            snippet_tag = result.select_one("p, .b_caption p")

            if title_tag:
                title = title_tag.get_text(strip=True)
                url = title_tag.get("href", "")
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                if url and url.startswith("http"):
                    results.append(SearchResult(
                        url=url, title=title, snippet=snippet,
                        engine="bing", query=query
                    ))

        return results


class DuckDuckGoSearchEngine:
    """DuckDuckGo HTML search engine scraper"""

    BASE_URL = "https://html.duckduckgo.com/html/"

    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        results = []
        data = {"q": query, "b": "", "kl": "us-en"}

        try:
            async with httpx.AsyncClient(
                timeout=settings.REQUEST_TIMEOUT,
                follow_redirects=True,
                headers=get_random_headers(),
            ) as client:
                resp = await client.post(self.BASE_URL, data=data)
                if resp.status_code == 200:
                    results = self._parse_results(resp.text, query)
        except Exception as e:
            logger.warning(f"DuckDuckGo search error for query '{query}': {e}")

        return results[:num_results]

    def _parse_results(self, html: str, query: str) -> List[SearchResult]:
        results = []
        soup = BeautifulSoup(html, "html.parser")

        for result in soup.select(".result__body, .web-result"):
            title_tag = result.select_one(".result__a, .result__title a")
            url_tag = result.select_one(".result__url, .result__extras__url")
            snippet_tag = result.select_one(".result__snippet, .result__body p")

            if title_tag:
                title = title_tag.get_text(strip=True)
                href = title_tag.get("href", "")
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                # Extract real URL from DDG redirect
                url_match = re.search(r"uddg=([^&]+)", href)
                if url_match:
                    from urllib.parse import unquote
                    url = unquote(url_match.group(1))
                elif url_tag:
                    url = url_tag.get_text(strip=True)
                    if not url.startswith("http"):
                        url = "https://" + url
                else:
                    continue

                if url.startswith("http"):
                    results.append(SearchResult(
                        url=url, title=title, snippet=snippet,
                        engine="duckduckgo", query=query
                    ))

        return results


class GoogleSearchEngine:
    """Google search engine scraper (via requests)"""

    BASE_URL = "https://www.google.com/search"

    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        results = []
        params = {
            "q": query,
            "num": min(num_results, 10),
            "hl": "en",
            "gl": "us",
        }

        try:
            async with httpx.AsyncClient(
                timeout=settings.REQUEST_TIMEOUT,
                follow_redirects=True,
                headers=get_random_headers(),
            ) as client:
                resp = await client.get(self.BASE_URL, params=params)
                if resp.status_code == 200:
                    results = self._parse_results(resp.text, query)
        except Exception as e:
            logger.warning(f"Google search error for query '{query}': {e}")

        return results

    def _parse_results(self, html: str, query: str) -> List[SearchResult]:
        results = []
        soup = BeautifulSoup(html, "html.parser")

        # Google search result containers
        for div in soup.select("div.g, div[data-sokoban-container]"):
            title_tag = div.select_one("h3")
            link_tag = div.select_one("a[href]")
            snippet_tag = div.select_one(".VwiC3b, .s3v9rd, span[style]")

            if title_tag and link_tag:
                title = title_tag.get_text(strip=True)
                href = link_tag.get("href", "")
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                # Filter out Google's own URLs
                if href.startswith("/url?q="):
                    url = href.split("/url?q=")[1].split("&")[0]
                    from urllib.parse import unquote
                    url = unquote(url)
                elif href.startswith("http"):
                    url = href
                else:
                    continue

                if url.startswith("http") and "google.com" not in url:
                    results.append(SearchResult(
                        url=url, title=title, snippet=snippet,
                        engine="google", query=query
                    ))

        return results[:num_results]


class SearchOrchestrator:
    """Orchestrates searches across multiple engines with rate limiting"""

    def __init__(self):
        self.bing = BingSearchEngine()
        self.ddg = DuckDuckGoSearchEngine()
        self.google = GoogleSearchEngine()
        self._semaphore = asyncio.Semaphore(3)

    async def search_with_delay(self, engine_name: str, query: str) -> List[SearchResult]:
        """Search with randomized delay to avoid rate limiting"""
        async with self._semaphore:
            delay = random.uniform(settings.SEARCH_DELAY_MIN, settings.SEARCH_DELAY_MAX)
            await asyncio.sleep(delay)

            for attempt in range(settings.MAX_RETRIES):
                try:
                    if engine_name == "bing":
                        return await self.bing.search(query)
                    elif engine_name == "duckduckgo":
                        return await self.ddg.search(query)
                    elif engine_name == "google":
                        return await self.google.search(query)
                except Exception as e:
                    logger.warning(f"Attempt {attempt+1} failed for {engine_name}: {e}")
                    if attempt < settings.MAX_RETRIES - 1:
                        await asyncio.sleep(2 ** attempt)

            return []

    async def search_all_engines(self, query: str) -> List[SearchResult]:
        """Run query on all enabled search engines"""
        tasks = [
            self.search_with_delay("bing", query),
            self.search_with_delay("duckduckgo", query),
            # Google is rate-limited more aggressively, use selectively
            # self.search_with_delay("google", query),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_results = []
        seen_urls = set()

        for result_list in results:
            if isinstance(result_list, list):
                for r in result_list:
                    if r.url not in seen_urls:
                        seen_urls.add(r.url)
                        all_results.append(r)

        return all_results
