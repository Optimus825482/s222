"""
SearXNG web search tool — used by Research Agent (GLM 4.7).
"""

from __future__ import annotations

import logging

import httpx

# Direct import to avoid circular/package issues in Streamlit
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import SEARXNG_URL

logger = logging.getLogger(__name__)

# Message returned to agent when SearXNG gives no results (so agent can inform user)
NO_RESULTS_MESSAGE = (
    "SearXNG arama 0 sonuç döndürdü. Olası nedenler: "
    "SEARXNG_URL erişilemiyor veya arama motorları kapalı. "
    "Farklı/İngilizce bir sorgu deneyin veya .env içinde SEARXNG_URL kontrol edin."
)


def _parse_results(data: dict, max_results: int) -> list[dict]:
    """Extract results from SearXNG JSON; some instances use 'results' or nested structure."""
    results = []
    raw = data.get("results") or data.get("answers") or []
    for item in raw[:max_results]:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("name") or ""
        url = item.get("url") or item.get("link") or ""
        snippet = (item.get("content") or item.get("snippet") or item.get("description") or "")[:500]
        if title or url or snippet:
            results.append({"title": title, "url": url, "snippet": snippet})
    return results


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search via SearXNG and return structured results. Retries without engine filter if empty."""
    # Try engines that work from server IPs first (no CAPTCHA/401); then instance defaults
    params_list = [
        {"q": query, "format": "json", "engines": "bing,startpage,mojeek", "language": "auto", "safesearch": 0},
        {"q": query, "format": "json", "language": "auto", "safesearch": 0},  # instance defaults
        {"q": query, "format": "json", "engines": "google,duckduckgo,brave", "language": "auto", "safesearch": 0},
    ]
    last_error = None
    for params in params_list:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{SEARXNG_URL}/search", params=params)
                resp.raise_for_status()
                data = resp.json()
            results = _parse_results(data, max_results)
            if results:
                return results
            # Empty: try next param set
            last_error = None
        except Exception as e:
            last_error = e
            logger.warning("SearXNG request failed: %s", e)
    # All attempts failed or returned empty
    if last_error:
        return [{"title": "Arama hatası", "url": "", "snippet": f"{type(last_error).__name__}: {last_error}"}]
    return [{"title": "Sonuç yok", "url": "", "snippet": NO_RESULTS_MESSAGE}]


def format_search_results(results: list[dict]) -> str:
    """Format search results for LLM context injection."""
    if not results:
        return (
            "<search_results>\n  No results found. "
            "SearXNG may be unreachable or returned empty (check SEARXNG_URL in .env).\n</search_results>"
        )

    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"  [{i}] {r['title']}")
        lines.append(f"      URL: {r['url']}")
        lines.append(f"      {r['snippet']}")
    return "<search_results>\n" + "\n".join(lines) + "\n</search_results>"
