from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
import asyncio
import sys
import re
from pathlib import Path
_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)
from deps import get_current_user, _audit
router = APIRouter()

# ── Memory Endpoints ─────────────────────────────────────────────

@router.get("/api/memory/stats")
async def api_memory_stats(user: dict = Depends(get_current_user)):
    """Get layered memory statistics."""
    try:
        from tools.memory import get_memory_stats
        return await get_memory_stats()
    except Exception as e:
        return {"error": str(e), "total_memories": 0}


@router.get("/api/memory/layers")
async def api_memory_layers(user: dict = Depends(get_current_user)):
    """Get memories grouped by layer."""
    try:
        from tools.memory import list_memories
        working = await list_memories(layer="working", limit=10)
        episodic = await list_memories(layer="episodic", limit=20)
        semantic = await list_memories(layer="semantic", limit=20)
        return {"working": working, "episodic": episodic, "semantic": semantic}
    except Exception as e:
        return {"working": [], "episodic": [], "semantic": [], "error": str(e)}


@router.delete("/api/memory/{memory_id}")
async def api_delete_memory(memory_id: int, user: dict = Depends(get_current_user)):
    try:
        from tools.memory import delete_memory
        ok = await delete_memory(memory_id)
        if not ok:
            raise HTTPException(404, "Memory not found")
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, str(e))


@router.get("/api/db/health")
async def api_db_health():
    """Check PostgreSQL connection health."""
    try:
        from tools.pg_connection import get_conn, release_conn
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()
        cur.close()
        release_conn(conn)
        return {"status": "ok", "backend": "postgresql", "version": str(version)}
    except Exception as e:
        return {"status": "error", "backend": "sqlite_fallback", "error": str(e)}


# ── Memory Advanced Endpoints ────────────────────────────────────

@router.get("/api/memory/correlate")
async def api_memory_correlate(
    query: str,
    max_results: int = 10,
    time_window_hours: int | None = None,
    user: dict = Depends(get_current_user),
):
    """Find correlated memories across layers and categories."""
    try:
        from tools.memory import correlate_memories
        return await correlate_memories(query, max_results, time_window_hours)
    except Exception as e:
        return {"clusters": [], "total_found": 0, "error": str(e)}


@router.get("/api/memory/timeline")
async def api_memory_timeline(
    hours: int = 24,
    group_by: str = "hour",
    user: dict = Depends(get_current_user),
):
    """Get memory creation timeline grouped by time intervals."""
    if group_by not in ("hour", "day", "category"):
        raise HTTPException(400, "group_by must be 'hour', 'day', or 'category'")
    try:
        from tools.memory import get_memory_timeline
        return get_memory_timeline(hours, group_by)
    except Exception as e:
        return []


@router.get("/api/memory/{memory_id}/related")
async def api_memory_related(
    memory_id: int,
    max_results: int = 5,
    user: dict = Depends(get_current_user),
):
    """Find memories related to a specific memory."""
    try:
        from tools.memory import find_related_memories
        return await find_related_memories(memory_id, max_results)
    except Exception as e:
        return []


# ── REST Endpoints: Project Export ───────────────────────────────

def _resolve_project_path(project_name: str):
    """Resolve project path and ensure it is under PROJECTS_DIR (path traversal safe)."""
    from tools.idea_to_project import PROJECTS_DIR
    project_name = project_name.strip()
    if "\x00" in project_name or ".." in project_name or Path(project_name).is_absolute():
        raise HTTPException(status_code=400, detail="Geçersiz dosya yolu")
    base = PROJECTS_DIR.resolve()
    path = (PROJECTS_DIR / project_name).resolve()
    if not path.is_relative_to(base) or path == base or not path.exists() or not path.is_dir():
        raise HTTPException(404, "Project not found")
    return path


@router.get("/api/projects")
async def api_list_projects(user: dict = Depends(get_current_user)):
    """List all generated idea-to-project outputs."""
    from tools.idea_to_project import PROJECTS_DIR, PHASES
    if not PROJECTS_DIR.exists():
        return []
    projects = []
    # Sort by creation time (oldest first) so the last element is the newest
    dirs = [d for d in PROJECTS_DIR.iterdir() if d.is_dir()]
    dirs.sort(key=lambda d: d.stat().st_ctime)
    for d in dirs:
        phases_done = [f.stem for f in d.glob("*.md")]
        projects.append({
            "name": d.name,
            "phases": phases_done,
            "phase_count": len(phases_done),
            "total_phases": len(PHASES),
        })
    return projects


