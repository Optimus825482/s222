"""
Web search tool — Tavily (optional) or SearXNG. Used by Research Agent (GLM 4.7).
When TAVILY_API_KEY is set, Tavily is tried first for higher-quality, LLM-oriented results.
"""

from __future__ import annotations

import logging
import os
import re

import httpx

# Direct import to avoid circular/package issues in Streamlit
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import SEARXNG_URL

logger = logging.getLogger(__name__)

# Message returned when no results (SearXNG unreachable or all filtered)
NO_RESULTS_MESSAGE = (
    "Arama 0 sonuç döndürdü. Olası nedenler: "
    "SEARXNG_URL erişilemiyor veya arama motorları kapalı. "
    "Farklı/İngilizce bir sorgu deneyin; .env içinde TAVILY_API_KEY veya SEARXNG_URL kontrol edin."
)

# Domains to exclude from SearXNG results (noise: adult, gaming, unrelated forums)
BLOCKED_DOMAIN_PATTERNS = re.compile(
    r"xvideos\.com|jeuxvideo\.com|amerika-forum\.de|florarestaurantgroup\.com|"
    r"baidu\.com|zhidao\.baidu|orange\.fr/mail|cricketworldcup\.com|"
    r"forgeofempires\.com|tessl\.io",
    re.I,
)


def _is_news_like_query(query: str) -> bool:
    """Heuristic: treat as news/current-events for Tavily topic=news."""
    q = (query or "").lower()
    news_terms = (
        "savaş", "war", "durum", "status", "current", "son", "latest", "gelişme",
        "tensions", "conflict", "2025", "2026", "news", "haber", "breaking",
    )
    return any(t in q for t in news_terms)


def _blocked_domain(url: str) -> bool:
    """True if URL belongs to a blocked (noise) domain."""
    if not url:
        return False
    return bool(BLOCKED_DOMAIN_PATTERNS.search(url))


def _parse_searxng_results(data: dict, max_results: int) -> list[dict]:
    """Extract results from SearXNG JSON; filter by blocked domains."""
    results = []
    raw = data.get("results") or data.get("answers") or []
    for item in raw:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or item.get("link") or ""
        if _blocked_domain(url):
            continue
        title = item.get("title") or item.get("name") or ""
        snippet = (item.get("content") or item.get("snippet") or item.get("description") or "")[:500]
        if title or url or snippet:
            results.append({"title": title, "url": url, "snippet": snippet})
        if len(results) >= max_results:
            break
    return results


async def _search_tavily(query: str, max_results: int) -> list[dict] | None:
    """Try Tavily search; return list of {title, url, snippet} or None on failure."""
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from tavily import AsyncTavilyClient
    except ImportError:
        logger.debug("tavily-python not installed; skipping Tavily")
        return None
    try:
        client = AsyncTavilyClient(api_key=api_key)
        topic = "news" if _is_news_like_query(query) else "general"
        resp = await client.search(
            query=query[:400],
            max_results=max_results,
            search_depth="advanced",
            topic=topic,
        )
        results = []
        for r in (resp.get("results") or [])[:max_results]:
            results.append({
                "title": r.get("title") or "",
                "url": r.get("url") or "",
                "snippet": (r.get("content") or r.get("score", ""))[:500],
            })
        if results:
            logger.info("Tavily returned %d results for query (topic=%s)", len(results), topic)
            return results
    except Exception as e:
        logger.warning("Tavily search failed: %s", e)
    return None


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search via Tavily (if TAVILY_API_KEY set) then SearXNG; return structured results."""
    # Prefer Tavily when configured — better relevance for research/news
    tavily_results = await _search_tavily(query, max_results)
    if tavily_results:
        return tavily_results

    if not SEARXNG_URL:
        return [{"title": "Arama hatası", "url": "", "snippet": "SEARXNG_URL boş; TAVILY_API_KEY da ayarlı değil."}]

    # SearXNG fallback; filter out blocked domains
    params_list = [
        {"q": query, "format": "json", "engines": "bing,startpage,mojeek", "language": "auto", "safesearch": 0},
        {"q": query, "format": "json", "language": "auto", "safesearch": 0},
        {"q": query, "format": "json", "engines": "google,duckduckgo,brave", "language": "auto", "safesearch": 0},
    ]
    last_error = None
    for params in params_list:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{SEARXNG_URL}/search", params=params)
                resp.raise_for_status()
                data = resp.json()
            results = _parse_searxng_results(data, max_results)
            if results:
                return results
            last_error = None
        except Exception as e:
            last_error = e
            logger.warning("SearXNG request failed: %s", e)
    if last_error:
        return [{"title": "Arama hatası", "url": "", "snippet": f"{type(last_error).__name__}: {last_error}"}]
    return [{"title": "Sonuç yok", "url": "", "snippet": NO_RESULTS_MESSAGE}]


def format_search_results(results: list[dict]) -> str:
    """Format search results for LLM context injection."""
    if not results:
        return (
            "<search_results>\n  No results found. "
            "Check TAVILY_API_KEY or SEARXNG_URL in .env.\n</search_results>"
        )

    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"  [{i}] {r['title']}")
        lines.append(f"      URL: {r['url']}")
        lines.append(f"      {r['snippet']}")
    return "<search_results>\n" + "\n".join(lines) + "\n</search_results>"
