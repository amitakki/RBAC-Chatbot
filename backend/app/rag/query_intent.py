"""Query intent detection: classify as structured (listing/filtering) or semantic."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

# Regex patterns for detecting structured/listing queries
_STRUCTURED_PATTERNS = [
    r'\b(list|show|give\s+me|get|fetch|display|find)\s+(all|every|each)\b',
    r'\ball\s+\w+\s+(with|and)\b',
    r'\bwho\s+are\s+(all|the)\b',
    r'\bhow\s+many\b',
    r'\bcount\s+(all|the)\b',
]

# Pattern to extract entity/value from structured query
_ENTITY_PATTERN = (
    r'(?:list|show|give\s+me|get|find|all)\s+(?:all\s+)?([A-Za-z\s]+?)'
    r'(?:\s+(?:with|and|their|in|from|at|by)|$)'
)


@dataclass
class QueryIntent:
    """Represents the intent and extracted entity from a user query."""

    intent: Literal["structured", "semantic"]
    entity: str | None = None


def detect_intent(query: str) -> QueryIntent:
    """
    Detect and classify a query as structured (listing/filtering) or semantic.

    Structured queries match patterns like:
    - "List all Marketing Managers with their locations"
    - "Show all employees in Finance"
    - "How many HR Managers are there"

    Returns:
        QueryIntent with intent classification and extracted entity (if structured).
    """
    q_lower = query.lower().strip()

    # Check if query matches any structured pattern
    is_structured = any(re.search(pat, q_lower) for pat in _STRUCTURED_PATTERNS)

    if not is_structured:
        return QueryIntent(intent="semantic", entity=None)

    # Structured query detected — try to extract the entity
    entity = _extract_entity(query)
    return QueryIntent(intent="structured", entity=entity)


# Alias for backward compatibility
classify_intent = detect_intent


def _extract_entity(query: str) -> str | None:
    """
    Extract the entity (role, department, etc.) from a structured query.

    Examples:
    - "List all Marketing Managers with their locations" → "Marketing Manager"
    - "Show all employees in Finance" → "Finance"
    - "How many HR Managers are there" → "HR Manager"

    Returns:
        Normalized entity string, or None if extraction fails.
    """
    q_lower = query.lower()

    # Try pattern-based extraction
    match = re.search(_ENTITY_PATTERN, q_lower)
    if match:
        entity_raw = match.group(1).strip()
        # Normalize: plurals to singular, title case
        entity_normalized = _normalize_entity(entity_raw)
        if entity_normalized:
            return entity_normalized

    return None


def _normalize_entity(entity_raw: str) -> str | None:
    """Normalize entity string: handle plurals, case, whitespace.

    Examples:
    - "marketing managers" → "marketing manager"
    - "finance  department" → "finance"
    """
    if not entity_raw:
        return None

    # Strip extra whitespace
    s = " ".join(entity_raw.split()).strip()

    # Remove trailing "department/team/group/members" noise
    s = re.sub(r'\s+(department|team|group|members|staff|employees)$', '', s)

    # Handle common plural forms: "managers" → "manager"
    if s.endswith("s"):
        # Heuristic: if it's a job title ending in "s", try singular form
        s_singular = s[:-1]
        # Keep the singular form (e.g., "Marketing Manager" not "Marketing Managers")
        s = s_singular

    return s if s else None