@router.get("/api/projects/{project_name}/export")
async def api_export_project(project_name: str, user: dict = Depends(get_current_user)):
    """Export full project as a single combined Markdown document."""
    from tools.idea_to_project import PROJECTS_DIR, PHASES
    project_dir = _resolve_project_path(project_name)

    parts = [
        f"# 🚀 Proje Raporu\n",
        f"**Proje:** {project_name.replace('_', ' ').title()}\n",
        f"**Oluşturulma:** {__import__('datetime').datetime.now().strftime('%d %B %Y, %H:%M')}\n",
        f"**Pipeline:** Idea-to-Project (5 Faz)\n",
        "---\n",
    ]

    # Table of contents
    parts.append("## 📑 İçindekiler\n")
    for i, phase in enumerate(PHASES, 1):
        filepath = project_dir / f"{phase['id']}.md"
        status = "✅" if filepath.exists() else "⏳"
        parts.append(f"{i}. {status} {phase['name']}")
    parts.append("\n---\n")

    # Phase contents
    for i, phase in enumerate(PHASES, 1):
        filepath = project_dir / f"{phase['id']}.md"
        parts.append(f"\n## {i}. {phase['name']}\n")
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            parts.append(content)
        else:
            parts.append("*Bu faz henüz tamamlanmadı.*")
        parts.append("\n---\n")

    return {"markdown": "\n".join(parts), "project_name": project_name}


@router.get("/api/projects/{project_name}/export/pdf")
async def api_export_project_pdf(project_name: str, user: dict = Depends(get_current_user)):
    """Export full project as a professional PDF with Turkish character support."""
    from fastapi.responses import Response
    from tools.idea_to_project import PROJECTS_DIR, PHASES
    from tools.export_service import generate_pdf

    project_dir = _resolve_project_path(project_name)

    # Build markdown content
    parts = [
        f"# Proje Raporu\n",
        f"Proje: {project_name.replace('_', ' ').title()}\n",
        "---\n",
    ]
    for i, phase in enumerate(PHASES, 1):
        filepath = project_dir / f"{phase['id']}.md"
        parts.append(f"\n## {i}. {phase['name']}\n")
        if filepath.exists():
            parts.append(filepath.read_text(encoding="utf-8"))
        else:
            parts.append("*Bu faz henüz tamamlanmadı.*")
        parts.append("\n---\n")

    md_content = "\n".join(parts)
    title = project_name.replace("_", " ").title()
    pdf_bytes = generate_pdf(md_content, title=f"Proje Raporu: {title}")

    safe_name = project_name[:40]
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_rapor.pdf"'},
    )


# ── REST Endpoints: Presentation Generation ─────────────────────

class PresentationRequest(BaseModel):
    topic: str
    slide_count: int | None = None  # None = use mode default
    with_images: bool = True
    language: str = "tr"
    mode: str = "midi"  # mini, midi, maxi
    theme: str = "corporate"  # corporate, modern_dark, nature


