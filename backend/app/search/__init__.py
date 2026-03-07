"""
app.search — public API for the search layer.

Import from here so the rest of the codebase is isolated from
internal module structure changes.
"""

from app.search.models import SearchResult, BlockedResponseError  # noqa: F401
from app.search.engines import ENGINE_REGISTRY  # noqa: F401
from app.search.orchestrator import SearchOrchestrator  # noqa: F401

__all__ = [
    "SearchOrchestrator",
    "SearchResult",
    "BlockedResponseError",
    "ENGINE_REGISTRY",
]
