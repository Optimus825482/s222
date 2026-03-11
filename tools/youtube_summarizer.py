"""
YouTube Summarizer tool — extract video info, transcripts, and summaries.

Uses YouTube's InnerTube API directly via httpx as primary method.
Falls back to youtube_transcript_api for robust multi-language support.
Supports automatic translation to any target language via deep_translator.
"""

from __future__ import annotations

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Optional, cast

import httpx

logger = logging.getLogger(__name__)
ResultDict = dict[str, Any]

# ── Optional dependency checks ────────────────────────────────────
YT_DLP_AVAILABLE = False
WHISPER_AVAILABLE = False

try:
    from youtube_transcript_api import YouTubeTranscriptApi

    YT_TRANSCRIPT_API_AVAILABLE = True
except ImportError:
    YT_TRANSCRIPT_API_AVAILABLE = False

try:
    from deep_translator import GoogleTranslator

    DEEP_TRANSLATOR_AVAILABLE = True
except ImportError:
    DEEP_TRANSLATOR_AVAILABLE = False

TRANSCRIPT_API_AVAILABLE = True  # Our InnerTube impl is always available

_YT_ID_RE = re.compile(r"(?:v=|youtu\.be/|embed/|shorts/|live/)([a-zA-Z0-9_-]{11})")

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

    oembed_url = (
        f"https://noembed.com/embed?url=https://www.youtube.com/watch?v={video_id}"
    )
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
                "thumbnail": data.get(
                    "thumbnail_url", f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                ),
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
                "id": video_id,
                "title": "",
                "description": "",
                "duration_seconds": None,
                "duration_formatted": "",
                "uploader": "",
                "uploader_id": "",
                "upload_date": "",
                "view_count": 0,
                "like_count": None,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                "tags": [],
                "categories": [],
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
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
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
                segments.append(
                    {
                        "start": round(start, 2),
                        "end": round(start + dur, 2),
                        "text": text,
                    }
                )
    except ET.ParseError as e:
        logger.error(f"XML parse error: {e}")
    return segments


def _transcript_item_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


async def _get_transcript_via_yt_api(
    video_id: str,
    language: str = "en",
) -> ResultDict:
    """
    Fallback: youtube_transcript_api ile transcript al.
    Eski Flask uygulamasındaki çoklu fallback mantığı:
    1. İstenen dilde manuel altyazı
    2. İstenen dilde otomatik altyazı
    3. İngilizce → YouTube çevirisi (istenen dile)
    4. İngilizce ham
    5. İlk bulunan herhangi bir dil
    """
    if not YT_TRANSCRIPT_API_AVAILABLE:
        return {
            "success": False,
            "transcript": None,
            "source": None,
            "language": None,
            "error": "youtube_transcript_api not installed",
        }

    def _fetch_sync() -> ResultDict:
        is_target_source = False
        transcript_data = None
        source = "yt_transcript_api"
        actual_lang = language
        errors: list[str] = []

        def _process_transcript_list(t_list):
            nonlocal is_target_source
            # 1. Target language — manual
            try:
                tr = t_list.find_transcript([language])
                is_target_source = True
                return tr.fetch()
            except Exception:
                pass
            # 2. Target language — auto-generated
            try:
                tr = t_list.find_generated_transcript([language])
                is_target_source = True
                return tr.fetch()
            except Exception:
                pass
            # 3. English → translate via YouTube
            try:
                try:
                    eng = t_list.find_transcript(["en"])
                except Exception:
                    eng = t_list.find_generated_transcript(["en"])
                if eng.is_translatable:
                    try:
                        translated = eng.translate(language)
                        is_target_source = True
                        return translated.fetch()
                    except Exception:
                        pass
                return eng.fetch()
            except Exception:
                pass
            # 4. Any available
            try:
                return t_list.find_generated_transcript([language, "en"]).fetch()
            except Exception:
                pass
            return None

        # Method 1: list_transcripts (modern API)
        transcript_api_class = cast(Any, YouTubeTranscriptApi)
        list_transcripts = getattr(transcript_api_class, "list_transcripts", None)

        if callable(list_transcripts):
            try:
                t_list = list_transcripts(video_id)
                transcript_data = _process_transcript_list(t_list)
            except Exception as e:
                errors.append(f"list_transcripts: {e}")

        # Method 2: get_transcript (legacy API)
        get_transcript = getattr(transcript_api_class, "get_transcript", None)
        if not transcript_data and callable(get_transcript):
            try:
                transcript_data = get_transcript(video_id, languages=[language, "en"])
            except Exception as e:
                errors.append(f"get_transcript: {e}")

        # Method 3: Instance-based API (some versions)
        if not transcript_data:
            try:
                api_instance: Any = transcript_api_class()
                instance_list_transcripts = getattr(
                    api_instance, "list_transcripts", None
                )
                if callable(instance_list_transcripts):
                    try:
                        t_list = instance_list_transcripts(video_id)
                        transcript_data = _process_transcript_list(t_list)
                    except Exception as e:
                        errors.append(f"instance.list_transcripts: {e}")
                instance_fetch = getattr(api_instance, "fetch", None)
                if not transcript_data and callable(instance_fetch):
                    try:
                        transcript_data = instance_fetch(video_id)
                    except Exception as e:
                        errors.append(f"instance.fetch: {e}")
            except Exception as e:
                errors.append(f"instance_creation: {e}")

        if not transcript_data:
            return {
                "success": False,
                "transcript": None,
                "source": None,
                "language": None,
                "error": f"yt_transcript_api failed: {'; '.join(errors)}",
            }

        # Normalize — transcript_data is list[dict] with text/start/duration
        transcript_items = cast(list[Any], transcript_data)
        segments = []
        for item in transcript_items:
            text = str(_transcript_item_value(item, "text", "") or "").strip()
            if text:
                start = float(_transcript_item_value(item, "start", 0) or 0)
                dur = float(_transcript_item_value(item, "duration", 0) or 0)
                segments.append(
                    {
                        "start": round(start, 2),
                        "end": round(start + dur, 2),
                        "text": text,
                    }
                )

        full_text = " ".join(s["text"] for s in segments)
        return {
            "success": True,
            "transcript": {
                "full_text": full_text,
                "segments": segments,
                "word_count": len(full_text.split()),
            },
            "source": source,
            "language": actual_lang if is_target_source else "en",
            "error": None,
        }

    # Run sync API in thread pool
    return await asyncio.get_event_loop().run_in_executor(None, _fetch_sync)