@router.post("/api/presentation/generate")
async def api_generate_presentation(req: PresentationRequest):
    """
    Generate a PPTX presentation: deep research → agent content → AI visuals.
    Supports MINI/MIDI/MAXI modes and multiple themes.
    Returns the PPTX file as download.
    """
    from fastapi.responses import Response
    from tools.presentation_service import (
        build_presentation_prompt, parse_slide_content,
        generate_presentation, deep_research_for_presentation,
        format_research_for_prompt, MODE_CONFIG,
    )

    mode = req.mode.lower()
    if mode not in MODE_CONFIG:
        mode = "midi"
    cfg = MODE_CONFIG[mode]
    slide_count = req.slide_count or cfg["default_slides"]

    # Step 0: Deep Research — depth scales with mode
    research_context = ""
    try:
        research = await deep_research_for_presentation(
            req.topic, language=req.language,
            max_queries=cfg["research_queries"],
            mode=mode,
        )
        research_context = format_research_for_prompt(research)
    except Exception as e:
        print(f"[API] Presentation deep research failed: {e}")

    # Step 1: Use agent to create slide content DIRECTLY (not through orchestrator)
    from pipelines.engine import PipelineEngine
    from core.models import Thread as ThreadModel, AgentRole

    thread = ThreadModel()
    engine = PipelineEngine()

    prompt = build_presentation_prompt(
        req.topic, slide_count, req.language,
        research_context=research_context,
        mode=mode,
    )

    # Use thinker for MIDI/MAXI, researcher for MINI
    if mode in ("midi", "maxi"):
        content_agent = engine.get_agent(AgentRole.THINKER)
    else:
        content_agent = engine.get_agent(AgentRole.RESEARCHER)

    raw_content = await content_agent.execute(prompt, thread)

    # Fallback if primary agent failed
    if not raw_content or raw_content.startswith("[Error]") or len(raw_content.strip()) < 50:
        if mode in ("midi", "maxi"):
            content_agent = engine.get_agent(AgentRole.RESEARCHER)
        else:
            content_agent = engine.get_agent(AgentRole.THINKER)
        raw_content = await content_agent.execute(prompt, thread)

    # Step 2: Parse agent output into structured slides
    slides_data = parse_slide_content(raw_content)

    # Fallback: if parsing failed, create basic slides from raw content
    if not slides_data:
        paragraphs = [p.strip() for p in raw_content.split("\n\n") if p.strip()]
        for i, para in enumerate(paragraphs[:slide_count], 1):
            lines = [l.strip() for l in para.split("\n") if l.strip()]
            title = lines[0][:60] if lines else f"Slayt {i}"
            bullets = lines[1:6] if len(lines) > 1 else [para[:100]]
            slides_data.append({
                "num": i,
                "title": title,
                "bullets": bullets,
                "image_prompt": f"Professional visual about {req.topic}",
                "is_section": False,
                "quote": None,
                "data_highlights": [],
            })

    # Step 3: Generate PPTX with images and theme
    pptx_bytes = await generate_presentation(
        slides_data=slides_data,
        title=req.topic,
        subtitle=f"{cfg['emoji']} {cfg['label']} | {len(slides_data)} Slayt | AI Destekli Sunum",
        with_images=req.with_images,
        theme=req.theme,
    )

    safe_name = re.sub(r'[^\w\-]', '_', req.topic[:40].lower())
    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_{mode}_sunum.pptx"'},
    )


# ── Presentation File Endpoints ─────────────────────────────────

def _resolve_presentation_path(filename: str) -> Path:
    """Resolve presentation filename to path under pres_dir (base name only, no path traversal)."""
    filename = filename.strip()
    if "\x00" in filename or ".." in filename or Path(filename).is_absolute():
        raise HTTPException(status_code=400, detail="Geçersiz dosya yolu")
    safe_name = Path(filename).name
    pres_dir = Path(__file__).parent.parent / "data" / "presentations"
    pres_dir = pres_dir.resolve()
    filepath = (pres_dir / safe_name).resolve()
    if not filepath.is_relative_to(pres_dir) or not filepath.exists() or filepath.suffix.lower() != ".pptx":
        raise HTTPException(404, "Presentation not found")
    return filepath


def _resolve_image_path(filename: str) -> Path:
    """Resolve image filename to path under images_dir (base name only, no path traversal)."""
    filename = filename.strip()
    if "\x00" in filename or ".." in filename or Path(filename).is_absolute():
        raise HTTPException(status_code=400, detail="Geçersiz dosya yolu")
    safe_name = Path(filename).name
    images_dir = Path(__file__).parent.parent / "data" / "images"
    images_dir = images_dir.resolve()
    filepath = (images_dir / safe_name).resolve()
    if not filepath.is_relative_to(images_dir) or not filepath.exists():
        raise HTTPException(404, "Image not found")
    return filepath


@router.get("/api/presentations")
async def api_list_presentations(user: dict = Depends(get_current_user)):
    """List all generated presentations."""
    pres_dir = Path(__file__).parent.parent / "data" / "presentations"
    if not pres_dir.exists():
        return []
    files = sorted(pres_dir.glob("*.pptx"), key=lambda f: f.stat().st_mtime, reverse=True)
    return [
        {"name": f.stem, "filename": f.name, "size_kb": round(f.stat().st_size / 1024)}
        for f in files
    ]


@router.get("/api/presentations/{filename}/download")
async def api_download_presentation(filename: str, user: dict = Depends(get_current_user)):
    """Download a generated PPTX file."""
    from fastapi.responses import FileResponse
    filepath = _resolve_presentation_path(filename)
    return FileResponse(
        path=str(filepath),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filepath.name,
    )


# ── User image generation (model choice + prompt improve) ─────────

