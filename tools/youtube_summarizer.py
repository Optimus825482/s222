"""
YouTube Summarizer tool — extract video info, transcripts, and summaries.

Uses YouTube's InnerTube API directly via httpx — no yt-dlp, no third-party
transcript libraries needed. Works on cloud IPs without cookie/bot issues.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# Keep these for backward compat with route imports
YT_DLP_AVAILABLE = False
WHISPER_AVAILABLE = False
TRANSCRIPT_API_AVAILABLE = True  # We use our own implementation now

_YT_ID_RE = re.compile(
    r"(?:v=|youtu\.be/|embed/|shorts/|live/)([a-zA-Z0-9_-]{11})"
)

_INNERTUBE_API_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
_INNERTUBE_CLIENT = {
    "clientName": "WEB",
    "clientVersion": "2.20240313.05.00",
    "hl": "en",
}


def extract_video_id(url: str) -> Optional[str]:
    m = _YT_ID_RE.search(url)
    return m.group(1) if m else None


def _format_duration(seconds: int) -> str:
    if not seconds:
        return "0:00"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ── Video metadata via oEmbed ─────────────────────────────────────

async def get_video_info(url: str) -> dict[str, Any]:
    """Extract video metadata using noembed oEmbed (no auth needed)."""
    video_id = extract_video_id(url)
    if not video_id:
        return {"success": False, "video_info": None, "error": "Invalid YouTube URL"}

    oembed_url = f"https://noembed.com/embed?url=https://www.youtube.com/watch?v={video_id}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(oembed_url)
            resp.raise_for_status()
            data = resp.json()

        if data.get("error"):
            return {"success": False, "video_info": None, "error": data["error"]}

        return {
            "success": True,
            "video_info": {
                "id": video_id,
                "title": data.get("title", ""),
                "description": "",
                "duration_seconds": None,
                "duration_formatted": "",
                "uploader": data.get("author_name", ""),
                "uploader_id": "",
                "upload_date": "",
                "view_count": 0,
                "like_count": None,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "thumbnail": data.get("thumbnail_url", f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"),
                "tags": [],
                "categories": [],
            },
            "error": None,
        }
    except Exception as e:
        logger.error(f"oEmbed metadata error: {e}")
        return {
            "success": True,
            "video_info": {
                "id": video_id, "title": "", "description": "",
                "duration_seconds": None, "duration_formatted": "",
                "uploader": "", "uploader_id": "", "upload_date": "",
                "view_count": 0, "like_count": None,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                "tags": [], "categories": [],
            },
            "error": None,
        }


# ── Transcript via InnerTube API ──────────────────────────────────

async def _fetch_innertube_player(video_id: str) -> dict[str, Any]:
    """Call YouTube InnerTube player endpoint to get caption track URLs."""
    payload = {
        "context": {"client": _INNERTUBE_CLIENT},
        "videoId": video_id,
    }
    url = f"https://www.youtube.com/youtubei/v1/player?key={_INNERTUBE_API_KEY}"

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
        )
        resp.raise_for_status()
        return resp.json()


def _extract_caption_tracks(player_data: dict) -> list[dict]:
    """Extract caption track info from InnerTube player response."""
    captions = player_data.get("captions", {})
    renderer = captions.get("playerCaptionsTracklistRenderer", {})
    tracks = renderer.get("captionTracks", [])
    return tracks


async def _download_transcript_xml(base_url: str) -> str:
    """Download transcript XML from YouTube's timedtext endpoint."""
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            base_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        resp.raise_for_status()
        return resp.text


def _parse_transcript_xml(xml_text: str) -> list[dict]:
    """Parse YouTube's timedtext XML into segments."""
    segments = []
    try:
        root = ET.fromstring(xml_text)
        for elem in root.iter("text"):
            start = float(elem.get("start", "0"))
            dur = float(elem.get("dur", "0"))
            text = (elem.text or "").strip()
            # Unescape HTML entities
            text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            text = text.replace("&#39;", "'").replace("&quot;", '"')
            if text:
                segments.append({
                    "start": round(start, 2),
                    "end": round(start + dur, 2),
                    "text": text,
                })
    except ET.ParseError as e:
        logger.error(f"XML parse error: {e}")
    return segments


