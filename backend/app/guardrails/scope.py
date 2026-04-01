"""
Out-of-scope query detection guard (RC-90, RC-91).

Two-layer check:
1. Keyword blocklist — fast scan for known off-topic domain phrases.
2. Embedding cosine similarity vs FinSolve anchor — if the query
   embedding is too dissimilar from the anchor text, the query is
   likely off-topic (threshold < 0.35, configurable).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.config import settings

# ---------------------------------------------------------------------------
# Off-topic keyword blocklist (RC-90)
# ---------------------------------------------------------------------------

_OUT_OF_SCOPE_KEYWORDS: list[str] = [
    # General knowledge / internet queries
    "ai trends",
    "artificial intelligence trends",
    "machine learning trends",
    "latest in ai",
    "trending in tech",
    # Politics / news
    "politics",
    "election",
    "government policy",
    "president",
    "prime minister",
    "parliament",
    # Sports / entertainment
    "cricket",
    "football",
    "soccer",
    "sports",
    "world cup",
    "olympics",
    "movie",
    "celebrity",
    # Weather
    "weather",
    "forecast",
    "temperature today",
    # Competitor / general business
    "competitor analysis",
    "industry benchmark",
    "market research outside",
    # Cooking / lifestyle
    "recipe",
    "cooking",
    "how to cook",
    # Coding help (general)
    "write me a python script",
    "debug this code",
    "explain this algorithm",
    # Personal advice
    "personal advice",
    "relationship",
    "dating",
]

# ---------------------------------------------------------------------------
# Scope anchor embedding (RC-91)
# ---------------------------------------------------------------------------

_SCOPE_ANCHOR = (
    "FinSolve internal company financial HR engineering marketing documents "
    "employee policies quarterly reports business performance"
)

_anchor_embedding: list[float] | None = None


def _get_anchor_embedding() -> list[float]:
    """Lazily compute and cache the scope anchor embedding."""
    global _anchor_embedding
    if _anchor_embedding is None:
        from app.rag.embedder import get_embedder
        _anchor_embedding = get_embedder().embed_one(_SCOPE_ANCHOR)
    return _anchor_embedding


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class ScopeResult:
    blocked: bool
    reason: str | None = None  # "out_of_scope_rejected" when blocked


def check_scope(query: str) -> ScopeResult:
    """Return a :class:`ScopeResult` indicating whether the query is
    outside the FinSolve document scope.

    Keyword scan runs first (cheap); embedding similarity check runs
    only when no keyword match is found.
    """
    lower = query.lower()

    # Layer 1: keyword scan
    for phrase in _OUT_OF_SCOPE_KEYWORDS:
        if phrase in lower:
            return ScopeResult(blocked=True, reason="out_of_scope_rejected")

    # Layer 2: embedding similarity vs FinSolve anchor
    try:
        from app.rag.embedder import get_embedder
        query_emb = get_embedder().embed_one(query)
        anchor_emb = _get_anchor_embedding()
        sim = _cosine_similarity(query_emb, anchor_emb)
        if sim < settings.scope_similarity_threshold:
            return ScopeResult(blocked=True, reason="out_of_scope_rejected")
    except Exception:
        # Embedding check is best-effort; never block on error
        pass

    return ScopeResult(blocked=False)
