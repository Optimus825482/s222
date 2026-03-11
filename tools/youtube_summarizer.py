"""
YouTube Summarizer tool — extract video info, transcripts, and summaries.

Uses youtube_transcript_api as primary method (with optional proxy for cloud IPs).
Falls back to YouTube's InnerTube API directly via httpx.
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

# Proxy support for youtube_transcript_api (Webshare residential proxy)
_WEBSHARE_PROXY_CONFIG = None
try:
    from youtube_transcript_api.proxies import WebshareProxyConfig

    _WEBSHARE_AVAILABLE = True
except ImportError:
    _WEBSHARE_AVAILABLE = False

TRANSCRIPT_API_AVAILABLE = True  # Our InnerTube impl is always available

_YT_ID_RE = re.compile(r"(?:v=|youtu\.be/|embed/|shorts/|live/)([a-zA-Z0-9_-]{11})")

_INNERTUBE_API_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
_INNERTUBE_CLIENT = {
    "clientName": "WEB",
    "clientVersion": "2.20240313.05.00",
    "hl": "en",
}


def _get_proxy_config() -> dict[str, str]:
    """Get proxy settings from config. Returns dict for httpx or empty dict."""
    try:
        from config import YOUTUBE_PROXY_URL
        if YOUTUBE_PROXY_URL:
            return {
                "http://": YOUTUBE_PROXY_URL,
                "https://": YOUTUBE_PROXY_URL,
            }
    except ImportError:
        pass
    return {}


def _get_yt_api_instance() -> "YouTubeTranscriptApi":
    """Create YouTubeTranscriptApi instance with proxy if configured."""
    if not YT_TRANSCRIPT_API_AVAILABLE:
        raise ImportError("youtube_transcript_api not installed")

    # Try Webshare proxy first (residential, most reliable)
    try:
        from config import WEBSHARE_PROXY_USERNAME, WEBSHARE_PROXY_PASSWORD
        if WEBSHARE_PROXY_USERNAME and WEBSHARE_PROXY_PASSWORD and _WEBSHARE_AVAILABLE:
            logger.info("Using Webshare residential proxy for YouTube")
            proxy_config = WebshareProxyConfig(
                proxy_username=WEBSHARE_PROXY_USERNAME,
                proxy_password=WEBSHARE_PROXY_PASSWORD,
            )
            return YouTubeTranscriptApi(proxy_config=proxy_config)
    except (ImportError, Exception) as e:
        logger.debug(f"Webshare proxy not configured: {e}")

    # Try generic HTTP proxy via cookie/proxy workaround
    try:
        from config import YOUTUBE_PROXY_URL
        if YOUTUBE_PROXY_URL:
            logger.info(f"Using HTTP proxy for YouTube: {YOUTUBE_PROXY_URL.split('@')[-1] if '@' in YOUTUBE_PROXY_URL else YOUTUBE_PROXY_URL}")
            # youtube_transcript_api v1.x supports generic proxy via GenericProxyConfig
            try:
                from youtube_transcript_api.proxies import GenericProxyConfig
                proxy_config = GenericProxyConfig(
                    http_url=YOUTUBE_PROXY_URL,
                    https_url=YOUTUBE_PROXY_URL,
                )
                return YouTubeTranscriptApi(proxy_config=proxy_config)
            except ImportError:
                logger.debug("GenericProxyConfig not available in this version")
    except (ImportError, Exception) as e:
        logger.debug(f"HTTP proxy not configured: {e}")

    # Try cookie-based auth (last resort)
    try:
        from config import YOUTUBE_COOKIES_PATH
        if YOUTUBE_COOKIES_PATH:
            from pathlib import Path
            cookie_path = Path(YOUTUBE_COOKIES_PATH)
            if cookie_path.exists():
                logger.info("Cookie path configured for YouTube transcript API")
                # NOTE: youtube_transcript_api v1.x does not support cookie_path in constructor.
                # We keep this branch as a logged hint and fall through to direct client init.
    except (ImportError, Exception) as e:
        logger.debug(f"Cookie auth not configured: {e}")

    # No proxy — direct connection
    return YouTubeTranscriptApi()


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

    proxy_map = _get_proxy_config()
    async with httpx.AsyncClient(timeout=20, proxy=proxy_map.get("https://") or None) as client:
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
    proxy_map = _get_proxy_config()
    async with httpx.AsyncClient(timeout=20, proxy=proxy_map.get("https://") or None) as client:
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


async def _get_transcript_via_yt_api(
    video_id: str,
    language: str = "en",
) -> ResultDict:
    """
    youtube_transcript_api v1.x ile transcript al.
    Strateji: önce list() ile mevcut dilleri bul, sonra fetch() ile al.
    Hangi dilde varsa onu al, çeviri sonra deep_translator ile yapılır.
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
        try:
            api = _get_yt_api_instance()

            # Önce mevcut transcript'leri listele
            detected_lang = "en"
            source_type = "yt_transcript_api"
            fetched = None

            try:
                transcript_list = api.list(video_id)
                logger.info(f"yt_transcript_api: listed transcripts for {video_id}")

                # Mevcut dilleri logla
                available_langs = []
                for t in transcript_list:
                    available_langs.append(f"{t.language_code}({'auto' if t.is_generated else 'manual'})")
                logger.info(f"yt_transcript_api: available languages: {available_langs}")

                # Strateji: herhangi bir dilde al (önce manual, sonra auto)
                best_transcript = None

                # 1. Manuel transcript ara (herhangi bir dil)
                try:
                    for t in transcript_list:
                        if not t.is_generated:
                            best_transcript = t
                            break
                except Exception:
                    pass

                # 2. Otomatik transcript ara (herhangi bir dil)
                if not best_transcript:
                    try:
                        for t in transcript_list:
                            if t.is_generated:
                                best_transcript = t
                                break
                    except Exception:
                        pass

                if best_transcript:
                    detected_lang = best_transcript.language_code
                    source_type = "yt_transcript_api_manual" if not best_transcript.is_generated else "yt_transcript_api_auto"
                    logger.info(f"yt_transcript_api: fetching {detected_lang} ({source_type})")
                    fetched = api.fetch(video_id, languages=[detected_lang])
                else:
                    logger.warning(f"yt_transcript_api: no transcripts found in list for {video_id}")

            except Exception as list_err:
                logger.warning(f"yt_transcript_api: list() failed: {list_err}, trying direct fetch...")

            # Fallback: direkt fetch (parametresiz — ilk mevcut dili alır)
            if fetched is None:
                try:
                    fetched = api.fetch(video_id)
                    logger.info(f"yt_transcript_api: direct fetch succeeded for {video_id}")
                except Exception as fetch_err:
                    logger.error(f"yt_transcript_api: fetch() also failed: {fetch_err}")
                    return {
                        "success": False, "transcript": None, "source": None,
                        "language": None,
                        "error": f"yt_transcript_api: {fetch_err}",
                    }

            raw_data = fetched.to_raw_data()
            logger.info(f"yt_transcript_api: got {len(raw_data)} raw segments")

            segments = []
            for item in raw_data:
                text = str(item.get("text", "")).strip()
                if text:
                    start = float(item.get("start", 0))
                    dur = float(item.get("duration", 0))
                    segments.append({
                        "start": round(start, 2),
                        "end": round(start + dur, 2),
                        "text": text,
                    })

            if not segments:
                return {
                    "success": False, "transcript": None, "source": None,
                    "language": None, "error": "yt_transcript_api: no segments found after parsing",
                }

            full_text = " ".join(s["text"] for s in segments)
            logger.info(f"yt_transcript_api: success — {len(segments)} segments, {len(full_text)} chars, lang={detected_lang}")
            return {
                "success": True,
                "transcript": {
                    "full_text": full_text,
                    "segments": segments,
                    "word_count": len(full_text.split()),
                },
                "source": source_type,
                "language": detected_lang,
                "error": None,
            }
        except Exception as e:
            logger.error(f"yt_transcript_api: unexpected error: {e}", exc_info=True)
            return {
                "success": False, "transcript": None, "source": None,
                "language": None,
                "error": f"yt_transcript_api: {e}",
            }

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _fetch_sync)


