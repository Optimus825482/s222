"""
YouTube video summarization endpoints.
Extract transcripts and generate summaries from YouTube videos.

Uses tools/youtube_summarizer.py as the underlying implementation with
support for yt-dlp (video info/subtitles) and Whisper (audio transcription fallback).
"""

import logging
import sys
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import get_current_user, _audit

logger = logging.getLogger(__name__)

router = APIRouter(tags=["youtube"])


# ── Constants ─────────────────────────────────────────────────────

MAX_TRANSCRIPT_LENGTH = 100_000  # Characters
MAX_SUMMARY_LENGTH = 10_000  # Characters


# ── Pydantic Models ───────────────────────────────────────────────

class YouTubeSummarizeRequest(BaseModel):
    """Request model for YouTube summarization."""
    url: str = Field(..., description="YouTube video URL (supports youtube.com, youtu.be, etc.)")
    language: str = Field(default="en", description="Preferred transcript language code (e.g., 'en', 'tr', 'de')")
    include_timestamps: bool = Field(default=False, description="Include timestamps in transcript")
    max_summary_length: int = Field(default=2000, description="Maximum summary length in characters")
    use_whisper_fallback: bool = Field(default=True, description="Use Whisper if no subtitles available")
    whisper_model: str = Field(default="base", description="Whisper model: tiny, base, small, medium, large")
    max_transcript_chars: int = Field(default=10000, description="Max transcript characters to return")


class YouTubeInfoRequest(BaseModel):
    """Request model for YouTube video info."""
    url: str = Field(..., description="YouTube video URL")


class YouTubeSummarizeResponse(BaseModel):
    """Response model for YouTube summarization."""
    success: bool
    video_id: str = Field(default="", description="YouTube video ID")
    title: Optional[str] = Field(default=None, description="Video title")
    duration_seconds: Optional[int] = Field(default=None, description="Video duration in seconds")
    channel: Optional[str] = Field(default=None, description="Channel name")
    transcript: str = Field(default="", description="Full transcript text")
    transcript_language: Optional[str] = Field(default=None, description="Detected/used transcript language")
    transcript_source: Optional[str] = Field(default=None, description="Source of transcript (subtitles/whisper)")
    summary: str = Field(default="", description="AI-generated summary")
    error: Optional[str] = Field(default=None, description="Error message if extraction failed")


class YouTubeTranscriptResponse(BaseModel):
    """Response model for transcript extraction only."""
    success: bool
    video_id: str = Field(default="", description="YouTube video ID")
    title: Optional[str] = Field(default=None, description="Video title")
    transcript: str = Field(default="", description="Full transcript text")
    transcript_language: Optional[str] = Field(default=None, description="Detected/used transcript language")
    transcript_source: Optional[str] = Field(default=None, description="Source of transcript (subtitles/whisper)")
    segments: list[dict] = Field(default_factory=list, description="Transcript segments with timestamps")
    error: Optional[str] = Field(default=None, description="Error message if extraction failed")


class YouTubeInfoResponse(BaseModel):
    """Response model for video info only."""
    success: bool
    video_id: str = Field(default="", description="YouTube video ID")
    title: Optional[str] = Field(default=None, description="Video title")
    description: Optional[str] = Field(default=None, description="Video description")
    duration_seconds: Optional[int] = Field(default=None, description="Video duration in seconds")
    channel: Optional[str] = Field(default=None, description="Channel name")
    view_count: Optional[int] = Field(default=None, description="View count")
    upload_date: Optional[str] = Field(default=None, description="Upload date")
    thumbnail_url: Optional[str] = Field(default=None, description="Thumbnail URL")
    available_captions: list[str] = Field(default_factory=list, description="Available caption languages")
    error: Optional[str] = Field(default=None, description="Error message if extraction failed")