# ── Translation via deep_translator ──────────────────────────────


async def translate_text(
    text: str,
    target_language: str = "tr",
    source_language: str = "auto",
    chunk_size: int = 4500,
) -> dict[str, Any]:
    """
    Translate text using deep_translator (Google Translate).
    Handles long texts by chunking at sentence boundaries.
    """
    if not DEEP_TRANSLATOR_AVAILABLE:
        return {
            "success": False,
            "translated": text,
            "error": "deep_translator not installed",
        }
    if not text or not text.strip():
        return {"success": True, "translated": "", "error": None}

    def _translate_sync() -> dict[str, Any]:
        try:
            translator = GoogleTranslator(
                source=source_language, target=target_language
            )

            # Short text — translate directly
            if len(text) <= chunk_size:
                result = translator.translate(text)
                return {"success": True, "translated": result or text, "error": None}

            # Long text — chunk by sentences
            sentences = re.split(r"(?<=[.!?])\s+", text)
            chunks: list[str] = []
            current = ""
            for sent in sentences:
                if len(current) + len(sent) + 1 > chunk_size:
                    if current:
                        chunks.append(current)
                    current = sent
                else:
                    current = f"{current} {sent}".strip() if current else sent
            if current:
                chunks.append(current)

            translated_parts = []
            for chunk in chunks:
                try:
                    part = translator.translate(chunk)
                    translated_parts.append(part or chunk)
                except Exception:
                    translated_parts.append(chunk)

            return {
                "success": True,
                "translated": " ".join(translated_parts),
                "error": None,
            }
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return {
                "success": False,
                "translated": text,
                "error": f"Translation failed: {e}",
            }

    return await asyncio.get_event_loop().run_in_executor(None, _translate_sync)


