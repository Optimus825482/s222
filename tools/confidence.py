"""
Confidence scoring system — heuristic analysis for multi-agent outputs.
No LLM calls. Uses regex, keyword detection, and structural analysis
to assign confidence scores and detect contradictions.
"""

from __future__ import annotations

import re
from typing import Any


# ── Constants ────────────────────────────────────────────────────

URL_PATTERN = re.compile(
    r"https?://[^\s\)\]\},\"'<>]+",
    re.IGNORECASE,
)

# Assumption indicators (TR + EN)
ASSUMPTION_PHRASES = [
    "muhtemelen", "probably", "likely", "büyük ihtimalle",
    "assuming", "varsayarak", "varsayıyorum", "tahminimce",
    "olabilir", "might", "perhaps", "belki", "possibly",
    "sanırım", "I think", "I believe", "düşünüyorum",
    "tahminen", "approximately", "yaklaşık olarak",
]

# Caveat / limitation indicators (TR + EN)
CAVEAT_PHRASES = [
    "ancak", "however", "but", "dikkat", "note that",
    "limitation", "sınırlama", "uyarı", "warning", "caveat",
    "bununla birlikte", "öte yandan", "on the other hand",
    "risk", "dezavantaj", "downside", "trade-off", "tradeoff",
    "dikkat edilmeli", "göz önünde bulundur",
]

# Specificity boosters — presence of these increases specificity score
SPECIFICITY_PATTERNS = [
    re.compile(r"\b\d{4}\b"),                    # years
    re.compile(r"\b\d+[.,]\d+\b"),               # decimals
    re.compile(r"\b\d+%"),                        # percentages
    re.compile(r"\b\d+\s*(ms|MB|GB|KB|fps)\b"),  # metrics with units
    re.compile(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)+\b"),  # proper nouns
]

# Positive / negative stance keywords for contradiction detection
POSITIVE_STANCE = [
    "iyi", "good", "great", "excellent", "başarılı", "successful",
    "önerilir", "recommended", "avantaj", "advantage", "benefit",
    "etkili", "effective", "verimli", "efficient", "uygun", "suitable",
    "güçlü", "strong", "robust", "ideal", "best", "en iyi",
]

NEGATIVE_STANCE = [
    "kötü", "bad", "poor", "başarısız", "failed", "unsuccessful",
    "önerilmez", "not recommended", "dezavantaj", "disadvantage",
    "etkisiz", "ineffective", "verimsiz", "inefficient", "uygun değil",
    "zayıf", "weak", "fragile", "worst", "en kötü", "avoid", "kaçın",
]



# ── Helpers ──────────────────────────────────────────────────────

def _extract_urls(text: str) -> list[str]:
    """Extract all URLs from text."""
    return URL_PATTERN.findall(text)


def _detect_phrases(text: str, phrases: list[str]) -> list[str]:
    """Find which phrases from the list appear in text (case-insensitive)."""
    text_lower = text.lower()
    return [p for p in phrases if p.lower() in text_lower]


def _calc_specificity(text: str) -> float:
    """
    Score 0-1 based on presence of specific data points:
    numbers, dates, proper nouns, metrics.
    """
    if not text:
        return 0.0

    hits = sum(1 for pat in SPECIFICITY_PATTERNS if pat.search(text))
    # Normalize: 0 hits = 0.2 base, 5+ hits = 1.0
    return min(0.2 + (hits * 0.16), 1.0)


def _calc_consistency(text: str) -> float:
    """
    Internal consistency: penalize self-contradictions.
    Looks for patterns like "X is good ... X is bad" within same text.
    """
    if not text or len(text) < 100:
        return 0.5

    sentences = re.split(r"[.!?\n]+", text)
    if len(sentences) < 2:
        return 0.7

    # Check for contradictory stance within same output
    has_positive = any(p in text.lower() for p in POSITIVE_STANCE[:6])
    has_negative = any(n in text.lower() for n in NEGATIVE_STANCE[:6])

    if has_positive and has_negative:
        # Could be nuanced analysis (good) or contradiction (bad)
        # If structured with headers/bullets, likely nuanced → higher score
        if any(m in text for m in ["##", "- ", "* ", "1."]):
            return 0.8  # structured comparison
        return 0.5  # unstructured mixed signals

    return 0.85


def _calc_length_quality(text: str) -> float:
    """Score based on response length appropriateness."""
    length = len(text)
    if length < 100:
        return 0.2
    if length < 200:
        return 0.5
    if length <= 3000:
        return 1.0
    if length <= 5000:
        return 0.85
    return 0.7  # overly verbose


# ── Public API ───────────────────────────────────────────────────