class YouTubeStatusResponse(BaseModel):
    """Response model for YouTube service status."""
    yt_dlp_available: bool
    whisper_available: bool
    transcript_api_available: bool = False
    features: dict
    whisper_models: list[str]
    supported_urls: list[str]


# ── Helper Functions ───────────────────────────────────────────────

def _extract_video_id_from_url(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats using the tools module."""
    try:
        # Use yt-dlp to extract video ID reliably
        import yt_dlp
        ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("id") if info else None
    except Exception:
        # Fallback to regex for common patterns
        import re
        patterns = [
            r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})",
            r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
            r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None


async def generate_summary(transcript: str, max_length: int = 2000) -> str:
    """Generate AI summary of transcript using available LLM."""
    if not transcript:
        return ""
    
    # Truncate if too long
    if len(transcript) > MAX_TRANSCRIPT_LENGTH:
        transcript = transcript[:MAX_TRANSCRIPT_LENGTH] + "... [truncated]"
    
    try:
        from openai import AsyncOpenAI
        from config import MODELS
        
        client = AsyncOpenAI()
        
        # Get model config
        model_name = "gpt-4o-mini"  # Default to fast model for summarization
        for model in MODELS:
            if "summary" in model.get("role", "").lower() or model.get("role") == "assistant":
                model_name = model.get("model", model_name)
                break
        
        prompt = f"""Summarize the following YouTube video transcript in a clear, structured format.

Provide:
1. **Main Topic**: What is the video about?
2. **Key Points**: Bullet points of the main arguments/ideas
3. **Takeaways**: What should viewers learn/remember?

Keep the summary under {max_length} characters.

Transcript:
{transcript}

Summary:"""
        
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates clear, concise summaries of video content."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_length // 3,  # Rough estimate
            temperature=0.3,
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logger.error(f"Summary generation failed: {e}", exc_info=True)
        # Return a truncated transcript as fallback
        return f"[Summary generation failed. First {max_length} chars of transcript:]\n\n{transcript[:max_length]}"


# ── Endpoints ────────────────────────────────────────────────────

@router.get("/api/youtube/status", response_model=YouTubeStatusResponse)
async def get_youtube_status(user: dict = Depends(get_current_user)):
    """
    Check YouTube summarizer service status and capabilities.
    
    Returns information about:
    - yt-dlp availability (for video info and subtitle extraction)
    - Whisper availability (for fallback transcription)
    - Supported features
    """
    try:
        from tools.youtube_summarizer import YT_DLP_AVAILABLE, WHISPER_AVAILABLE, TRANSCRIPT_API_AVAILABLE
        
        return YouTubeStatusResponse(
            yt_dlp_available=YT_DLP_AVAILABLE,
            whisper_available=WHISPER_AVAILABLE,
            transcript_api_available=TRANSCRIPT_API_AVAILABLE,
            features={
                "transcript_api": TRANSCRIPT_API_AVAILABLE,
                "video_info": True,
                "subtitle_extraction": YT_DLP_AVAILABLE,
                "whisper_transcription": WHISPER_AVAILABLE,
            },
            whisper_models=["tiny", "base", "small", "medium", "large"] if WHISPER_AVAILABLE else [],
            supported_urls=[
                "youtube.com/watch?v=...",
                "youtu.be/...",
                "youtube.com/shorts/...",
            ],
        )
    except Exception as e:
        logger.error(f"Status check error: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Status check error: {e}")


@router.post("/api/youtube/info", response_model=YouTubeInfoResponse)
async def get_youtube_video_info(
    request: YouTubeInfoRequest,
    user: dict = Depends(get_current_user),
):
    """Get metadata about a YouTube video without transcript extraction.
    
    Returns title, description, duration, channel, and available caption languages.
    
    **Features:**
    - Extracts comprehensive video metadata
    - Lists available caption/subtitle languages
    - Fast operation (no audio download)
    """
    try:
        from tools.youtube_summarizer import get_video_info
        
        result = await get_video_info(request.url)
        
        if not result.get("success"):
            # Extract video ID for error response
            video_id = _extract_video_id_from_url(request.url) or ""
            return YouTubeInfoResponse(
                success=False,
                video_id=video_id,
                error=result.get("error", "Failed to extract video info")
            )
        
        video_info = result.get("video_info", {})
        video_id = video_info.get("id", _extract_video_id_from_url(request.url) or "")
        
        # Audit log
        _audit(
            "youtube_info",
            user.get("user_id", user.get("sub", "unknown")),
            detail=f"Video: {video_id}, Title: {video_info.get('title', 'Unknown')}"
        )
        
        return YouTubeInfoResponse(
            success=True,
            video_id=video_id,
            title=video_info.get("title"),
            description=video_info.get("description"),
            duration_seconds=video_info.get("duration_seconds"),
            channel=video_info.get("uploader"),
            view_count=video_info.get("view_count"),
            upload_date=video_info.get("upload_date"),
            thumbnail_url=video_info.get("thumbnail"),
            available_captions=video_info.get("tags", []),  # Tags can indicate caption availability
            error=None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"YouTube info extraction error: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"YouTube info extraction error: {e}")


@router.post("/api/youtube/transcript", response_model=YouTubeTranscriptResponse)
async def get_youtube_transcript(
    request: YouTubeSummarizeRequest,
    user: dict = Depends(get_current_user),
):
    """Extract transcript from a YouTube video without summarization.
    
    Returns the full transcript text with optional timestamps.
    
    **Features:**
    - Extracts video metadata
    - Downloads transcript/captions in preferred language
    - Falls back to Whisper transcription if no subtitles available
    
    **Supported URL formats:**
    - youtube.com/watch?v=VIDEO_ID
    - youtu.be/VIDEO_ID
    - youtube.com/embed/VIDEO_ID
    - youtube.com/shorts/VIDEO_ID
    """
    try:
        from tools.youtube_summarizer import get_transcript, get_video_info
        import asyncio
        
        # Get video info and transcript in parallel
        video_info_task = get_video_info(request.url)
        transcript_task = get_transcript(
            url=request.url,
            language=request.language,
            use_whisper_fallback=request.use_whisper_fallback,
            whisper_model=request.whisper_model,
        )
        
        video_result, transcript_result = await asyncio.gather(
            video_info_task, transcript_task, return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(video_result, Exception):
            video_result = {"success": False, "video_info": None, "error": str(video_result)}
        if isinstance(transcript_result, Exception):
            transcript_result = {"success": False, "transcript": None, "error": str(transcript_result)}
        
        video_info = video_result.get("video_info", {}) if video_result.get("success") else {}
        video_id = video_info.get("id", _extract_video_id_from_url(request.url) or "")
        
        if not transcript_result.get("success"):
            return YouTubeTranscriptResponse(
                success=False,
                video_id=video_id,
                title=video_info.get("title"),
                transcript="",
                transcript_language="",
                transcript_source="",
                segments=[],
                error=transcript_result.get("error", "Failed to extract transcript")
            )
        
        transcript_data = transcript_result.get("transcript", {})
        full_text = transcript_data.get("full_text", "") if isinstance(transcript_data, dict) else ""
        segments = transcript_data.get("segments", []) if isinstance(transcript_data, dict) else []
        
        # Format transcript with timestamps if requested
        formatted_transcript = full_text
        if request.include_timestamps and segments:
            formatted_parts = []
            for seg in segments:
                start = seg.get("start", 0)
                minutes = int(start // 60)
                seconds = int(start % 60)
                text = seg.get("text", "")
                formatted_parts.append(f"[{minutes:02d}:{seconds:02d}] {text}")
            formatted_transcript = "\n".join(formatted_parts)
        
        # Truncate if needed
        max_chars = request.max_transcript_chars
        if len(formatted_transcript) > max_chars:
            formatted_transcript = formatted_transcript[:max_chars] + "\n\n[... transcript truncated]"
        
        # Audit log
        _audit(
            "youtube_transcript",
            user.get("user_id", user.get("sub", "unknown")),
            detail=f"Video: {video_id}, Source: {transcript_result.get('source', 'unknown')}"
        )
        
        return YouTubeTranscriptResponse(
            success=True,
            video_id=video_id,
            title=video_info.get("title"),
            transcript=formatted_transcript,
            transcript_language=transcript_result.get("language") or request.language,
            transcript_source=transcript_result.get("source") or "",
            segments=segments[:1000] if segments else [],  # Limit segments
            error=None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcript extraction error: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Transcript extraction error: {e}")


@router.post("/api/youtube/summarize", response_model=YouTubeSummarizeResponse)
async def summarize_youtube_video(
    request: YouTubeSummarizeRequest,
    user: dict = Depends(get_current_user),
):
    """Summarize a YouTube video by extracting its transcript and generating an AI summary.
    
    **Features:**
    - Extracts video metadata (title, channel, duration)
    - Downloads transcript/captions in preferred language
    - Falls back to Whisper transcription if no subtitles available
    - Generates AI-powered summary of the content
    
    **Supported URL formats:**
    - youtube.com/watch?v=VIDEO_ID
    - youtu.be/VIDEO_ID
    - youtube.com/embed/VIDEO_ID
    - youtube.com/shorts/VIDEO_ID
    """
    try:
        from tools.youtube_summarizer import summarize_video
        import asyncio
        
        result = await summarize_video(
            url=request.url,
            language=request.language,
            use_whisper_fallback=request.use_whisper_fallback,
            whisper_model=request.whisper_model,
            max_transcript_chars=request.max_transcript_chars,
        )
        
        video_info = result.get("video_info", {}) or {}
        transcript_data = result.get("transcript", {}) or {}
        
        video_id = video_info.get("id", _extract_video_id_from_url(request.url) or "")
        
        # Get transcript text
        full_text = transcript_data.get("full_text", "") if isinstance(transcript_data, dict) else ""
        
        # Format transcript with timestamps if requested
        formatted_transcript = full_text
        if request.include_timestamps and transcript_data.get("segments"):
            segments = transcript_data.get("segments", [])
            formatted_parts = []
            for seg in segments:
                start = seg.get("start", 0)
                minutes = int(start // 60)
                seconds = int(start % 60)
                text = seg.get("text", "")
                formatted_parts.append(f"[{minutes:02d}:{seconds:02d}] {text}")
            formatted_transcript = "\n".join(formatted_parts)
        
        # Truncate transcript if needed
        max_chars = request.max_transcript_chars
        if len(formatted_transcript) > max_chars:
            formatted_transcript = formatted_transcript[:max_chars] + "\n\n[... transcript truncated]"
        
        # Generate AI summary
        summary = ""
        if full_text:
            summary = await generate_summary(full_text, max_length=request.max_summary_length)
        
        # Audit log
        _audit(
            "youtube_summarize",
            user.get("user_id", user.get("sub", "unknown")),
            detail=f"Video: {video_id}, Title: {video_info.get('title', 'Unknown')}"
        )
        
        # Collect errors
        errors = result.get("errors", [])
        error_msg = "; ".join(errors) if errors else None
        
        return YouTubeSummarizeResponse(
            success=result.get("success", False) or bool(full_text),
            video_id=video_id,
            title=video_info.get("title"),
            duration_seconds=video_info.get("duration_seconds"),
            channel=video_info.get("uploader"),
            transcript=formatted_transcript,
            transcript_language=result.get("transcript_language") or request.language,
            transcript_source=result.get("transcript_source") or "",
            summary=summary[:MAX_SUMMARY_LENGTH],
            error=error_msg
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"YouTube summarization error: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"YouTube summarization error: {e}")