IMAGE_MODELS = ["zimage", "flux", "imagen-4", "grok-imagine"]


class ImageGenerateRequest(BaseModel):
    prompt: str
    model: str = "imagen-4"
    width: int = 512
    height: int = 512


class ImageImprovePromptRequest(BaseModel):
    prompt: str


def _images_dir() -> Path:
    """Return data/images directory for saving generated images."""
    images_dir = Path(__file__).parent.parent / "data" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    return images_dir.resolve()


def _get_pollinations_api_key() -> str:
    import os
    return (os.environ.get("POLLINATIONS_API_KEY") or os.environ.get("Pollinations_api_key") or "").strip()


@router.post("/api/images/generate")
async def api_images_generate(request: Request, req: ImageGenerateRequest, user: dict = Depends(get_current_user)):
    """Generate image from prompt. Saves only to data/images/ (files) — not to agent memory or RAG.
    With API key tries gen.pollinations.ai first (nologo, enhance); then public as fallback."""
    import urllib.parse
    import httpx
    import uuid
    import base64
    import logging

    logger = logging.getLogger(__name__)
    model = (req.model or "flux").lower().strip()
    if model not in IMAGE_MODELS:
        model = "flux"
    prompt = (req.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt boş olamaz")
    # Pollinations URL length limit ~2000; keep prompt ≤200 chars to avoid 400
    if len(prompt) > 200:
        logger.warning("Prompt too long (%s chars), truncating to 200", len(prompt))
        prompt = prompt[:197] + "..."
    width = max(512, min(2048, req.width))
    height = max(512, min(2048, req.height))
    encoded = urllib.parse.quote(prompt)
    if len(encoded) + 200 > 1800:
        prompt = "artificial intelligence technology digital art"
        encoded = urllib.parse.quote(prompt)

    def save_and_return(content: bytes, ext: str) -> dict:
        filename = f"img_{uuid.uuid4().hex[:12]}{ext}"
        filepath = _images_dir() / filename
        filepath.write_bytes(content)
        b64 = base64.b64encode(content).decode("utf-8")
        _audit("image_generate", user["user_id"], f"model={model} filename={filename}")
        base_url = str(request.base_url).rstrip("/")
        download_path = f"/api/images/{filename}/download"
        return {
            "filename": filename,
            "download_url": download_path,
            "image_url": f"{base_url}{download_path}",
            "image_base64": b64,
            "model": model,
            "prompt": prompt[:200],
        }

    def content_type_ext(resp) -> str:
        ct = (resp.headers.get("content-type") or "").lower()
        return ".png" if "png" in ct else ".jpg"

    last_error: list[str] = []
    timeout_gen = 65.0
    timeout_public = 20.0

    # 1) API key varsa önce gen.pollinations.ai dene (hızlı sonuç; public sık 502 ve uzun bekletiyor)
    api_key = _get_pollinations_api_key()
    if api_key:
        headers = {"Accept": "image/jpeg, image/png", "Authorization": f"Bearer {api_key}"}
        models_to_try = [model] if model == "flux" else [model, "flux"]
        for try_model in models_to_try:
            url_gen = (
                f"https://gen.pollinations.ai/image/{encoded}"
                f"?model={try_model}&width={width}&height={height}&nologo=true&enhance=true"
            )
            try:
                async with httpx.AsyncClient(timeout=timeout_gen, follow_redirects=True) as client:
                    resp = await client.get(url_gen, headers=headers)
                    if resp.status_code == 200 and len(resp.content) > 500:
                        return save_and_return(resp.content, content_type_ext(resp))
                    if try_model == model:
                        last_error.append(f"gen HTTP {resp.status_code}: {(resp.text or '')[:200]}")
            except Exception as e:
                if try_model == model:
                    last_error.append(f"gen: {e}")
                    logger.exception("Image generate (gen) failed")

    # 2) Fallback: public endpoint (kısa timeout — 502 gelince uzun beklemeyelim)
    url_public = f"https://image.pollinations.ai/prompt/{encoded}?model={model}&width={width}&height={height}"
    try:
        async with httpx.AsyncClient(timeout=timeout_public, follow_redirects=True) as client:
            resp = await client.get(url_public)
            if resp.status_code == 200 and len(resp.content) > 500:
                return save_and_return(resp.content, content_type_ext(resp))
            last_error.append(f"public HTTP {resp.status_code}: {(resp.text or '')[:200]}")
    except Exception as e:
        last_error.append(f"public: {e}")

    detail = "Görsel oluşturulamadı: " + "; ".join(last_error) if last_error else "Görsel oluşturulamadı."
    raise HTTPException(status_code=502, detail=detail[:1000])


@router.post("/api/images/improve-prompt")
async def api_images_improve_prompt(req: ImageImprovePromptRequest, user: dict = Depends(get_current_user)):
    """Improve image generation prompt using DeepSeek; returns improved_prompt for the input."""
    import httpx
    from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

    prompt = (req.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt boş olamaz")
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=503, detail="DeepSeek API anahtarı yapılandırılmamış")

    system = (
        "You are a prompt engineer for AI image generation. "
        "Given an image prompt, return ONLY the improved, more descriptive prompt in English. "
        "Do not add explanations, prefixes, or quotes. Output nothing but the single improved prompt line."
    )
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 500,
        "temperature": 0.5,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            )
            if r.status_code != 200:
                raise HTTPException(status_code=502, detail=f"DeepSeek hatası: {r.status_code}")
            data = r.json()
            choice = (data.get("choices") or [{}])[0]
            improved = (choice.get("message") or {}).get("content") or prompt
            improved = improved.strip().strip('"').strip("'")
            if not improved:
                improved = prompt
            return {"improved_prompt": improved}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Prompt iyileştirme hatası: {str(e)}")


