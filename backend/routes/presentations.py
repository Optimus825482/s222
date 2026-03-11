"""
AI-Powered Presentation Builder — generate, enhance, and regenerate slides.
Uses NVIDIA-hosted LLMs for research + orchestration, web search for context.
"""

import asyncio
import colorsys
import json
import logging
import random
import re
import sys
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import openai

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import get_current_user, _audit
from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, MODELS
from tools.search import web_search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/presentations", tags=["presentations"])

# ── Color Utilities ───────────────────────────────────────────────────

def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    rgb_values: tuple[int, int, int] = (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )
    return rgb_values


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB tuple to hex color."""
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def rgb_to_hsl(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert RGB to HSL (hue, saturation, lightness) all 0-1."""
    r_norm, g_norm, b_norm = r / 255, g / 255, b / 255
    h, l, s = colorsys.rgb_to_hls(r_norm, g_norm, b_norm)
    return (h, s, l)


def hsl_to_rgb(h: float, s: float, l: float) -> tuple[int, int, int]:
    """Convert HSL to RGB."""
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (int(r * 255), int(g * 255), int(b * 255))


def get_luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance (WCAG formula)."""
    def linearize(c: float) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def get_contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """Calculate contrast ratio between two hex colors (WCAG)."""
    fg_rgb = hex_to_rgb(fg_hex)
    bg_rgb = hex_to_rgb(bg_hex)
    fg_lum = get_luminance(*fg_rgb)
    bg_lum = get_luminance(*bg_rgb)
    lighter = max(fg_lum, bg_lum)
    darker = min(fg_lum, bg_lum)
    return (lighter + 0.05) / (darker + 0.05)


def adjust_lightness_for_contrast(hex_color: str, target_contrast: float, against_light: bool) -> str:
    """Adjust color lightness to achieve target contrast against white or black."""
    rgb = hex_to_rgb(hex_color)
    h, s, _ = rgb_to_hsl(*rgb)
    bg_lum = 1.0 if against_light else 0.0
    
    lo = 0.0 if against_light else 0.5
    hi = 0.5 if against_light else 1.0
    
    for _ in range(50):
        mid = (lo + hi) / 2
        test_rgb = hsl_to_rgb(h, s, mid)
        fg_lum = get_luminance(*test_rgb)
        lighter = max(fg_lum, bg_lum)
        darker = min(fg_lum, bg_lum)
        contrast = (lighter + 0.05) / (darker + 0.05)
        
        if against_light:
            if contrast < target_contrast:
                hi = mid
            else:
                lo = mid
        else:
            if contrast < target_contrast:
                lo = mid
            else:
                hi = mid
    
    final_l = lo if against_light else hi
    return rgb_to_hex(*hsl_to_rgb(h, s, final_l))


def generate_harmonious_palette(base_hue: float, is_dark: bool = True) -> dict[str, str]:
    """Generate a harmonious color palette from a base hue.
    
    Args:
        base_hue: Base hue value (0-1)
        is_dark: Whether to generate a dark theme palette
        
    Returns:
        Dict with background, text, accent, accent_secondary, muted colors
    """
    # Saturation and lightness values for harmonious palette
    if is_dark:
        # Dark theme: dark background, light text
        bg_sat, bg_light = 0.15, 0.08 + random.uniform(0, 0.04)  # Very dark with slight tint
        text_sat, text_light = 0.02, 0.95  # Nearly white
        accent_sat = 0.7 + random.uniform(0, 0.2)
        accent_light = 0.55 + random.uniform(0, 0.15)
        accent2_hue = (base_hue + 0.4 + random.uniform(-0.1, 0.1)) % 1.0  # Complementary-ish
        muted_sat, muted_light = 0.1, 0.5
    else:
        # Light theme: light background, dark text
        bg_sat, bg_light = 0.03, 0.98  # Nearly white with slight tint
        text_sat, text_light = 0.1, 0.12  # Nearly black
        accent_sat = 0.65 + random.uniform(0, 0.25)
        accent_light = 0.45 + random.uniform(0, 0.1)
        accent2_hue = (base_hue + 0.4 + random.uniform(-0.1, 0.1)) % 1.0
        muted_sat, muted_light = 0.05, 0.45
    
    # Generate base colors
    bg_rgb = hsl_to_rgb(base_hue, bg_sat, bg_light)
    text_rgb = hsl_to_rgb(base_hue, text_sat, text_light)
    accent_rgb = hsl_to_rgb(base_hue, accent_sat, accent_light)
    accent2_rgb = hsl_to_rgb(accent2_hue, accent_sat, accent_light)
    muted_rgb = hsl_to_rgb(base_hue, muted_sat, muted_light)
    
    bg_hex = rgb_to_hex(*bg_rgb)
    text_hex = rgb_to_hex(*text_rgb)
    accent_hex = rgb_to_hex(*accent_rgb)
    accent2_hex = rgb_to_hex(*accent2_rgb)
    muted_hex = rgb_to_hex(*muted_rgb)
    
    # Ensure contrast compliance (WCAG AA: 4.5:1 for text)
    # Adjust text for contrast against background
    text_contrast = get_contrast_ratio(text_hex, bg_hex)
    if text_contrast < 4.5:
        text_hex = adjust_lightness_for_contrast(text_hex, 4.5, not is_dark)
    
    # Ensure accent has sufficient contrast for readability
    accent_contrast = get_contrast_ratio(accent_hex, bg_hex)
    if accent_contrast < 3.0:
        accent_hex = adjust_lightness_for_contrast(accent_hex, 3.0, not is_dark)
    
    return {
        "background": bg_hex,
        "text": text_hex,
        "accent": accent_hex,
        "accent_secondary": accent2_hex,
        "muted": muted_hex,
    }


def generate_slide_color(index: int, total: int, style: str = "professional") -> dict[str, str]:
    """Generate a unique color palette for a slide.
    
    Creates varied but harmonious colors across slides to avoid "same colors" issue.
    
    Args:
        index: Slide index (0-based)
        total: Total number of slides
        style: Presentation style (affects color choices)
        
    Returns:
        Dict with background, text, accent, accent_secondary, muted colors
    """
    # Define style-specific hue ranges
    style_hues = {
        "professional": [0.55, 0.65],  # Blues
        "creative": [0.0, 0.15],  # Reds, oranges
        "minimal": [0.0, 0.02],  # Near-neutral
        "academic": [0.58, 0.62],  # Blues
        "corporate": [0.58, 0.65],  # Blues with purple
    }
    
    hue_range = style_hues.get(style, style_hues["professional"])
    
    # Distribute hues across slides with golden ratio for natural variation
    golden_ratio = 0.618033988749895
    base_hue = hue_range[0] + (hue_range[1] - hue_range[0]) * ((index * golden_ratio) % 1.0)
    
    # Add subtle variation
    base_hue += random.uniform(-0.05, 0.05)
    base_hue = base_hue % 1.0
    
    # Determine if first/last slides should be dark (for impact)
    is_dark = True
    if style == "minimal":
        is_dark = index == 0 or index == total - 1  # Only first/last dark
    elif total > 4 and 2 <= index < total - 2:
        # Mix dark and light for middle slides
        is_dark = random.random() > 0.4
    
    return generate_harmonious_palette(base_hue, is_dark)


# ── LLM Client ───────────────────────────────────────────────────

_llm_client: openai.AsyncOpenAI | None = None


def _get_llm_client() -> openai.AsyncOpenAI:
    global _llm_client
    if _llm_client is None:
        if not NVIDIA_API_KEY:
            raise HTTPException(503, "NVIDIA API key not configured")
        _llm_client = openai.AsyncOpenAI(
            api_key=NVIDIA_API_KEY,
            base_url=NVIDIA_BASE_URL,
        )
    return _llm_client


# ── Pydantic Models ──────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=8000)
    slide_count: int = Field(default=8, ge=3, le=30)
    language: str = Field(default="tr", max_length=5)
    style: str = Field(default="professional", max_length=30)


class EnhancePromptRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=8000)


class RegenerateSlideRequest(BaseModel):
    presentation_context: str = Field(..., min_length=1, max_length=5000)
    slide_index: int = Field(..., ge=0)
    instruction: str = Field(..., min_length=1, max_length=1000)


class ImagePromptRequest(BaseModel):
    slide_title: str = Field(..., min_length=1, max_length=500)
    slide_content: str = Field(..., max_length=2000)
    user_instruction: str = Field(default="", max_length=500)


class SlideSchema(BaseModel):
    id: int
    title: str
    content: str
    bullets: list[str]
    notes: str
    image_prompt: str
    layout: str
    colors: dict[str, str] = Field(
        default_factory=lambda: {
            "background": "#0f172a",
            "text": "#f8fafc",
            "accent": "#3b82f6",
            "accent_secondary": "#8b5cf6",
            "muted": "#64748b",
        }
    )


# ── Helpers ──────────────────────────────────────────────────────

def _extract_json(text: str) -> Any:
    """Extract JSON from LLM response — handles ```json blocks and raw JSON."""
    # Try ```json ... ``` block first
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        candidate = m.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Try raw JSON (first { or [ to last } or ])
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue

    raise ValueError(f"No valid JSON found in LLM response (length={len(text)})")


async def _llm_call(
    model_key: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int | None = None,
    timeout_seconds: float = 60,
) -> str:
    """Unified LLM call with error handling and timeout."""
    client = _get_llm_client()
    model_cfg = MODELS.get(model_key)
    if not model_cfg:
        raise HTTPException(500, f"Model config not found: {model_key}")

    try:
        async with asyncio.timeout(timeout_seconds):
            resp = await client.chat.completions.create(
                model=model_cfg["id"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=model_cfg.get("temperature", 0.7),
                top_p=model_cfg.get("top_p", 0.9),
                max_tokens=max_tokens or model_cfg.get("max_tokens", 4096),
            )
        content = resp.choices[0].message.content
        if not content:
            raise ValueError("Empty LLM response")
        return content.strip()
    except TimeoutError:
        logger.error("LLM call timed out (%s) after %ss", model_key, timeout_seconds)
        raise HTTPException(504, f"AI model timed out after {timeout_seconds}s")
    except openai.APIError as e:
        logger.error("LLM API error (%s): %s", model_key, e)
        raise HTTPException(502, f"LLM service error: {e.message}")
    except Exception as e:
        logger.error("LLM call failed (%s): %s", model_key, e)
        raise HTTPException(502, f"LLM call failed: {type(e).__name__}")


async def _research_topic(prompt: str, language: str) -> str:
    """Run web searches and summarize findings using researcher model."""
    # Generate 3 search queries from the prompt
    query_prompt = (
        f"Generate exactly 3 concise web search queries to research this presentation topic.\n"
        f"Topic: {prompt}\n"
        f"Language preference: {language}\n\n"
        f"Return ONLY a JSON array of 3 strings, nothing else.\n"
        f'Example: ["query 1", "query 2", "query 3"]'
    )

    try:
        raw = await _llm_call("critic", "You generate search queries.", query_prompt, timeout_seconds=30)
        queries: list[str] = _extract_json(raw)
        if not isinstance(queries, list) or len(queries) == 0:
            queries = [prompt]
        queries = queries[:3]
    except Exception:
        logger.warning("Query generation failed, using raw prompt")
        queries = [prompt]

    # Execute searches concurrently
    search_tasks = [web_search(q, max_results=3) for q in queries]
    all_results = await asyncio.gather(*search_tasks, return_exceptions=True)

    # Compile research context
    research_parts: list[str] = []
    for result_item in all_results:
        if isinstance(result_item, BaseException):
            continue
        result_rows = cast(list[dict[str, Any]], result_item)
        for r in result_rows:
            research_parts.append(
                f"- [{r.get('title', '')}]({r.get('url', '')}): {r.get('snippet', '')}"
            )

    if not research_parts:
        return "No web research results available. Generate content from general knowledge."

    research_text = "\n".join(research_parts[:9])  # Cap at 9 snippets for faster LLM response

    # Summarize with researcher model
    summary = await _llm_call(
        "speed",
        "You are a research assistant. Summarize the following web search results into key facts and insights for a presentation. Be concise and factual.",
        f"Topic: {prompt}\n\nSearch Results:\n{research_text}",
        timeout_seconds=45,
    )
    return summary


# ── Endpoints ────────────────────────────────────────────────────

LAYOUT_OPTIONS = ["title", "content", "two-column", "image-focus", "quote", "closing"]


@router.post("/generate")
async def generate_presentation(
    body: GenerateRequest,
    user: dict = Depends(get_current_user),
):
    """Generate a full presentation from a prompt using research + LLM orchestration."""
    logger.info("Generating presentation: user=%s, slides=%d", user["user_id"], body.slide_count)

    # Truncate prompt to keep LLM input manageable
    user_prompt_text = body.prompt[:2500]

    # Phase 1: Research
    try:
        research_context = await _research_topic(user_prompt_text, body.language)
    except Exception as e:
        logger.warning("Research phase failed, continuing without: %s", e)
        research_context = "No research available. Use general knowledge."

    # Phase 2: Generate structured slides
    system_prompt = """You are a world-class presentation architect who creates compelling, visually-driven slide decks.

DESIGN PRINCIPLES:
- ONE core idea per slide — never overload
- Titles must be punchy and specific (max 8 words), not generic ("Sonuç" → "AI 2026'da Kodlamayı Yeniden Tanımlıyor")
- Content text is a SHORT supporting sentence (max 25 words), not a paragraph
- Bullets are crisp insights (max 12 words each), not full sentences
- Use VARIED layouts to create visual rhythm — never use "content" layout more than 2x in a row
- "quote" layout: content = the quote text, bullets[0] = attribution
- "two-column" layout: ideal for comparisons, before/after, pros/cons
- "image-focus" layout: use when a visual tells the story better than text
- image_prompt must be cinematic and specific — describe scene, lighting, style, mood

COLOR PALETTE DESIGN:
- Each slide has a unique color palette for visual variety
- Colors must have WCAG AA contrast (4.5:1 for text, 3:1 for large text)
- Dark themes: dark backgrounds (#0a0a0a to #1a1a2e range) with light text (#f0f0f0)
- Light themes: light backgrounds (#fafafa to #f5f5f5) with dark text (#1a1a1a)
- Accent colors: vibrant for emphasis, harmonious with background
- NEVER use pure white (#ffffff) or pure black (#000000) backgrounds

Return ONLY valid JSON — no markdown, no explanation."""

    slide_generation_prompt = f"""Create a {body.slide_count}-slide presentation.

Topic: {body.prompt}
Language: {body.language}
Style: {body.style}

Research Context:
{research_context}

Return a JSON object:
{{
  "slides": [
    {{
      "id": 1,
      "title": "Short punchy title (max 8 words)",
      "content": "One supporting sentence (max 25 words)",
      "bullets": ["Crisp point (max 12 words)", "Another crisp point"],
      "notes": "Speaker notes",
      "image_prompt": "Cinematic English prompt: subject, scene, lighting, style, mood, color palette",
      "layout": "title",
      "colors": {{
        "background": "#0f172a",
        "text": "#f8fafc",
        "accent": "#3b82f6",
        "accent_secondary": "#8b5cf6",
        "muted": "#64748b"
      }}
    }}
  ]
}}

COLOR PALETTE RULES:
- background: Dark (#0a0a14 to #1e1e2e) for impact slides, light (#f8f9fa) for content slides
- text: Must have 4.5:1 contrast ratio against background
- accent: Vibrant color for highlights and emphasis
- accent_secondary: Harmonious complementary color
- muted: Low saturation for secondary text and borders
- VARY colors between slides - avoid identical palettes

LAYOUT STRATEGY for {body.slide_count} slides:
- Slide 1: "title" — bold opening with topic + subtitle
- Slide 2-{body.slide_count - 1}: Mix these layouts for visual variety:
  * "content" — standard bullet points (use max 2-3 times total)
  * "two-column" — comparisons, data vs insight, text vs visual
  * "image-focus" — when the image IS the message, minimal text
  * "quote" — expert quote or key statistic as centerpiece
- Slide {body.slide_count}: "closing" — memorable takeaway + call to action

STRICT RULES:
- Exactly {body.slide_count} slides
- All text in {body.language} language
- image_prompt MUST be in English, be specific and cinematic (not generic clip-art descriptions)
- Titles: max 8 words, specific and engaging — avoid generic titles like "Giriş", "Sonuç", "Genel Bakış"
- Content: max 25 words — this is a subtitle, NOT a paragraph
- Bullets: 2-4 per slide, max 12 words each — punchy, not sentences
- NEVER use the same layout 3 times in a row
- NEVER give all slides the same colors - vary backgrounds and accents
- Speaker notes should be conversational guidance for the presenter
- Style tone: {body.style}"""

    raw_response = await _llm_call("speed", system_prompt, slide_generation_prompt, timeout_seconds=120)

    try:
        data = _extract_json(raw_response)
    except ValueError:
        logger.error("Failed to parse slides JSON from LLM response")
        raise HTTPException(502, "Failed to parse presentation structure from AI response")

    # Validate and normalize slides
    slides_raw = data.get("slides") if isinstance(data, dict) else data
    if not isinstance(slides_raw, list) or len(slides_raw) == 0:
        raise HTTPException(502, "AI returned empty or invalid slides array")

    slides: list[dict[str, Any]] = []
    for i, s in enumerate(slides_raw):
        if not isinstance(s, dict):
            continue
        layout = s.get("layout", "content")
        if i == 0:
            layout = "title"
        elif i == len(slides_raw) - 1:
            layout = "closing"
        elif layout not in LAYOUT_OPTIONS:
            layout = "content"

        # Handle colors - use LLM provided or generate harmonious palette
        colors = s.get("colors")
        if not isinstance(colors, dict) or not all(k in colors for k in ["background", "text", "accent"]):
            # Generate colors programmatically with contrast checking
            colors = generate_slide_color(i, len(slides_raw), body.style)
        else:
            # Validate and fix contrast if needed
            bg = str(colors.get("background", "#0f172a"))
            text = str(colors.get("text", "#f8fafc"))
            if not bg.startswith("#"):
                bg = "#0f172a"
            if not text.startswith("#"):
                text = "#f8fafc"
            try:
                contrast = get_contrast_ratio(text, bg)
                if contrast < 4.5:
                    # Fix contrast by adjusting text color
                    is_light_bg = sum(hex_to_rgb(bg)) > 384  # ~128 per channel
                    text = adjust_lightness_for_contrast(text, 4.5, is_light_bg)
            except Exception:
                bg, text = "#0f172a", "#f8fafc"
            
            colors = {
                "background": bg,
                "text": text,
                "accent": str(colors.get("accent", "#3b82f6")),
                "accent_secondary": str(colors.get("accent_secondary", "#8b5cf6")),
                "muted": str(colors.get("muted", "#64748b")),
            }

        slides.append({
            "id": i + 1,
            "title": str(s.get("title", f"Slide {i + 1}")),
            "content": str(s.get("content", "")),
            "bullets": [str(b) for b in s.get("bullets", [])][:5],
            "notes": str(s.get("notes", "")),
            "image_prompt": str(s.get("image_prompt", "")),
            "layout": layout,
            "colors": colors,
        })

    _audit("presentation_generate", user["user_id"], detail=f"slides={len(slides)}, prompt={body.prompt[:80]}")
    logger.info("Presentation generated: %d slides for user %s", len(slides), user["user_id"])

    return {"slides": slides, "slide_count": len(slides), "language": body.language, "style": body.style}


@router.post("/enhance-prompt")
async def enhance_prompt(
    body: EnhancePromptRequest,
    user: dict = Depends(get_current_user),
):
    """Improve a raw presentation prompt with AI suggestions."""
    system_prompt = (
        "You are a presentation strategist. Transform vague topics into focused, compelling presentation briefs. "
        "Think about narrative arc, audience engagement, and visual storytelling. Return ONLY valid JSON."
    )

    user_prompt = f"""Transform this raw idea into a detailed presentation brief:
"{body.prompt}"

Return JSON:
{{
  "enhanced_prompt": "A detailed brief that includes: 1) Clear thesis/angle, 2) Target audience, 3) Key narrative arc (opening hook → evidence → insight → call to action), 4) 3-5 specific subtopics to cover, 5) Suggested visual themes",
  "suggested_slide_count": 8,
  "suggested_style": "professional"
}}

RULES:
- enhanced_prompt should be 150-300 words, structured as a creative brief
- Don't just expand the topic — give it an ANGLE and a STORY
- suggested_slide_count: 5-8 for focused talks, 10-15 for deep dives, 15-20 for comprehensive
- Style options: professional, creative, minimal, academic, corporate"""

    raw = await _llm_call("speed", system_prompt, user_prompt, timeout_seconds=30)

    try:
        result = _extract_json(raw)
    except ValueError:
        raise HTTPException(502, "Failed to parse enhanced prompt from AI response")

    if not isinstance(result, dict) or "enhanced_prompt" not in result:
        raise HTTPException(502, "AI returned invalid enhancement structure")

    # Sanitize output
    enhanced = {
        "enhanced_prompt": str(result["enhanced_prompt"])[:7000],
        "suggested_slide_count": max(3, min(30, int(result.get("suggested_slide_count", 8)))),
        "suggested_style": str(result.get("suggested_style", "professional")),
    }

    _audit("presentation_enhance", user["user_id"], detail=f"prompt={body.prompt[:80]}")
    return enhanced


@router.post("/regenerate-slide")
async def regenerate_slide(
    body: RegenerateSlideRequest,
    user: dict = Depends(get_current_user),
):
    """Regenerate a single slide with specific instructions."""
    system_prompt = (
        "You are a presentation designer. Regenerate a single slide based on the context and instruction. "
        "Return ONLY valid JSON for one slide object. Include a harmonious color palette."
    )

    user_prompt = f"""Regenerate slide at index {body.slide_index}.

Presentation context:
{body.presentation_context}

User instruction: {body.instruction}

Return JSON for a single slide:
{{
  "id": {body.slide_index + 1},
  "title": "Slide title",
  "content": "Main content paragraph",
  "bullets": ["Point 1", "Point 2", "Point 3"],
  "notes": "Speaker notes",
  "image_prompt": "English image generation prompt",
  "layout": "content",
  "colors": {{
    "background": "#0f172a",
    "text": "#f8fafc",
    "accent": "#3b82f6",
    "accent_secondary": "#8b5cf6",
    "muted": "#64748b"
  }}
}}

Layout options: {LAYOUT_OPTIONS}

Color rules:
- background: Dark (#0a0a14 to #1e1e2e) or light (#f8f9fa)
- text: Must contrast well with background
- accent: Vibrant highlight color
- Vary from any colors in the presentation context"""

    raw = await _llm_call("speed", system_prompt, user_prompt, timeout_seconds=45)

    try:
        slide_data = _extract_json(raw)
    except ValueError:
        raise HTTPException(502, "Failed to parse regenerated slide from AI response")

    if not isinstance(slide_data, dict):
        raise HTTPException(502, "AI returned invalid slide structure")

    layout = slide_data.get("layout", "content")
    if layout not in LAYOUT_OPTIONS:
        layout = "content"

    # Handle colors
    colors = slide_data.get("colors")
    if not isinstance(colors, dict) or not all(k in colors for k in ["background", "text", "accent"]):
        colors = generate_slide_color(body.slide_index, 5, "professional")
    else:
        # Validate colors
        bg = str(colors.get("background", "#0f172a"))
        text = str(colors.get("text", "#f8fafc"))
        if not bg.startswith("#"):
            bg = "#0f172a"
        if not text.startswith("#"):
            text = "#f8fafc"
        try:
            contrast = get_contrast_ratio(text, bg)
            if contrast < 4.5:
                is_light_bg = sum(hex_to_rgb(bg)) > 384
                text = adjust_lightness_for_contrast(text, 4.5, is_light_bg)
        except Exception:
            bg, text = "#0f172a", "#f8fafc"
        
        colors = {
            "background": bg,
            "text": text,
            "accent": str(colors.get("accent", "#3b82f6")),
            "accent_secondary": str(colors.get("accent_secondary", "#8b5cf6")),
            "muted": str(colors.get("muted", "#64748b")),
        }

    slide = {
        "id": body.slide_index + 1,
        "title": str(slide_data.get("title", f"Slide {body.slide_index + 1}")),
        "content": str(slide_data.get("content", "")),
        "bullets": [str(b) for b in slide_data.get("bullets", [])][:5],
        "notes": str(slide_data.get("notes", "")),
        "image_prompt": str(slide_data.get("image_prompt", "")),
        "layout": layout,
        "colors": colors,
    }

    _audit("presentation_regenerate_slide", user["user_id"], detail=f"slide_index={body.slide_index}")
    return {"slide": slide}


@router.post("/generate-image-prompt")
async def generate_image_prompt(
    body: ImagePromptRequest,
    user: dict = Depends(get_current_user),
):
    """Generate a new image prompt for a specific slide."""
    system_prompt = (
        "You are a visual design expert. Generate a detailed, descriptive image prompt "
        "suitable for AI image generation (e.g., Pollinations.ai). "
        "The prompt should be in English and describe a professional, visually appealing image. "
        "Return ONLY valid JSON."
    )

    instruction_part = f"\nUser instruction: {body.user_instruction}" if body.user_instruction else ""

    user_prompt = f"""Generate an image prompt for this presentation slide:

Title: {body.slide_title}
Content: {body.slide_content}{instruction_part}

Return JSON:
{{
  "image_prompt": "A detailed English prompt describing the image to generate"
}}"""

    raw = await _llm_call("speed", system_prompt, user_prompt, timeout_seconds=30)

    try:
        result = _extract_json(raw)
    except ValueError:
        raise HTTPException(502, "Failed to parse image prompt from AI response")

    image_prompt = str(result.get("image_prompt", "")) if isinstance(result, dict) else ""
    if not image_prompt:
        raise HTTPException(502, "AI returned empty image prompt")

    _audit("presentation_image_prompt", user["user_id"], detail=f"slide={body.slide_title[:50]}")
    return {"image_prompt": image_prompt}
