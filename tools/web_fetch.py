"""
Web Fetch tool — fetch and extract text content from URLs.
Available to all agents for retrieving web page content.
"""

from __future__ import annotations

import re

import httpx


async def web_fetch(url: str, max_chars: int = 8000) -> dict:
    """
    Fetch a URL and return cleaned text content.
    Returns dict with url, title, content, status.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
    }

    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            max_redirects=5,
        ) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            html = resp.text

        title = _extract_title(html)
        text = _html_to_text(html)

        # Truncate to max_chars
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[... truncated]"

        return {
            "url": str(resp.url),
            "title": title,
            "content": text,
            "status": resp.status_code,
            "content_length": len(text),
        }

    except httpx.HTTPStatusError as e:
        return {
            "url": url,
            "title": "",
            "content": f"HTTP Error {e.response.status_code}: {e.response.reason_phrase}",
            "status": e.response.status_code,
            "content_length": 0,
        }
    except Exception as e:
        return {
            "url": url,
            "title": "",
            "content": f"Fetch error: {type(e).__name__}: {e}",
            "status": 0,
            "content_length": 0,
        }


def _extract_title(html: str) -> str:
    """Extract <title> from HTML."""
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _html_to_text(html: str) -> str:
    """Convert HTML to readable text — lightweight, no dependencies."""
    # Remove script and style blocks
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<nav[^>]*>.*?</nav>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<footer[^>]*>.*?</footer>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # Block elements → newlines
    text = re.sub(r"<(?:p|div|h[1-6]|li|tr|br|hr)[^>]*>", "\n", text, flags=re.IGNORECASE)

    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode common entities
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&nbsp;", " ")
    )

    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def format_fetch_result(result: dict) -> str:
    """Format fetch result for LLM context."""
    title = result.get("title", "")
    url = result.get("url", "")
    content = result.get("content", "")
    return (
        f"<web_page>\n"
        f"  <url>{url}</url>\n"
        f"  <title>{title}</title>\n"
        f"  <content>\n{content}\n  </content>\n"
        f"</web_page>"
    )
