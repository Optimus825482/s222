"""
Export Service — Professional PDF & Markdown export with Turkish character support.
Uses ReportLab for PDF generation with proper pagination, headers, and Unicode fonts.
"""

from __future__ import annotations

import io
import os
import re
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ── Font Registration (Turkish character support) ────────────────

_FONT_REGISTERED = False

def _register_fonts():
    """Register a Unicode-capable font for Turkish characters."""
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return

    # Try Windows system fonts first
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        # Linux fallbacks
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]

    bold_paths = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/tahomabd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]

    registered_regular = False
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont("TRFont", fp))
                registered_regular = True
                break
            except Exception:
                continue

    registered_bold = False
    for fp in bold_paths:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont("TRFontBold", fp))
                registered_bold = True
                break
            except Exception:
                continue

    if not registered_regular:
        # Fallback — use Helvetica (limited Turkish support)
        pass

    _FONT_REGISTERED = True


def _get_font_name(bold: bool = False) -> str:
    """Get registered font name."""
    _register_fonts()
    if bold:
        try:
            pdfmetrics.getFont("TRFontBold")
            return "TRFontBold"
        except KeyError:
            pass
    try:
        pdfmetrics.getFont("TRFont")
        return "TRFont"
    except KeyError:
        return "Helvetica-Bold" if bold else "Helvetica"


# ── PDF Styles ───────────────────────────────────────────────────

def _build_styles() -> dict[str, ParagraphStyle]:
    """Build PDF paragraph styles with Turkish font support."""
    font = _get_font_name()
    font_bold = _get_font_name(bold=True)

    return {
        "title": ParagraphStyle(
            "CustomTitle",
            fontName=font_bold,
            fontSize=22,
            leading=28,
            spaceAfter=12,
            textColor=HexColor("#1a1a2e"),
            alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "CustomSubtitle",
            fontName=font,
            fontSize=11,
            leading=14,
            spaceAfter=20,
            textColor=HexColor("#666666"),
            alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "CustomH1",
            fontName=font_bold,
            fontSize=16,
            leading=22,
            spaceBefore=18,
            spaceAfter=8,
            textColor=HexColor("#16213e"),
        ),
        "h2": ParagraphStyle(
            "CustomH2",
            fontName=font_bold,
            fontSize=13,
            leading=18,
            spaceBefore=14,
            spaceAfter=6,
            textColor=HexColor("#0f3460"),
        ),
        "h3": ParagraphStyle(
            "CustomH3",
            fontName=font_bold,
            fontSize=11,
            leading=15,
            spaceBefore=10,
            spaceAfter=4,
            textColor=HexColor("#533483"),
        ),
        "body": ParagraphStyle(
            "CustomBody",
            fontName=font,
            fontSize=10,
            leading=14,
            spaceAfter=6,
            textColor=HexColor("#333333"),
            alignment=TA_JUSTIFY,
        ),
        "bullet": ParagraphStyle(
            "CustomBullet",
            fontName=font,
            fontSize=10,
            leading=14,
            spaceAfter=3,
            leftIndent=20,
            textColor=HexColor("#333333"),
        ),
        "code": ParagraphStyle(
            "CustomCode",
            fontName="Courier",
            fontSize=8,
            leading=11,
            spaceAfter=6,
            leftIndent=10,
            backColor=HexColor("#f5f5f5"),
            textColor=HexColor("#2d2d2d"),
        ),
        "footer": ParagraphStyle(
            "CustomFooter",
            fontName=font,
            fontSize=8,
            textColor=HexColor("#999999"),
            alignment=TA_CENTER,
        ),
    }


# ── Markdown to PDF Elements ────────────────────────────────────

