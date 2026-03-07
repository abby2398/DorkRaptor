"""
DorkRaptor GitHub Leak Detection Service
Scans GitHub for exposed secrets and credentials related to target domain
"""

import logging
from typing import List, Dict, Optional
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.dorks.database import GITHUB_DORKS

logger = logging.getLogger(__name__)


class GitHubLeakScanner:
    """Scans GitHub for domain-related leaks"""

    SEARCH_URL = "https://api.github.com/search/code"
    WEB_SEARCH_URL = "https://github.com/search"

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.GITHUB_TOKEN

    def _get_headers(self) -> Dict:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def scan_domain(self, domain: str) -> List[Dict]:
        """Scan GitHub for leaks related to the domain"""
        results = []

        if self.token:
            # Use GitHub API if token is available
            api_results = await self._api_search(domain)
            results.extend(api_results)
        else:
            # Fall back to web scraping
            web_results = await self._web_search(domain)
            results.extend(web_results)

        return results

    async def _api_search(self, domain: str) -> List[Dict]:
        """Search using GitHub API (requires token)"""
        results = []
        queries = [
            f'"{domain}" password',
            f'"{domain}" api_key',
            f'"{domain}" secret',
            f'"{domain}" access_token',
        ]

        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            for query in queries[:4]:  # Rate limit: 4 queries
                try:
                    resp = await client.get(
                        self.SEARCH_URL,
                        headers=self._get_headers(),
                        params={"q": query, "per_page": 10},
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data.get("items", []):
                            results.append({
                                "url": item.get("html_url", ""),
                                "title": f"GitHub: {item.get('name', 'Unknown file')} in {item.get('repository', {}).get('full_name', '')}",
                                "snippet": f"Potential leak found in GitHub repository. File: {item.get('path', '')}",
                                "dork_query": query,
                                "source": "github",
                                "category": "github_leaks",
                                "raw_data": {
                                    "repository": item.get("repository", {}).get("full_name"),
                                    "file_path": item.get("path"),
                                    "sha": item.get("sha"),
                                },
                            })
                    elif resp.status_code == 403:
                        logger.warning("GitHub API rate limit reached")
                        break
                except Exception as e:
                    logger.warning(f"GitHub API search error: {e}")

        return results

    async def _web_search(self, domain: str) -> List[Dict]:
        """Web-based GitHub search (no token required, limited)."""
        results = []

        github_queries = [
            f'site:github.com "{domain}" password',
            f'site:github.com "{domain}" api_key',
            f'site:github.com "{domain}" secret',
        ]

        from app.search import SearchOrchestrator
        async with SearchOrchestrator(enabled_engines=["bing"]) as orchestrator:
            for query in github_queries[:3]:
                try:
                    search_results = await orchestrator.search_engine("bing", query, num_results=5)
                    for r in search_results:
                        if "github.com" in r.url:
                            results.append({
                                "url": r.url,
                                "title": r.title,
                                "snippet": r.snippet,
                                "dork_query": query,
                                "source": "github",
                                "category": "github_leaks",
                            })
                except Exception as e:
                    logger.warning(f"GitHub web search error: {e}")

        return results


class CloudExposureScanner:
    """Scans for exposed cloud storage buckets and endpoints"""

    async def scan_domain(self, domain: str) -> List[Dict]:
        """Check for exposed cloud storage buckets"""
        from app.dorks.database import CLOUD_BUCKETS
        results = []

        # Generate bucket candidates
        buckets = [b.replace("{domain}", domain.replace(".", "-")) for b in CLOUD_BUCKETS]
        base_domain = domain.split(".")[0]
        buckets.extend([
            f"{base_domain}.s3.amazonaws.com",
            f"{base_domain}-backup.s3.amazonaws.com",
            f"{base_domain}-data.s3.amazonaws.com",
            f"{base_domain}-dev.s3.amazonaws.com",
        ])

        async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
            for bucket_url in buckets[:20]:  # Check first 20 candidates
                if not bucket_url.startswith("http"):
                    bucket_url = f"https://{bucket_url}"
                try:
                    resp = await client.head(bucket_url)
                    if resp.status_code in [200, 403]:
                        # 200 = public, 403 = exists but private
                        status = "PUBLIC" if resp.status_code == 200 else "PRIVATE (exists)"
                        results.append({
                            "url": bucket_url,
                            "title": f"Cloud Storage Bucket: {status}",
                            "snippet": f"Cloud storage endpoint found at {bucket_url}. Status: {status}",
                            "dork_query": f"cloud bucket scan: {bucket_url}",
                            "source": "cloud_scan",
                            "category": "cloud_storage",
                            "severity": "critical" if resp.status_code == 200 else "medium",
                        })
                except Exception:
                    pass  # Bucket doesn't exist or not reachable

        return results