# ── Web scraping fallback — YouTube watch page ───────────────────


async def _get_transcript_via_web_scrape(video_id: str) -> ResultDict:
    """
    Fallback: YouTube watch sayfasından captionTracks JSON'ını scrape et.
    Bu yöntem normal bir tarayıcı isteği gibi görünür ve genellikle
    API-level IP ban'lerden etkilenmez.
    """
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    proxy_map = _get_proxy_config()

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(
            timeout=20,
            proxy=proxy_map.get("https://") or None,
            follow_redirects=True,
        ) as client:
            resp = await client.get(watch_url, headers=headers)
            resp.raise_for_status()
            html = resp.text

        # captionTracks JSON'ını HTML'den çek
        # YouTube sayfasında "captionTracks": [...] şeklinde gömülü
        caption_pattern = re.compile(r'"captionTracks"\s*:\s*(\[.*?\])', re.DOTALL)
        match = caption_pattern.search(html)

        if not match:
            # Alternatif pattern — playerCaptionsTracklistRenderer içinde
            alt_pattern = re.compile(
                r'"playerCaptionsTracklistRenderer"\s*:\s*\{.*?"captionTracks"\s*:\s*(\[.*?\])',
                re.DOTALL,
            )
            match = alt_pattern.search(html)

        if not match:
            return {
                "success": False,
                "transcript": None,
                "source": None,
                "language": None,
                "error": "web_scrape: no captionTracks found in page HTML",
            }

        import json

        try:
            # JSON string'i temizle — bazen escape karakterleri var
            raw_json = match.group(1)
            # Unicode escape'leri düzelt
            raw_json = raw_json.encode().decode("unicode_escape", errors="replace")
            tracks = json.loads(raw_json)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"web_scrape: JSON parse failed: {e}")
            return {
                "success": False,
                "transcript": None,
                "source": None,
                "language": None,
                "error": f"web_scrape: JSON parse error: {e}",
            }

        if not tracks:
            return {
                "success": False,
                "transcript": None,
                "source": None,
                "language": None,
                "error": "web_scrape: captionTracks array is empty",
            }

        # İlk track'i al (genellikle en iyi eşleşme)
        chosen = tracks[0]
        for t in tracks:
            lang = t.get("languageCode", "")
            if lang == "en":
                chosen = t
                break

        base_url = chosen.get("baseUrl", "")
        actual_lang = chosen.get("languageCode", "en")
        kind = chosen.get("kind", "")
        source = "web_scrape_auto" if kind == "asr" else "web_scrape_manual"

        if not base_url:
            return {
                "success": False,
                "transcript": None,
                "source": None,
                "language": None,
                "error": "web_scrape: no baseUrl in caption track",
            }

        logger.info(f"web_scrape: found caption track — lang={actual_lang}, kind={kind}")

        # Transcript XML'i indir
        xml_text = await _download_transcript_xml(base_url)
        segments = _parse_transcript_xml(xml_text)

        if not segments:
            return {
                "success": False,
                "transcript": None,
                "source": None,
                "language": None,
                "error": "web_scrape: no segments parsed from XML",
            }

        full_text = " ".join(s["text"] for s in segments)
        logger.info(f"web_scrape: success — {len(segments)} segments, {len(full_text)} chars, lang={actual_lang}")

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
        logger.error(f"web_scrape: failed: {e}", exc_info=True)
        return {
            "success": False,
            "transcript": None,
            "source": None,
            "language": None,
            "error": f"web_scrape: {e}",
        }


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

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _translate_sync)