async def get_transcript(
    url: str,
    language: str = "en",
    target_language: Optional[str] = None,
    use_whisper_fallback: bool = True,
    whisper_model: str = "base",
) -> ResultDict:
    """
    Extract transcript with multi-method fallback:
    1. InnerTube API (primary — no deps, works on cloud)
    2. youtube_transcript_api (fallback — robust multi-language)

    If target_language is set and differs from source, auto-translates.
    """
    video_id = extract_video_id(url)
    if not video_id:
        return {
            "success": False,
            "transcript": None,
            "source": None,
            "language": None,
            "error": "Invalid YouTube URL",
        }

    innertube_result = None
    try:
        # ── Primary: InnerTube API ────────────────────────────────
        player_data = await _fetch_innertube_player(video_id)

        playability = player_data.get("playabilityStatus", {})
        if playability.get("status") == "ERROR":
            innertube_result = {
                "success": False,
                "transcript": None,
                "source": None,
                "language": None,
                "error": playability.get("reason", "Video unavailable"),
            }
        else:
            tracks = _extract_caption_tracks(player_data)
            if not tracks:
                innertube_result = {
                    "success": False,
                    "transcript": None,
                    "source": None,
                    "language": None,
                    "error": "No captions via InnerTube",
                }
            else:
                # Pick best track — prefer requested language, then 'en', then first
                chosen_track = None
                for track in tracks:
                    if track.get("languageCode", "") == language:
                        chosen_track = track
                        break
                if chosen_track is None:
                    for track in tracks:
                        if track.get("languageCode", "") == "en":
                            chosen_track = track
                            break
                if chosen_track is None:
                    chosen_track = tracks[0]

                actual_lang = chosen_track.get("languageCode", language)
                kind = chosen_track.get("kind", "")
                source = "auto_captions" if kind == "asr" else "manual_subtitles"

                base_url = chosen_track.get("baseUrl", "")
                if base_url:
                    xml_text = await _download_transcript_xml(base_url)
                    segments = _parse_transcript_xml(xml_text)
                    if segments:
                        full_text = " ".join(s["text"] for s in segments)
                        innertube_result = {
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

    except Exception as e:
        logger.warning(f"InnerTube failed, will try fallback: {e}")

    # ── Fallback: youtube_transcript_api ──────────────────────────
    if not innertube_result or not innertube_result.get("success"):
        logger.info("Trying youtube_transcript_api fallback...")
        yt_api_result = await _get_transcript_via_yt_api(video_id, language)
        if yt_api_result.get("success"):
            innertube_result = yt_api_result
        elif innertube_result is None:
            innertube_result = yt_api_result

    # ── Auto-translate if target_language differs ─────────────────
    result = innertube_result or {
        "success": False,
        "transcript": None,
        "source": None,
        "language": None,
        "error": "All transcript methods failed",
    }

    if (
        result.get("success")
        and target_language
        and result.get("language") != target_language
    ):
        transcript_data = result.get("transcript", {})
        full_text = (
            transcript_data.get("full_text", "")
            if isinstance(transcript_data, dict)
            else ""
        )
        if full_text:
            tr_result = await translate_text(
                full_text,
                target_language=target_language,
                source_language=result.get("language", "auto"),
            )
            if tr_result.get("success"):
                transcript_data["full_text"] = tr_result["translated"]
                transcript_data["word_count"] = len(tr_result["translated"].split())
                result["transcript"] = transcript_data
                result["language"] = target_language
                result["source"] = f"{result.get('source', 'unknown')}+translated"

    return result


# ── Main summarize function ───────────────────────────────────────


async def summarize_video(
    url: str,
    language: str = "en",
    target_language: Optional[str] = None,
    use_whisper_fallback: bool = True,
    whisper_model: str = "base",
    max_transcript_chars: int = 10000,
) -> dict[str, Any]:
    """Get video info + transcript in parallel, build summary."""
    video_result, transcript_result = await asyncio.gather(
        get_video_info(url),
        get_transcript(
            url, language, target_language, use_whisper_fallback, whisper_model
        ),
        return_exceptions=True,
    )

    if isinstance(video_result, Exception):
        video_result = {
            "success": False,
            "video_info": None,
            "error": str(video_result),
        }
    if isinstance(transcript_result, Exception):
        transcript_result = {
            "success": False,
            "transcript": None,
            "source": None,
            "language": None,
            "error": str(transcript_result),
        }

    video_data = cast(ResultDict, video_result)
    transcript_data = cast(ResultDict, transcript_result)

    summary = _build_video_summary(video_data, transcript_data, max_transcript_chars)

    return {
        "success": video_data.get("success", False)
        or transcript_data.get("success", False),
        "video_info": video_data.get("video_info"),
        "transcript": transcript_data.get("transcript"),
        "transcript_source": transcript_data.get("source"),
        "transcript_language": transcript_data.get("language"),
        "summary": summary,
        "errors": _collect_errors(video_data, transcript_data),
    }


def _build_video_summary(
    video_result: ResultDict, transcript_result: ResultDict, max_chars: int
) -> str:
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


def _collect_errors(*results: ResultDict) -> list[str]:
    return [r["error"] for r in results if r and r.get("error")]


def format_video_summary(result: dict[str, Any]) -> str:
    return result.get("summary", "<error>No summary available</error>")


@dataclass
class VideoInfo:
    id: str
    title: str
    description: str
    duration_seconds: Optional[int]
    uploader: str
    upload_date: str
    view_count: int
    like_count: Optional[int]
    url: str
    thumbnail: str
    tags: list[str]
    categories: list[str]

@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


__all__ = [
    "get_video_info",
    "get_transcript",
    "summarize_video",
    "format_video_summary",
    "extract_video_id",
    "translate_text",
    "VideoInfo",
    "TranscriptSegment",
    "YT_DLP_AVAILABLE",
    "WHISPER_AVAILABLE",
    "TRANSCRIPT_API_AVAILABLE",
    "YT_TRANSCRIPT_API_AVAILABLE",
    "DEEP_TRANSLATOR_AVAILABLE",
]