@router.get("/api/images")
async def api_list_images(user: dict = Depends(get_current_user)):
    """List saved images in data/images/ (filename, size_kb, created_at)."""
    import os
    images_dir = _images_dir()
    if not images_dir.exists():
        return []
    out = []
    for f in sorted(images_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            st = f.stat()
            out.append({
                "filename": f.name,
                "size_kb": round(st.st_size / 1024),
                "created_at": st.st_mtime,
            })
    return out


@router.delete("/api/images/{filename}")
async def api_delete_image(filename: str, user: dict = Depends(get_current_user)):
    """Delete a saved image by filename."""
    filepath = _resolve_image_path(filename)
    filepath.unlink()
    _audit("image_delete", user["user_id"], f"filename={filename}")
    return {"deleted": True, "filename": filename}


@router.get("/api/images/{filename}/download")
async def api_download_image(filename: str, user: dict = Depends(get_current_user)):
    """Download a generated image file."""
    from fastapi.responses import FileResponse
    filepath = _resolve_image_path(filename)
    suffix = filepath.suffix.lower()
    media_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    media_type = media_types.get(suffix, "image/jpeg")
    return FileResponse(
        path=str(filepath),
        media_type=media_type,
        filename=filepath.name,
    )


@router.get("/api/presentations/{filename}/pdf")
async def api_presentation_pdf(filename: str, user: dict = Depends(get_current_user)):
    """Export a PPTX presentation as a professional PDF with slide content."""
    from fastapi.responses import Response
    from tools.export_service import generate_presentation_pdf

    filepath = _resolve_presentation_path(filename)

    title = filepath.stem.replace("_", " ")
    pdf_bytes = generate_presentation_pdf(str(filepath), title=title)
    pdf_name = filepath.name.replace(".pptx", ".pdf")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{pdf_name}"'},
    )


# ── Generic Export Endpoints ─────────────────────────────────────

class ExportPdfRequest(BaseModel):
    markdown: str
    title: str = "Rapor"


@router.post("/api/export/pdf")
async def api_export_pdf(req: ExportPdfRequest, user: dict = Depends(get_current_user)):
    """Convert any markdown content to professional PDF."""
    from fastapi.responses import Response
    from tools.export_service import generate_pdf

    pdf_bytes = generate_pdf(req.markdown, title=req.title)
    safe_name = re.sub(r'[^\w\-]', '_', req.title[:40].lower())
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'},
    )


class ExportHtmlRequest(BaseModel):
    markdown: str
    title: str = "Rapor"


@router.post("/api/export/html")
async def api_export_html(req: ExportHtmlRequest, user: dict = Depends(get_current_user)):
    """Convert any markdown content to a standalone styled HTML report."""
    from fastapi.responses import Response
    from tools.export_service import generate_html

    html_content = generate_html(req.markdown, title=req.title)
    safe_name = re.sub(r'[^\w\-]', '_', req.title[:40].lower())
    return Response(
        content=html_content.encode("utf-8"),
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.html"'},
    )