"""
Backwards-compatibility shim.

All search logic has moved to ``app.search``.
This module re-exports the public API so any existing imports continue to work.
"""
from app.search import SearchOrchestrator, SearchResult, ENGINE_REGISTRY  # noqa: F401
from app.search.engines import BingEngine as BingSearchEngine  # noqa: F401
from app.search.engines import DuckDuckGoEngine as DuckDuckGoSearchEngine  # noqa: F401
from app.search.engines import GoogleEngine as GoogleSearchEngine  # noqa: F401

__all__ = [
    "SearchOrchestrator",
    "SearchResult",
    "ENGINE_REGISTRY",
    "BingSearchEngine",
    "DuckDuckGoSearchEngine",
    "GoogleSearchEngine",
]