async def get_transcript(
    url: str,
    language: str = "en",
    use_whisper_fallback: bool = True,
    whisper_model: str = "base",
) -> dict[str, Any]:
    """
    Extract transcript using YouTube's InnerTube API directly.
    No third-party libraries needed — just httpx.
    """
    video_id = extract_video_id(url)
    if not video_id:
        return {"success": False, "transcript": None, "source": None,
                "language": None, "error": "Invalid YouTube URL"}

    try:
        # Step 1: Get player data with caption tracks
        player_data = await _fetch_innertube_player(video_id)

        # Check playability
        playability = player_data.get("playabilityStatus", {})
        if playability.get("status") == "ERROR":
            return {"success": False, "transcript": None, "source": None,
                    "language": None,
                    "error": playability.get("reason", "Video unavailable")}

        # Step 2: Find caption tracks
        tracks = _extract_caption_tracks(player_data)
        if not tracks:
            return {"success": False, "transcript": None, "source": None,
                    "language": None,
                    "error": "No captions available for this video"}

        # Step 3: Pick best track — prefer requested language, then 'en', then first
        chosen_track = None
        source = "auto_captions"

        # Try exact language match
        for track in tracks:
            lang_code = track.get("languageCode", "")
            if lang_code == language:
                chosen_track = track
                break

        # Try English fallback
        if chosen_track is None:
            for track in tracks:
                if track.get("languageCode", "") == "en":
                    chosen_track = track
                    break

        # Take first available
        if chosen_track is None:
            chosen_track = tracks[0]

        actual_lang = chosen_track.get("languageCode", language)
        kind = chosen_track.get("kind", "")
        source = "auto_captions" if kind == "asr" else "manual_subtitles"

        # Step 4: Download and parse transcript XML
        base_url = chosen_track.get("baseUrl", "")
        if not base_url:
            return {"success": False, "transcript": None, "source": None,
                    "language": None, "error": "Caption track has no URL"}

        xml_text = await _download_transcript_xml(base_url)
        segments = _parse_transcript_xml(xml_text)

        if not segments:
            return {"success": False, "transcript": None, "source": source,
                    "language": actual_lang,
                    "error": "Downloaded captions but no text segments found"}

        full_text = " ".join(s["text"] for s in segments)
        return {
            "success": True,
            "transcript": {
                "full_text": full_text,
                "segments": segments,
                "word_count": len(full_text.split()),
            },
            "source": source,
            "language": actual_lang,
            "error": None,
        }

    except httpx.HTTPStatusError as e:
        return {"success": False, "transcript": None, "source": None,
                "language": None,
                "error": f"HTTP error {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        logger.error(f"InnerTube transcript error: {e}", exc_info=True)
        return {"success": False, "transcript": None, "source": None,
                "language": None,
                "error": f"Transcript extraction error: {type(e).__name__}: {e}"}


# ── Main summarize function ───────────────────────────────────────

async def summarize_video(
    url: str,
    language: str = "en",
    use_whisper_fallback: bool = True,
    whisper_model: str = "base",
    max_transcript_chars: int = 10000,
) -> dict[str, Any]:
    """Get video info + transcript in parallel, build summary."""
    video_result, transcript_result = await asyncio.gather(
        get_video_info(url),
        get_transcript(url, language, use_whisper_fallback, whisper_model),
        return_exceptions=True,
    )

    if isinstance(video_result, Exception):
        video_result = {"success": False, "video_info": None, "error": str(video_result)}
    if isinstance(transcript_result, Exception):
        transcript_result = {"success": False, "transcript": None, "source": None,
                             "language": None, "error": str(transcript_result)}

    summary = _build_video_summary(video_result, transcript_result, max_transcript_chars)

    return {
        "success": video_result.get("success", False) or transcript_result.get("success", False),
        "video_info": video_result.get("video_info"),
        "transcript": transcript_result.get("transcript"),
        "transcript_source": transcript_result.get("source"),
        "transcript_language": transcript_result.get("language"),
        "summary": summary,
        "errors": _collect_errors(video_result, transcript_result),
    }


def _build_video_summary(video_result: dict, transcript_result: dict, max_chars: int) -> str:
    parts = ["<youtube_video>"]
    if video_result.get("success") and video_result.get("video_info"):
        info = video_result["video_info"]
        parts.append("  <metadata>")
        parts.append(f"    <title>{info.get('title', '')}</title>")
        parts.append(f"    <uploader>{info.get('uploader', '')}</uploader>")
        parts.append(f"    <url>{info.get('url', '')}</url>")
        parts.append("  </metadata>")

    if transcript_result.get("success") and transcript_result.get("transcript"):
        t = transcript_result["transcript"]
        source = transcript_result.get("source", "unknown")
        full_text = t.get("full_text", "")
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "\n\n[... truncated]"
        parts.append(f'  <transcript source="{source}">')
        parts.append(f"    {full_text}")
        parts.append("  </transcript>")
    else:
        parts.append("  <transcript>Not available</transcript>")

    parts.append("</youtube_video>")
    return "\n".join(parts)


def _collect_errors(*results: dict) -> list[str]:
    return [r["error"] for r in results if r and r.get("error")]


def format_video_summary(result: dict[str, Any]) -> str:
    return result.get("summary", "<error>No summary available</error>")


# Backward compat dataclasses
from dataclasses import dataclass

@dataclass
class VideoInfo:
    id: str; title: str; description: str; duration_seconds: int
    uploader: str; upload_date: str; view_count: int
    like_count: Optional[int]; url: str; thumbnail: str
    tags: list[str]; categories: list[str]

@dataclass
class TranscriptSegment:
    start: float; end: float; text: str


__all__ = [
    "get_video_info", "get_transcript", "summarize_video",
    "format_video_summary", "extract_video_id",
    "VideoInfo", "TranscriptSegment",
    "YT_DLP_AVAILABLE", "WHISPER_AVAILABLE", "TRANSCRIPT_API_AVAILABLE",
]