def _escape_xml(text: str) -> str:
    """Escape XML special characters for ReportLab paragraphs."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


def _md_to_flowables(markdown_text: str, styles: dict) -> list:
    """Convert markdown text to ReportLab flowable elements."""
    flowables = []
    lines = markdown_text.split("\n")
    in_code_block = False
    code_buffer = []

    for line in lines:
        stripped = line.strip()

        # Code block toggle
        if stripped.startswith("```"):
            if in_code_block:
                # End code block
                code_text = _escape_xml("\n".join(code_buffer))
                if code_text.strip():
                    flowables.append(Paragraph(code_text.replace("\n", "<br/>"), styles["code"]))
                    flowables.append(Spacer(1, 4))
                code_buffer = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_buffer.append(line)
            continue

        # Empty line
        if not stripped:
            flowables.append(Spacer(1, 4))
            continue

        # Horizontal rule
        if stripped in ("---", "***", "___"):
            flowables.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#cccccc")))
            flowables.append(Spacer(1, 6))
            continue

        # Headers
        if stripped.startswith("### "):
            text = _escape_xml(stripped[4:])
            flowables.append(Paragraph(text, styles["h3"]))
            continue
        if stripped.startswith("## "):
            text = _escape_xml(stripped[3:])
            flowables.append(Paragraph(text, styles["h2"]))
            continue
        if stripped.startswith("# "):
            text = _escape_xml(stripped[2:])
            flowables.append(Paragraph(text, styles["h1"]))
            continue

        # Bullet points
        if stripped.startswith(("- ", "* ", "• ")):
            text = _escape_xml(stripped[2:])
            flowables.append(Paragraph(f"• {text}", styles["bullet"]))
            continue

        # Numbered lists
        num_match = re.match(r"^(\d+)\.\s+(.+)", stripped)
        if num_match:
            num, text = num_match.groups()
            text = _escape_xml(text)
            flowables.append(Paragraph(f"{num}. {text}", styles["bullet"]))
            continue

        # Checkbox items
        if stripped.startswith(("- [ ] ", "- [x] ", "- [X] ")):
            checked = stripped[3] in ("x", "X")
            mark = "☑" if checked else "☐"
            text = _escape_xml(stripped[6:])
            flowables.append(Paragraph(f"{mark} {text}", styles["bullet"]))
            continue

        # Bold text inline
        text = _escape_xml(stripped)
        # Convert **bold** to <b>bold</b>
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

        flowables.append(Paragraph(text, styles["body"]))

    return flowables


# ── PDF Generation ───────────────────────────────────────────────

def _header_footer(canvas, doc):
    """Draw header and footer on each page."""
    canvas.saveState()
    font = _get_font_name()

    # Footer: page number
    canvas.setFont(font, 8)
    canvas.setFillColor(HexColor("#999999"))
    page_num = f"Sayfa {doc.page}"
    canvas.drawCentredString(A4[0] / 2, 15 * mm, page_num)

    # Header line (not on first page)
    if doc.page > 1:
        canvas.setStrokeColor(HexColor("#e0e0e0"))
        canvas.setLineWidth(0.5)
        canvas.line(2 * cm, A4[1] - 1.5 * cm, A4[0] - 2 * cm, A4[1] - 1.5 * cm)

    canvas.restoreState()


def generate_pdf(markdown_content: str, title: str = "Rapor") -> bytes:
    """
    Generate a professional PDF from markdown content.
    Returns PDF as bytes.
    """
    _register_fonts()
    styles = _build_styles()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2.5 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title=title,
        author="Multi-Agent Ops Center",
    )

    flowables = []

    # Title page elements
    flowables.append(Spacer(1, 3 * cm))
    flowables.append(Paragraph(_escape_xml(title), styles["title"]))
    flowables.append(Spacer(1, 0.5 * cm))

    from datetime import datetime
    date_str = datetime.now().strftime("%d %B %Y, %H:%M")
    flowables.append(Paragraph(f"Oluşturulma: {date_str}", styles["subtitle"]))
    flowables.append(Paragraph("Multi-Agent Ops Center", styles["subtitle"]))
    flowables.append(Spacer(1, 1 * cm))
    flowables.append(HRFlowable(width="60%", thickness=1, color=HexColor("#0f3460")))
    flowables.append(Spacer(1, 1 * cm))

    # Content
    content_flowables = _md_to_flowables(markdown_content, styles)
    flowables.extend(content_flowables)

    doc.build(flowables, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buffer.getvalue()

def generate_presentation_pdf(pptx_path: str, title: str = "Sunum") -> bytes:
    """
    Read a PPTX file and generate a professional PDF with slide content.
    Each slide becomes a section in the PDF with title + bullets.
    """
    from pptx import Presentation as PptxPresentation

    _register_fonts()
    styles = _build_styles()

    # Add slide-specific styles
    font = _get_font_name()
    font_bold = _get_font_name(bold=True)
    slide_title_style = ParagraphStyle(
        "SlideTitle",
        fontName=font_bold,
        fontSize=14,
        leading=20,
        spaceBefore=16,
        spaceAfter=8,
        textColor=HexColor("#0f3460"),
        borderWidth=0,
        borderPadding=0,
    )
    slide_num_style = ParagraphStyle(
        "SlideNum",
        fontName=font_bold,
        fontSize=9,
        leading=12,
        textColor=HexColor("#999999"),
    )
    slide_body_style = ParagraphStyle(
        "SlideBody",
        fontName=font,
        fontSize=10,
        leading=15,
        spaceAfter=4,
        leftIndent=15,
        textColor=HexColor("#333333"),
    )

    prs = PptxPresentation(pptx_path)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2.5 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title=title,
        author="Multi-Agent Ops Center",
    )

    flowables = []

    # Title page
    flowables.append(Spacer(1, 3 * cm))
    flowables.append(Paragraph(_escape_xml(title), styles["title"]))
    flowables.append(Spacer(1, 0.5 * cm))

    from datetime import datetime
    date_str = datetime.now().strftime("%d %B %Y, %H:%M")
    flowables.append(Paragraph(f"Oluşturulma: {date_str}", styles["subtitle"]))
    flowables.append(Paragraph(f"{len(prs.slides)} Slayt | AI Destekli Sunum", styles["subtitle"]))
    flowables.append(Spacer(1, 1 * cm))
    flowables.append(HRFlowable(width="60%", thickness=1, color=HexColor("#0f3460")))
    flowables.append(PageBreak())

    # Extract slides
    for i, slide in enumerate(prs.slides, 1):
        # Slide number
        flowables.append(Paragraph(f"Slayt {i}/{len(prs.slides)}", slide_num_style))

        # Extract all text from slide shapes
        texts = []
        slide_title_text = ""
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for para in shape.text_frame.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                texts.append(text)

        # First text is usually the title
        if texts:
            slide_title_text = texts[0]
            body_texts = texts[1:]
        else:
            slide_title_text = f"Slayt {i}"
            body_texts = []

        flowables.append(Paragraph(_escape_xml(slide_title_text), slide_title_style))

        # Body content
        for text in body_texts:
            escaped = _escape_xml(text)
            flowables.append(Paragraph(f"• {escaped}", slide_body_style))

        flowables.append(Spacer(1, 6))
        flowables.append(HRFlowable(width="100%", thickness=0.3, color=HexColor("#e0e0e0")))
        flowables.append(Spacer(1, 4))

    doc.build(flowables, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buffer.getvalue()



def generate_presentation_pdf(pptx_path: str, title: str = "Sunum") -> bytes:
    """
    Read a PPTX file and generate a professional PDF with slide content.
    Each slide becomes a section in the PDF with title + bullets.
    """
    from pptx import Presentation as PptxPresentation

    _register_fonts()
    styles = _build_styles()

    font = _get_font_name()
    font_bold = _get_font_name(bold=True)
    slide_title_style = ParagraphStyle(
        "SlideTitle",
        fontName=font_bold,
        fontSize=14,
        leading=20,
        spaceBefore=16,
        spaceAfter=8,
        textColor=HexColor("#0f3460"),
    )
    slide_num_style = ParagraphStyle(
        "SlideNum",
        fontName=font_bold,
        fontSize=9,
        leading=12,
        textColor=HexColor("#999999"),
    )
    slide_body_style = ParagraphStyle(
        "SlideBody",
        fontName=font,
        fontSize=10,
        leading=15,
        spaceAfter=4,
        leftIndent=15,
        textColor=HexColor("#333333"),
    )

    prs = PptxPresentation(pptx_path)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2.5 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title=title,
        author="Multi-Agent Ops Center",
    )

    flowables = []

    # Title page
    flowables.append(Spacer(1, 3 * cm))
    flowables.append(Paragraph(_escape_xml(title), styles["title"]))
    flowables.append(Spacer(1, 0.5 * cm))

    from datetime import datetime
    date_str = datetime.now().strftime("%d %B %Y, %H:%M")
    flowables.append(Paragraph(f"Oluşturulma: {date_str}", styles["subtitle"]))
    flowables.append(Paragraph(f"{len(prs.slides)} Slayt | AI Destekli Sunum", styles["subtitle"]))
    flowables.append(Spacer(1, 1 * cm))
    flowables.append(HRFlowable(width="60%", thickness=1, color=HexColor("#0f3460")))
    flowables.append(PageBreak())

    # Extract slides
    for i, slide in enumerate(prs.slides, 1):
        flowables.append(Paragraph(f"Slayt {i}/{len(prs.slides)}", slide_num_style))

        texts = []
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for para in shape.text_frame.paragraphs:
                text = para.text.strip()
                if text:
                    texts.append(text)

        if texts:
            slide_title_text = texts[0]
            body_texts = texts[1:]
        else:
            slide_title_text = f"Slayt {i}"
            body_texts = []

        flowables.append(Paragraph(_escape_xml(slide_title_text), slide_title_style))

        for text in body_texts:
            flowables.append(Paragraph(f"• {_escape_xml(text)}", slide_body_style))

        flowables.append(Spacer(1, 6))
        flowables.append(HRFlowable(width="100%", thickness=0.3, color=HexColor("#e0e0e0")))
        flowables.append(Spacer(1, 4))

    doc.build(flowables, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buffer.getvalue()