def score_confidence(
    output: str,
    agent_role: str,
    task_type: str,
) -> dict[str, Any]:
    """
    Analyze agent output and assign a confidence score using heuristics.

    Args:
        output: The agent's text output.
        agent_role: Role identifier (e.g. "speed", "researcher").
        task_type: Task classification (e.g. "research", "coding").

    Returns:
        Structured confidence assessment with score, factors, sources,
        and detected assumptions.
    """
    if not output or not output.strip():
        return {
            "confidence_score": 0.0,
            "confidence_level": "low",
            "factors": {
                "has_sources": False,
                "has_caveats": False,
                "specificity": 0.0,
                "consistency": 0.0,
                "length_quality": 0.0,
            },
            "sources_used": [],
            "assumptions_made": [],
        }

    sources = _extract_urls(output)
    assumptions = _detect_phrases(output, ASSUMPTION_PHRASES)
    caveats = _detect_phrases(output, CAVEAT_PHRASES)

    has_sources = len(sources) > 0
    has_caveats = len(caveats) > 0
    specificity = _calc_specificity(output)
    consistency = _calc_consistency(output)
    length_quality = _calc_length_quality(output)

    # Weighted confidence calculation
    weights: dict[str, float] = {
        "specificity": 0.25,
        "consistency": 0.25,
        "length_quality": 0.20,
        "sources_bonus": 0.15,
        "caveats_bonus": 0.10,
        "assumptions_penalty": 0.05,
    }

    raw_score = (
        specificity * weights["specificity"]
        + consistency * weights["consistency"]
        + length_quality * weights["length_quality"]
        + (0.9 if has_sources else 0.3) * weights["sources_bonus"]
        + (0.8 if has_caveats else 0.4) * weights["caveats_bonus"]
        - (min(len(assumptions) * 0.1, 0.5)) * weights["assumptions_penalty"]
    )

    # Role-based adjustments
    if agent_role == "researcher" and has_sources:
        raw_score += 0.05  # researchers with sources get a boost
    if task_type == "coding" and "```" in output:
        raw_score += 0.05  # code tasks with code blocks

    confidence_score = round(max(0.0, min(1.0, raw_score)), 3)

    # Map to level
    if confidence_score >= 0.85:
        level = "very_high"
    elif confidence_score >= 0.65:
        level = "high"
    elif confidence_score >= 0.40:
        level = "medium"
    else:
        level = "low"

    return {
        "confidence_score": confidence_score,
        "confidence_level": level,
        "factors": {
            "has_sources": has_sources,
            "has_caveats": has_caveats,
            "specificity": round(specificity, 3),
            "consistency": round(consistency, 3),
            "length_quality": round(length_quality, 3),
        },
        "sources_used": sources,
        "assumptions_made": assumptions,
    }


def detect_contradictions(results: dict[str, str]) -> list[dict[str, Any]]:
    """
    Detect contradictions between multiple agent outputs.

    Args:
        results: Mapping of agent_role -> output text.

    Returns:
        List of detected contradictions with involved agents and details.
    """
    if len(results) < 2:
        return []

    contradictions: list[dict[str, Any]] = []
    roles = list(results.keys())

    for i in range(len(roles)):
        for j in range(i + 1, len(roles)):
            role_a, role_b = roles[i], roles[j]
            text_a, text_b = results[role_a].lower(), results[role_b].lower()

            # Check for opposing stances on overlapping topics
            a_positive = [w for w in POSITIVE_STANCE if w in text_a]
            a_negative = [w for w in NEGATIVE_STANCE if w in text_a]
            b_positive = [w for w in POSITIVE_STANCE if w in text_b]
            b_negative = [w for w in NEGATIVE_STANCE if w in text_b]

            # Find shared topic keywords (words appearing in both outputs)
            words_a = set(re.findall(r"\b\w{4,}\b", text_a))
            words_b = set(re.findall(r"\b\w{4,}\b", text_b))
            shared_topics = words_a & words_b

            # Remove common stop words from shared topics
            stop_words = {
                "this", "that", "with", "from", "have", "been", "will",
                "would", "could", "should", "about", "their", "which",
                "there", "these", "those", "than", "then", "when", "what",
                "olan", "için", "daha", "gibi", "olan", "olar", "bile",
            }
            shared_topics -= stop_words

            if not shared_topics:
                continue

            # Detect stance contradiction: A positive + B negative (or vice versa)
            if (a_positive and b_negative) or (a_negative and b_positive):
                # Determine severity based on overlap
                overlap_ratio = len(shared_topics) / max(len(words_a | words_b), 1)
                severity = (
                    "high" if overlap_ratio > 0.3
                    else "medium" if overlap_ratio > 0.15
                    else "low"
                )

                contradictions.append({
                    "agents": [role_a, role_b],
                    "type": "stance_conflict",
                    "severity": severity,
                    "shared_topics": sorted(list(shared_topics))[:10],
                    "detail": (
                        f"{role_a} leans "
                        f"{'positive' if a_positive else 'negative'}, "
                        f"{role_b} leans "
                        f"{'positive' if b_positive else 'negative'} "
                        f"on overlapping topics."
                    ),
                })

    return contradictions


def weighted_synthesis_scores(
    results: dict[str, dict[str, Any]],
) -> dict[str, float]:
    """
    Calculate synthesis weight per agent based on confidence data.

    Args:
        results: Mapping of agent_role -> confidence assessment dict
                 (output of score_confidence).

    Returns:
        Mapping of agent_role -> normalized weight (0-1, sums to ~1.0).
    """
    if not results:
        return {}

    raw_weights: dict[str, float] = {}

    for role, conf in results.items():
        score = conf.get("confidence_score", 0.5)
        factors = conf.get("factors", {})

        # Boost agents with sources and high specificity
        source_bonus = 0.1 if factors.get("has_sources") else 0.0
        specificity_bonus = factors.get("specificity", 0.5) * 0.1

        raw_weights[role] = score + source_bonus + specificity_bonus

    # Normalize so weights sum to 1.0
    total = sum(raw_weights.values())
    if total == 0:
        # Equal weights fallback
        n = len(results)
        return {role: 1.0 / n for role in results}

    return {
        role: round(w / total, 3)
        for role, w in raw_weights.items()
    }
