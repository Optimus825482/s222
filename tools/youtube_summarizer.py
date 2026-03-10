"""
YouTube Summarizer tool — extract video info, transcripts, and summaries.

Primary: youtube-transcript-api for transcripts (no cookies needed).
Fallback: yt-dlp for subtitles if installed.
Metadata: noembed.com oEmbed API (lightweight, no auth).
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ── Dependency checks ─────────────────────────────────────────────

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    TRANSCRIPT_API_AVAILABLE = True
except ImportError:
    TRANSCRIPT_API_AVAILABLE = False
    logger.warning("youtube-transcript-api not installed. pip install youtube-transcript-api")

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


# ── Helpers ───────────────────────────────────────────────────────

_YT_ID_RE = re.compile(
    r"(?:v=|youtu\.be/|embed/|shorts/|live/)([a-zA-Z0-9_-]{11})"
)


def extract_video_id(url: str) -> Optional[str]:
    m = _YT_ID_RE.search(url)
    return m.group(1) if m else None


def _format_duration(seconds: int) -> str:
    if not seconds:
        return "0:00"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


@dataclass
class VideoInfo:
    id: str; title: str; description: str; duration_seconds: int
    uploader: str; upload_date: str; view_count: int
    like_count: Optional[int]; url: str; thumbnail: str
    tags: list[str]; categories: list[str]


@dataclass
class TranscriptSegment:
    start: float; end: float; text: str


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
                "thumbnail": data.get("thumbnail_url", ""),
                "tags": [],
                "categories": [],
            },
            "error": None,
        }
    except Exception as e:
        logger.error(f"oEmbed metadata error: {e}")
        # Return minimal info with just the video_id
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

# ── Transcript extraction ─────────────────────────────────────────

async def get_transcript(
    url: str,
    language: str = "en",
    use_whisper_fallback: bool = True,
    whisper_model: str = "base",
) -> dict[str, Any]:
    """
    Extract transcript. Priority:
    1. youtube-transcript-api (no cookies, no bot detection)
    2. yt-dlp subtitles (fallback, may hit bot wall)
    3. Whisper audio transcription (heavy fallback)
    """
    video_id = extract_video_id(url)
    if not video_id:
        return {"success": False, "transcript": None, "source": None,
                "language": None, "error": "Invalid YouTube URL"}

    # ── Try youtube-transcript-api first ──
    if TRANSCRIPT_API_AVAILABLE:
        result = await _get_transcript_via_api(video_id, language)
        if result["success"]:
            return result
        logger.info(f"youtube-transcript-api failed for {video_id}: {result.get('error')}")

    # ── Fallback: yt-dlp subtitles ──
    if YT_DLP_AVAILABLE:
        result = await _get_transcript_via_ytdlp(url, language)
        if result["success"]:
            return result
        logger.info(f"yt-dlp subtitles failed for {video_id}: {result.get('error')}")

    # ── Fallback: Whisper ──
    if use_whisper_fallback and WHISPER_AVAILABLE:
        return await _transcribe_with_whisper(url, whisper_model)

    # Nothing worked
    errors = []
    if not TRANSCRIPT_API_AVAILABLE:
        errors.append("youtube-transcript-api not installed")
    if not YT_DLP_AVAILABLE:
        errors.append("yt-dlp not installed")
    if not WHISPER_AVAILABLE:
        errors.append("openai-whisper not installed")
    return {
        "success": False, "transcript": None, "source": None,
        "language": None,
        "error": f"No transcript available. Missing deps: {', '.join(errors)}"
    }


async def _get_transcript_via_api(video_id: str, language: str) -> dict[str, Any]:
    """Use youtube-transcript-api — lightweight, no cookies needed."""

    def _fetch():
        try:
            # Try requested language first, then fall back to any available
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            transcript = None
            actual_lang = language
            source = "manual_subtitles"

            # 1) Manual in requested language
            try:
                transcript = transcript_list.find_manually_created_transcript([language, "en"])
                source = "manual_subtitles"
                actual_lang = transcript.language_code
            except Exception:
                pass

            # 2) Auto-generated in requested language
            if transcript is None:
                try:
                    transcript = transcript_list.find_generated_transcript([language, "en"])
                    source = "auto_captions"
                    actual_lang = transcript.language_code
                except Exception:
                    pass

            # 3) Any available transcript
            if transcript is None:
                try:
                    for t in transcript_list:
                        transcript = t
                        source = "auto_captions" if t.is_generated else "manual_subtitles"
                        actual_lang = t.language_code
                        break
                except Exception:
                    pass

            if transcript is None:
                return {
                    "success": False, "transcript": None, "source": None,
                    "language": None, "error": "No transcripts available for this video"
                }

            entries = transcript.fetch()
            segments = []
            texts = []
            for entry in entries:
                start = entry.get("start", 0)
                dur = entry.get("duration", 0)
                text = entry.get("text", "").strip()
                if text:
                    segments.append({"start": round(start, 2), "end": round(start + dur, 2), "text": text})
                    texts.append(text)

            full_text = " ".join(texts)
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
        except Exception as e:
            return {
                "success": False, "transcript": None, "source": None,
                "language": None, "error": f"transcript-api error: {type(e).__name__}: {e}"
            }

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch)


async def _get_transcript_via_ytdlp(url: str, language: str) -> dict[str, Any]:
    """Fallback: use yt-dlp for subtitle extraction."""

    def _extract():
        try:
            ydl_opts = {
                "quiet": True, "no_warnings": True, "skip_download": True,
                "writesubtitles": True, "writeautomaticsub": True,
                "subtitleslangs": [language, "en"], "subtitlesformat": "json3",
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                subtitles = info.get("subtitles", {}) or {}
                auto_captions = info.get("automatic_captions", {}) or {}

                # Find subtitle URL
                sub_url, is_auto = None, False
                for lang in [language, "en"]:
                    for src, auto in [(subtitles, False), (auto_captions, True)]:
                        if lang in src:
                            for sub in src[lang]:
                                if sub.get("ext") == "json3":
                                    sub_url = sub.get("url")
                                    is_auto = auto
                                    break
                        if sub_url:
                            break
                    if sub_url:
                        break

                if not sub_url:
                    return {"success": False, "transcript": None, "source": None,
                            "language": None, "error": "No subtitles found via yt-dlp"}

                resp = httpx.get(sub_url, timeout=30.0)
                resp.raise_for_status()
                data = resp.json()

                segments = []
                for event in data.get("events", []):
                    if "segs" not in event:
                        continue
                    start = event.get("tStart", 0) / 1000.0
                    dur = event.get("dDurationMs", 0) / 1000.0
                    text = "".join(s.get("utf8", "") for s in event["segs"]).strip()
                    if text:
                        segments.append({"start": round(start, 2), "end": round(start + dur, 2), "text": text})

                full_text = " ".join(s["text"] for s in segments)
                return {
                    "success": bool(segments),
                    "transcript": {"full_text": full_text, "segments": segments, "word_count": len(full_text.split())},
                    "source": "auto_captions" if is_auto else "manual_subtitles",
                    "language": language,
                    "error": None if segments else "Parsed subtitles but no text found",
                }
        except Exception as e:
            return {"success": False, "transcript": None, "source": None,
                    "language": None, "error": f"yt-dlp subtitle error: {type(e).__name__}: {e}"}

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract)


async def _transcribe_with_whisper(url: str, model_size: str = "base") -> dict[str, Any]:
    """Download audio and transcribe with Whisper."""
    import os, tempfile

    def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_file = os.path.join(tmpdir, "audio.%(ext)s")
            ydl_opts = {
                "quiet": True, "no_warnings": True, "format": "bestaudio/best",
                "outtmpl": audio_file,
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(url, download=True)

                audio_path = os.path.join(tmpdir, "audio.mp3")
                if not os.path.exists(audio_path):
                    for ext in ["m4a", "opus", "webm", "wav"]:
                        alt = os.path.join(tmpdir, f"audio.{ext}")
                        if os.path.exists(alt):
                            audio_path = alt
                            break

                if not os.path.exists(audio_path):
                    return {"success": False, "transcript": None, "source": None,
                            "language": None, "error": "Failed to download audio"}

                model = whisper.load_model(model_size)
                result = model.transcribe(audio_path)
                segments = [{"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"].strip()}
                            for s in result.get("segments", [])]
                full_text = result.get("text", "").strip()
                return {
                    "success": True,
                    "transcript": {"full_text": full_text, "segments": segments, "word_count": len(full_text.split())},
                    "source": "whisper_transcription",
                    "language": result.get("language", "unknown"),
                    "error": None,
                }
            except Exception as e:
                return {"success": False, "transcript": None, "source": None,
                        "language": None, "error": f"Whisper error: {type(e).__name__}: {e}"}

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run)


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


__all__ = [
    "get_video_info", "get_transcript", "summarize_video",
    "format_video_summary", "extract_video_id",
    "VideoInfo", "TranscriptSegment",
    "YT_DLP_AVAILABLE", "WHISPER_AVAILABLE", "TRANSCRIPT_API_AVAILABLE",
]
