"""
SearXNG web search tool — used by Research Agent (GLM 4.7).
"""

from __future__ import annotations

import httpx

# Direct import to avoid circular/package issues in Streamlit
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import SEARXNG_URL


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search via SearXNG and return structured results."""
    params = {
        "q": query,
        "format": "json",
        "engines": "google,duckduckgo,brave",
        "language": "auto",
        "safesearch": 0,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{SEARXNG_URL}/search", params=params)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("results", [])[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", "")[:500],
            })
        return results

    except Exception as e:
        return [{"title": "Search Error", "url": "", "snippet": str(e)}]


def format_search_results(results: list[dict]) -> str:
    """Format search results for LLM context injection."""
    if not results:
        return "<search_results>\n  No results found.\n</search_results>"

    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"  [{i}] {r['title']}")
        lines.append(f"      URL: {r['url']}")
        lines.append(f"      {r['snippet']}")
    return "<search_results>\n" + "\n".join(lines) + "\n</search_results>"