async def get_transcript(
    url: str,
    language: str = "en",
    target_language: Optional[str] = None,
    use_whisper_fallback: bool = True,
    whisper_model: str = "base",
) -> ResultDict:
    """
    Extract transcript with multi-method fallback:
    1. youtube_transcript_api (primary — robust, multi-language, works on cloud IPs)
    2. InnerTube API (fallback — no deps but unreliable on server/cloud IPs)

    If target_language is set and differs from source, auto-translates via deep_translator.
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

    result = None

    # ── Primary: youtube_transcript_api (daha güvenilir, özellikle sunucularda) ──
    if YT_TRANSCRIPT_API_AVAILABLE:
        logger.info(f"Trying youtube_transcript_api (primary) for {video_id}...")
        yt_api_result = await _get_transcript_via_yt_api(video_id, language)
        if yt_api_result.get("success"):
            result = yt_api_result
        else:
            logger.warning(f"youtube_transcript_api failed: {yt_api_result.get('error')}")
    else:
        logger.warning("youtube_transcript_api not available, skipping primary method")

    # ── Fallback: InnerTube API ──────────────────────────────────────
    if not result or not result.get("success"):
        logger.info(f"Trying InnerTube (fallback) for {video_id}...")
        try:
            player_data = await _fetch_innertube_player(video_id)

            playability = player_data.get("playabilityStatus", {})
            if playability.get("status") == "ERROR":
                innertube_error = playability.get("reason", "Video unavailable")
                logger.warning(f"InnerTube: video error — {innertube_error}")
                if result is None:
                    result = {
                        "success": False,
                        "transcript": None,
                        "source": None,
                        "language": None,
                        "error": innertube_error,
                    }
            else:
                tracks = _extract_caption_tracks(player_data)
                if not tracks:
                    logger.warning("InnerTube: no caption tracks found")
                    if result is None:
                        result = {
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
                            result = {
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
                            logger.info(f"InnerTube fallback succeeded: {actual_lang}, {len(segments)} segments")

        except Exception as e:
            logger.warning(f"InnerTube fallback failed: {e}")

    # ── Fallback 3: Web scrape (YouTube watch page HTML'den caption URL çek) ──
    if not result or not result.get("success"):
        logger.info(f"Trying web scrape (fallback 3) for {video_id}...")
        scrape_result = await _get_transcript_via_web_scrape(video_id)
        if scrape_result.get("success"):
            result = scrape_result
        else:
            logger.warning(f"Web scrape failed: {scrape_result.get('error')}")

    # ── Auto-translate if target_language differs ─────────────────
    if result is None:
        result = {
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
            logger.info(f"Auto-translating from {result.get('language')} to {target_language}...")
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
                logger.info(f"Translation successful to {target_language}")
            else:
                logger.warning(f"Translation failed: {tr_result.get('error')}")

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
