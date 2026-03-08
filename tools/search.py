"""
Web search tool — Tavily (primary) → Exa (secondary) → Whoogle JSON (fallback).
Priority chain based on API key availability and result quality.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

import httpx

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import WHOOGLE_URL

logger = logging.getLogger(__name__)

NO_RESULTS_MESSAGE = (
    "Arama 0 sonuç döndürdü. Olası nedenler: "
    "Arama servisleri erişilemiyor veya sonuç vermedi. "
    "Farklı/İngilizce bir sorgu deneyin; .env içinde "
    "TAVILY_API_KEY, EXA_API_KEY veya WHOOGLE_URL kontrol edin."
)

BLOCKED_DOMAIN_PATTERNS = re.compile(
    r"xvideos\.com|jeuxvideo\.com|amerika-forum\.de|florarestaurantgroup\.com|"
    r"baidu\.com|zhidao\.baidu|orange\.fr/mail|cricketworldcup\.com|"
    r"forgeofempires\.com|tessl\.io",
    re.I,
)


def _blocked_domain(url: str) -> bool:
    return bool(BLOCKED_DOMAIN_PATTERNS.search(url or ""))


def _is_news_like_query(query: str) -> bool:
    q = (query or "").lower()
    news_terms = (
        "savaş", "war", "durum", "status", "current", "son", "latest",
        "gelişme", "tensions", "conflict", "2025", "2026", "news",
        "haber", "breaking",
    )
    return any(t in q for t in news_terms)


# ── Tavily (Primary) ─────────────────────────────────────────────

async def _search_tavily(
    query: str, max_results: int = 5
) -> list[dict[str, str]]:
    """Tavily API — LLM-optimized search. Requires TAVILY_API_KEY."""
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return []

    try:
        is_news = _is_news_like_query(query)
        payload: dict[str, Any] = {
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": False,
            "search_depth": "advanced" if is_news else "basic",
        }
        if is_news:
            payload["topic"] = "news"

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.tavily.com/search", json=payload
            )
            resp.raise_for_status()
            data = resp.json()

        results: list[dict[str, str]] = []
        for r in data.get("results", []):
            url = r.get("url", "")
            if _blocked_domain(url):
                continue
            results.append({
                "title": r.get("title", ""),
                "url": url,
                "snippet": r.get("content", "")[:500],
            })
        logger.info("Tavily returned %d results for: %s", len(results), query[:60])
        return results

    except Exception as exc:
        logger.warning("Tavily search failed: %s", exc)
        return []


# ── Exa (Secondary) ──────────────────────────────────────────────

async def _search_exa(
    query: str, max_results: int = 5
) -> list[dict[str, str]]:
    """Exa API — neural search with highlights. Requires EXA_API_KEY."""
    api_key = os.getenv("EXA_API_KEY", "").strip()
    if not api_key:
        return []

    try:
        from exa_py import AsyncExa

        exa = AsyncExa(api_key=api_key)
        search_result = await exa.search(
            query,
            num_results=max_results,
            contents={"highlights": {"max_characters": 4000}},
        )

        results: list[dict[str, str]] = []
        for r in search_result.results:
            url = getattr(r, "url", "")
            if _blocked_domain(url):
                continue
            # highlights → snippet
            highlights = getattr(r, "highlights", None) or []
            snippet = " ".join(highlights)[:500] if highlights else ""
            results.append({
                "title": getattr(r, "title", "") or "",
                "url": url,
                "snippet": snippet,
            })
        logger.info("Exa returned %d results for: %s", len(results), query[:60])
        return results

    except Exception as exc:
        logger.warning("Exa search failed: %s", exc)
        return []


# ── Whoogle JSON (Fallback) ──────────────────────────────────────

async def _search_whoogle(
    query: str, max_results: int = 5
) -> list[dict[str, str]]:
    """Whoogle format=json — self-hosted Google proxy. Needs session cookie."""
    if not WHOOGLE_URL:
        return []

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            # Step 1: get session cookie
            await client.get(WHOOGLE_URL)

            # Step 2: search with format=json
            resp = await client.get(
                f"{WHOOGLE_URL}/search",
                params={"q": query, "format": "json"},
            )
            resp.raise_for_status()
            data = resp.json()

        results: list[dict[str, str]] = []
        for r in data.get("results", [])[:max_results]:
            url = r.get("href", "")
            if _blocked_domain(url):
                continue
            results.append({
                "title": r.get("title", ""),
                "url": url,
                "snippet": (r.get("content") or r.get("text", ""))[:500],
            })
        logger.info("Whoogle returned %d results for: %s", len(results), query[:60])
        return results

    except Exception as exc:
        logger.warning("Whoogle search failed: %s", exc)
        return []


# ── Public API ───────────────────────────────────────────────────

async def web_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """
    Search chain: Tavily → Exa → Whoogle.
    Returns first provider that yields results.
    """
    # 1) Tavily
    results = await _search_tavily(query, max_results)
    if results:
        return results

    # 2) Exa
    results = await _search_exa(query, max_results)
    if results:
        return results

    # 3) Whoogle
    results = await _search_whoogle(query, max_results)
    if results:
        return results

    logger.warning("All search providers returned 0 results for: %s", query[:80])
    return []


def format_search_results(results: list[dict[str, str]]) -> str:
    """Format search results into readable text for LLM context."""
    if not results:
        return NO_RESULTS_MESSAGE

    lines: list[str] = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        snippet = r.get("snippet", "")
        lines.append(f"{i}. **{title}**\n   URL: {url}\n   {snippet}")
    return "\n\n".join(lines)
