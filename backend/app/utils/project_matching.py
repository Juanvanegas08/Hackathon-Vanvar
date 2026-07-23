"""Project name normalization and matching helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.constants import PROJECT_NAME_STOPWORDS
from app.utils.normalization import normalize_for_comparison


def normalize_project_name(value: str | None) -> str | None:
    """Normalize a project name for comparison."""
    normalized = normalize_for_comparison(value)
    if normalized is None:
        return None
    cleaned = re.sub(r"[^a-z0-9\s]", " ", normalized)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or None


def significant_tokens(value: str | None) -> set[str]:
    """Extract meaningful tokens from a project or location string."""
    normalized = normalize_project_name(value)
    if normalized is None:
        return set()
    return {
        token
        for token in normalized.split(" ")
        if token and token not in PROJECT_NAME_STOPWORDS and len(token) > 2
    }


def core_project_key(value: str | None) -> str | None:
    """Build a compact key from significant tokens."""
    tokens = sorted(significant_tokens(value))
    if not tokens:
        return normalize_project_name(value)
    return " ".join(tokens)


@dataclass(frozen=True, slots=True)
class MatchDecision:
    """Result of comparing two project names."""

    kind: str  # exact | approximate | ambiguous | none
    score: float
    left: str
    right: str


def compare_project_names(left: str, right: str) -> MatchDecision:
    """Compare two project names with conservative approximate matching."""
    left_norm = normalize_project_name(left)
    right_norm = normalize_project_name(right)
    if not left_norm or not right_norm:
        return MatchDecision("none", 0.0, left, right)

    if left_norm == right_norm:
        return MatchDecision("exact", 1.0, left, right)

    left_core = core_project_key(left)
    right_core = core_project_key(right)
    if left_core and right_core and left_core == right_core:
        return MatchDecision("exact", 0.98, left, right)

    left_tokens = significant_tokens(left)
    right_tokens = significant_tokens(right)
    if not left_tokens or not right_tokens:
        return MatchDecision("none", 0.0, left, right)

    intersection = left_tokens & right_tokens
    union = left_tokens | right_tokens
    jaccard = len(intersection) / len(union)

    # Clear containment of distinctive tokens (e.g. MONGUI vs Agrupación ... Monguí).
    smaller, larger = (
        (left_tokens, right_tokens)
        if len(left_tokens) <= len(right_tokens)
        else (right_tokens, left_tokens)
    )
    containment = smaller.issubset(larger) and len(smaller) >= 1
    distinctive = any(len(token) >= 5 for token in smaller)

    if containment and distinctive and jaccard >= 0.34:
        return MatchDecision("approximate", max(0.85, jaccard), left, right)
    if jaccard >= 0.75 and len(intersection) >= 2:
        return MatchDecision("approximate", jaccard, left, right)
    if jaccard >= 0.5 and len(intersection) == 1 and distinctive:
        # Single-token overlap can be ambiguous across similar names.
        return MatchDecision("ambiguous", jaccard, left, right)
    return MatchDecision("none", jaccard, left, right)


def text_overlap_score(query: str | None, target: str | None) -> float:
    """Score textual overlap between a lead preference and a project field."""
    query_tokens = significant_tokens(query)
    target_tokens = significant_tokens(target)
    if not query_tokens or not target_tokens:
        # Fallback: substring check on normalized text.
        q = normalize_project_name(query)
        t = normalize_project_name(target)
        if q and t and (q in t or t in q):
            return 0.8
        return 0.0
    intersection = query_tokens & target_tokens
    if not intersection:
        q = normalize_project_name(query)
        t = normalize_project_name(target)
        if q and t and (q in t or t in q):
            return 0.75
        return 0.0
    return len(intersection) / max(len(query_tokens), 1)
