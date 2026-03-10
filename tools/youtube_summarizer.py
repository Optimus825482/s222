"""
YouTube Summarizer tool — extract video info, transcripts, and summaries.
Uses yt-dlp for video info/transcripts, with Whisper fallback for audio transcription.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Try to import yt-dlp
try:
    import yt_dlp

    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    logger.warning("yt-dlp not installed. YouTube summarizer will have limited functionality.")

# Try to import Whisper for fallback transcription
try:
    import whisper

    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.debug("openai-whisper not installed. Whisper transcription fallback unavailable.")


@dataclass
class VideoInfo:
    """Structured video information."""

    id: str
    title: str
    description: str
    duration_seconds: int
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
    """A single transcript segment with timing."""

    start: float
    end: float
    text: str


async def get_video_info(url: str) -> dict[str, Any]:
    """
    Extract video metadata from a YouTube URL.

    Args:
        url: YouTube video URL (any format supported by yt-dlp)

    Returns:
        dict with video info or error message
    """
    if not YT_DLP_AVAILABLE:
        return {
            "success": False,
            "error": "yt-dlp is not installed. Run: pip install yt-dlp",
            "video_info": None,
        }

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
        "writesubtitles": False,
        "writeautomaticsub": False,
    }

    def _extract():
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                # Parse upload date
                upload_date = info.get("upload_date", "")
                if upload_date:
                    # Format: YYYYMMDD -> YYYY-MM-DD
                    upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"

                return {
                    "success": True,
                    "video_info": {
                        "id": info.get("id", ""),
                        "title": info.get("title", ""),
                        "description": info.get("description", ""),
                        "duration_seconds": info.get("duration", 0),
                        "duration_formatted": _format_duration(info.get("duration", 0)),
                        "uploader": info.get("uploader", info.get("channel", "")),
                        "uploader_id": info.get("uploader_id", ""),
                        "upload_date": upload_date,
                        "view_count": info.get("view_count", 0),
                        "like_count": info.get("like_count"),
                        "url": info.get("webpage_url", url),
                        "thumbnail": info.get("thumbnail", ""),
                        "tags": info.get("tags", []) or [],
                        "categories": info.get("categories", []) or [],
                        "average_rating": info.get("average_rating"),
                        "comment_count": info.get("comment_count"),
                    },
                    "error": None,
                }
        except yt_dlp.utils.DownloadError as e:
            return {
                "success": False,
                "video_info": None,
                "error": f"Download error: {str(e)}",
            }
        except Exception as e:
            return {
                "success": False,
                "video_info": None,
                "error": f"Extraction error: {type(e).__name__}: {str(e)}",
            }

    # Run in thread pool since yt-dlp is synchronous
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract)


async def get_transcript(
    url: str,
    language: str = "en",
    use_whisper_fallback: bool = True,
    whisper_model: str = "base",
) -> dict[str, Any]:
    """
    Extract transcript from a YouTube video.

    First tries to get captions/subtitles from YouTube (manual or auto-generated).
    Falls back to Whisper transcription if captions unavailable and use_whisper_fallback=True.

    Args:
        url: YouTube video URL
        language: Preferred language code for subtitles (default: "en")
        use_whisper_fallback: Whether to use Whisper if no subtitles found
        whisper_model: Whisper model size (tiny, base, small, medium, large)

    Returns:
        dict with transcript data or error
    """
    if not YT_DLP_AVAILABLE:
        return {
            "success": False,
            "transcript": None,
            "source": None,
            "error": "yt-dlp is not installed. Run: pip install yt-dlp",
        }

    # First try to get subtitles from YouTube
    transcript_result = await _get_youtube_subtitles(url, language)

    if transcript_result["success"]:
        return transcript_result

    # No subtitles available, try Whisper fallback
    if use_whisper_fallback and WHISPER_AVAILABLE:
        logger.info(f"No subtitles found for {url}, falling back to Whisper transcription")
        return await _transcribe_with_whisper(url, whisper_model)

    if use_whisper_fallback and not WHISPER_AVAILABLE:
        return {
            "success": False,
            "transcript": None,
            "source": None,
            "error": "No subtitles available and Whisper is not installed. Run: pip install openai-whisper",
        }

    return {
        "success": False,
        "transcript": None,
        "source": None,
        "error": transcript_result.get("error", "No subtitles found for this video"),
    }


async def _get_youtube_subtitles(url: str, language: str = "en") -> dict[str, Any]:
    """Try to get subtitles from YouTube (manual or auto-generated)."""

    def _extract():
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [language, "en"],
            "subtitlesformat": "json3",
            "outtmpl": "%(id)s.%(ext)s",
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                # Check for manual subtitles first
                subtitles = info.get("subtitles", {}) or {}
                auto_captions = info.get("automatic_captions", {}) or {}

                # Get available subtitle tracks
                available_langs = list(subtitles.keys()) + list(auto_captions.keys())

                # Prefer manual subtitles over auto-generated
                subtitle_url = None
                is_auto = False

                if language in subtitles:
                    for sub in subtitles[language]:
                        if sub.get("ext") == "json3":
                            subtitle_url = sub.get("url")
                            break
                elif "en" in subtitles:
                    for sub in subtitles["en"]:
                        if sub.get("ext") == "json3":
                            subtitle_url = sub.get("url")
                            break

                if not subtitle_url:
                    if language in auto_captions:
                        for sub in auto_captions[language]:
                            if sub.get("ext") == "json3":
                                subtitle_url = sub.get("url")
                                is_auto = True
                                break
                    elif "en" in auto_captions:
                        for sub in auto_captions["en"]:
                            if sub.get("ext") == "json3":
                                subtitle_url = sub.get("url")
                                is_auto = True
                                break

                if not subtitle_url:
                    return {
                        "success": False,
                        "transcript": None,
                        "source": None,
                        "error": f"No subtitles found. Available languages: {available_langs}",
                    }

                # Fetch and parse the JSON3 subtitles
                import httpx

                resp = httpx.get(subtitle_url, timeout=30.0)
                resp.raise_for_status()
                data = resp.json()

                # Parse JSON3 format
                segments = []
                for event in data.get("events", []):
                    if "segs" not in event:
                        continue
                    start = event.get("tStart", 0) / 1000.0
                    duration = event.get("dDurationMs", 0) / 1000.0
                    text = "".join(seg.get("utf8", "") for seg in event["segs"])
                    text = text.strip()
                    if text:
                        segments.append(
                            TranscriptSegment(
                                start=start,
                                end=start + duration,
                                text=text,
                            )
                        )

                if not segments:
                    return {
                        "success": False,
                        "transcript": None,
                        "source": None,
                        "error": "Parsed subtitle data but no text segments found",
                    }

                full_text = " ".join(seg.text for seg in segments)
                return {
                    "success": True,
                    "transcript": {
                        "full_text": full_text,
                        "segments": [
                            {
                                "start": round(seg.start, 2),
                                "end": round(seg.end, 2),
                                "text": seg.text,
                            }
                            for seg in segments
                        ],
                        "word_count": len(full_text.split()),
                    },
                    "source": "auto_captions" if is_auto else "manual_subtitles",
                    "language": language,
                    "error": None,
                }

        except Exception as e:
            return {
                "success": False,
                "transcript": None,
                "source": None,
                "error": f"Subtitle extraction error: {type(e).__name__}: {str(e)}",
            }

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract)


async def _transcribe_with_whisper(url: str, model_size: str = "base") -> dict[str, Any]:
    """Download audio and transcribe with Whisper."""

    def _download_and_transcribe():
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_file = os.path.join(tmpdir, "audio.%(ext)s")

            # Download audio only
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "format": "bestaudio/best",
                "outtmpl": audio_file,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    video_id = info.get("id", "unknown")

                # Find the downloaded audio file
                audio_path = os.path.join(tmpdir, "audio.mp3")
                if not os.path.exists(audio_path):
                    # Try other extensions
                    for ext in ["m4a", "opus", "webm", "wav"]:
                        alt_path = os.path.join(tmpdir, f"audio.{ext}")
                        if os.path.exists(alt_path):
                            audio_path = alt_path
                            break

                if not os.path.exists(audio_path):
                    return {
                        "success": False,
                        "transcript": None,
                        "source": None,
                        "error": "Failed to download audio file",
                    }

                # Transcribe with Whisper
                logger.info(f"Transcribing {audio_path} with Whisper {model_size} model...")
                model = whisper.load_model(model_size)
                result = model.transcribe(audio_path)

                # Build segments
                segments = []
                for seg in result.get("segments", []):
                    segments.append(
                        {
                            "start": round(seg.get("start", 0), 2),
                            "end": round(seg.get("end", 0), 2),
                            "text": seg.get("text", "").strip(),
                        }
                    )

                full_text = result.get("text", "").strip()

                return {
                    "success": True,
                    "transcript": {
                        "full_text": full_text,
                        "segments": segments,
                        "word_count": len(full_text.split()),
                    },
                    "source": "whisper_transcription",
                    "language": result.get("language", "unknown"),
                    "model": model_size,
                    "error": None,
                }

            except Exception as e:
                return {
                    "success": False,
                    "transcript": None,
                    "source": None,
                    "error": f"Whisper transcription error: {type(e).__name__}: {str(e)}",
                }

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_and_transcribe)


async def summarize_video(
    url: str,
    language: str = "en",
    use_whisper_fallback: bool = True,
    whisper_model: str = "base",
    max_transcript_chars: int = 10000,
) -> dict[str, Any]:
    """
    Get comprehensive video summary including metadata and transcript.

    Combines get_video_info and get_transcript into a single convenience function.

    Args:
        url: YouTube video URL
        language: Preferred language for subtitles
        use_whisper_fallback: Use Whisper if no subtitles available
        whisper_model: Whisper model size for fallback
        max_transcript_chars: Maximum characters to include in transcript

    Returns:
        dict with video_info, transcript, and formatted summary
    """
    # Get video info and transcript in parallel
    video_info_task = get_video_info(url)
    transcript_task = get_transcript(url, language, use_whisper_fallback, whisper_model)

    video_result, transcript_result = await asyncio.gather(
        video_info_task, transcript_task, return_exceptions=True
    )

    # Handle exceptions
    if isinstance(video_result, Exception):
        video_result = {
            "success": False,
            "video_info": None,
            "error": f"Video info error: {type(video_result).__name__}: {str(video_result)}",
        }

    if isinstance(transcript_result, Exception):
        transcript_result = {
            "success": False,
            "transcript": None,
            "source": None,
            "error": f"Transcript error: {type(transcript_result).__name__}: {str(transcript_result)}",
        }

    # Build summary
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


def _build_video_summary(
    video_result: dict[str, Any],
    transcript_result: dict[str, Any],
    max_chars: int,
) -> str:
    """Build a formatted summary string for LLM context."""
    parts = ["<youtube_video>"]

    # Add video info
    if video_result.get("success") and video_result.get("video_info"):
        info = video_result["video_info"]
        parts.append("  <metadata>")
        parts.append(f"    <title>{info.get('title', 'Unknown')}</title>")
        parts.append(f"    <url>{info.get('url', '')}</url>")
        parts.append(f"    <video_id>{info.get('id', '')}</video_id>")
        parts.append(f"    <uploader>{info.get('uploader', '')}</uploader>")
        parts.append(f"    <upload_date>{info.get('upload_date', '')}</upload_date>")
        parts.append(f"    <duration>{info.get('duration_formatted', '')}</duration>")
        parts.append(f"    <views>{info.get('view_count', 0):,}</views>")
        if info.get("like_count"):
            parts.append(f"    <likes>{info.get('like_count'):,}</likes>")
        if info.get("tags"):
            parts.append(f"    <tags>{', '.join(info.get('tags', [])[:5])}</tags>")
        parts.append("  </metadata>")

        # Add description (truncated)
        description = info.get("description", "")
        if description:
            desc_preview = description[:500] + "..." if len(description) > 500 else description
            parts.append(f"  <description>\n    {desc_preview}\n  </description>")

    # Add transcript
    if transcript_result.get("success") and transcript_result.get("transcript"):
        transcript = transcript_result["transcript"]
        source = transcript_result.get("source", "unknown")

        parts.append(f"  <transcript source=\"{source}\">")
        full_text = transcript.get("full_text", "")
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "\n\n[... transcript truncated]"
        parts.append(f"    {full_text}")
        parts.append("  </transcript>")
    else:
        parts.append("  <transcript>Not available</transcript>")

    parts.append("</youtube_video>")
    return "\n".join(parts)


def _collect_errors(*results: dict[str, Any]) -> list[str]:
    """Collect all error messages from results."""
    errors = []
    for result in results:
        if result and result.get("error"):
            errors.append(result["error"])
    return errors


def _format_duration(seconds: int) -> str:
    """Format duration in seconds to HH:MM:SS or MM:SS."""
    if not seconds:
        return "0:00"
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_video_summary(result: dict[str, Any]) -> str:
    """Format video summary result for LLM context."""
    return result.get("summary", "<error>No summary available</error>")


# Export public functions
__all__ = [
    "get_video_info",
    "get_transcript",
    "summarize_video",
    "format_video_summary",
    "VideoInfo",
    "TranscriptSegment",
]