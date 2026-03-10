"""
OCR Service — Text extraction from images and PDFs.
Uses pytesseract for image OCR and pdfplumber for PDF text extraction.
"""

from __future__ import annotations

import base64
import io
import os
import tempfile
from typing import Any

# Lazy imports to avoid startup errors if tesseract not installed
_pil_imported = False
_pytesseract_imported = False
_pdfplumber_imported = False

PIL_IMAGE = None
pytesseract = None
pdfplumber = None


def _ensure_imports():
    """Lazily import OCR dependencies."""
    global _pil_imported, _pytesseract_imported, _pdfplumber_imported
    global PIL_IMAGE, pytesseract, pdfplumber

    if not _pil_imported:
        try:
            from PIL import Image
            PIL_IMAGE = Image
            _pil_imported = True
        except ImportError:
            pass

    if not _pytesseract_imported:
        try:
            import pytesseract as _pytesseract
            pytesseract = _pytesseract
            _pytesseract_imported = True
        except ImportError:
            pass

    if not _pdfplumber_imported:
        try:
            import pdfplumber as _pdfplumber
            pdfplumber = _pdfplumber
            _pdfplumber_imported = True
        except ImportError:
            pass


def _check_tesseract_installed() -> bool:
    """Check if Tesseract OCR binary is available."""
    import shutil
    return shutil.which("tesseract") is not None


# Language code mapping for common languages
LANGUAGE_MAP = {
    "en": "eng",
    "english": "eng",
    "tr": "tur",
    "turkish": "tur",
    "de": "deu",
    "german": "deu",
    "fr": "fra",
    "french": "fra",
    "es": "spa",
    "spanish": "spa",
    "it": "ita",
    "italian": "ita",
    "pt": "por",
    "portuguese": "por",
    "ru": "rus",
    "russian": "rus",
    "zh": "chi_sim",
    "chinese": "chi_sim",
    "ja": "jpn",
    "japanese": "jpn",
    "ko": "kor",
    "korean": "kor",
    "ar": "ara",
    "arabic": "ara",
}


async def extract_text_from_image(
    image_source: str | bytes,
    language: str = "eng",
    preprocess: bool = True,
    dpi: int = 300,
) -> dict[str, Any]:
    """
    Extract text from an image using Tesseract OCR.

    Args:
        image_source: Path to image file, base64-encoded string, or raw bytes.
        language: OCR language code (e.g., 'eng', 'tur', 'deu').
                  Also accepts full names like 'english', 'turkish'.
        preprocess: Apply image preprocessing (grayscale, contrast enhancement).
        dpi: DPI for image processing (higher = better quality, slower).

    Returns:
        dict with keys:
            - text: Extracted text content
            - confidence: Average confidence score (0-100)
            - pages: Number of pages processed (always 1 for images)
            - language: Language code used
            - source_type: 'file', 'base64', or 'bytes'
            - word_count: Number of words extracted
            - char_count: Number of characters extracted
            - error: Error message if extraction failed
    """
    _ensure_imports()

    # Validate dependencies
    if PIL_IMAGE is None:
        return {
            "text": "",
            "confidence": 0,
            "pages": 0,
            "language": language,
            "source_type": "unknown",
            "word_count": 0,
            "char_count": 0,
            "error": "PIL/Pillow not installed. Install with: pip install Pillow",
        }

    if pytesseract is None:
        return {
            "text": "",
            "confidence": 0,
            "pages": 0,
            "language": language,
            "source_type": "unknown",
            "word_count": 0,
            "char_count": 0,
            "error": "pytesseract not installed. Install with: pip install pytesseract",
        }

    if not _check_tesseract_installed():
        return {
            "text": "",
            "confidence": 0,
            "pages": 0,
            "language": language,
            "source_type": "unknown",
            "word_count": 0,
            "char_count": 0,
            "error": "Tesseract OCR binary not found. Install Tesseract: https://github.com/tesseract-ocr/tesseract",
        }

    # Normalize language code
    lang_code = LANGUAGE_MAP.get(language.lower(), language)
    if lang_code.lower() in LANGUAGE_MAP:
        lang_code = LANGUAGE_MAP[lang_code.lower()]

    try:
        # Load image from source
        image = None
        source_type = "unknown"

        if isinstance(image_source, str):
            if os.path.isfile(image_source):
                # File path
                image = PIL_IMAGE.open(image_source)
                source_type = "file"
            elif image_source.startswith("data:image"):
                # Data URL: data:image/png;base64,xxxxx
                base64_data = image_source.split(",", 1)[-1]
                image_bytes = base64.b64decode(base64_data)
                image = PIL_IMAGE.open(io.BytesIO(image_bytes))
                source_type = "base64"
            else:
                # Assume base64-encoded string
                try:
                    image_bytes = base64.b64decode(image_source)
                    image = PIL_IMAGE.open(io.BytesIO(image_bytes))
                    source_type = "base64"
                except Exception:
                    return {
                        "text": "",
                        "confidence": 0,
                        "pages": 0,
                        "language": lang_code,
                        "source_type": "unknown",
                        "word_count": 0,
                        "char_count": 0,
                        "error": f"Could not load image from source",
                    }
        elif isinstance(image_source, bytes):
            image = PIL_IMAGE.open(io.BytesIO(image_source))
            source_type = "bytes"
        else:
            return {
                "text": "",
                "confidence": 0,
                "pages": 0,
                "language": lang_code,
                "source_type": "unknown",
                "word_count": 0,
                "char_count": 0,
                "error": f"Invalid image_source type: {type(image_source)}",
            }

        # Convert to RGB if necessary
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        # Preprocessing
        if preprocess:
            # Convert to grayscale for better OCR
            if image.mode != "L":
                image = image.convert("L")

            # Enhance contrast
            try:
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.5)
            except Exception:
                pass  # Skip enhancement if it fails

        # Run OCR with detailed data
        ocr_config = f"--dpi {dpi} --oem 3 --psm 6"

        # Get text
        text = pytesseract.image_to_string(image, lang=lang_code, config=ocr_config)

        # Get confidence data
        try:
            data = pytesseract.image_to_data(image, lang=lang_code, config=ocr_config, output_type=pytesseract.Output.DICT)
            confidences = [int(c) for c in data.get("conf", []) if c and str(c).isdigit() and int(c) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        except Exception:
            avg_confidence = 0

        # Clean text
        text = text.strip()

        return {
            "text": text,
            "confidence": round(avg_confidence, 1),
            "pages": 1,
            "language": lang_code,
            "source_type": source_type,
            "word_count": len(text.split()),
            "char_count": len(text),
            "error": None,
        }

    except Exception as e:
        return {
            "text": "",
            "confidence": 0,
            "pages": 0,
            "language": lang_code,
            "source_type": source_type if "source_type" in dir() else "unknown",
            "word_count": 0,
            "char_count": 0,
            "error": f"OCR error: {type(e).__name__}: {e}",
        }


async def extract_text_from_pdf(
    pdf_source: str | bytes,
    pages: str | None = None,
    extract_tables: bool = False,
) -> dict[str, Any]:
    """
    Extract text from a PDF file using pdfplumber.

    Args:
        pdf_source: Path to PDF file, base64-encoded string, or raw bytes.
        pages: Page range to extract (e.g., '1-5', '1,3,5', '1-3,5,7-9').
               None means all pages.
        extract_tables: Also extract tables as structured data.

    Returns:
        dict with keys:
            - text: Full extracted text content
            - pages_extracted: Number of pages processed
            - total_pages: Total pages in PDF
            - page_contents: List of per-page content (if detailed=True)
            - tables: List of extracted tables (if extract_tables=True)
            - word_count: Total words extracted
            - char_count: Total characters extracted
            - source_type: 'file', 'base64', or 'bytes'
            - error: Error message if extraction failed
    """
    _ensure_imports()

    if pdfplumber is None:
        return {
            "text": "",
            "pages_extracted": 0,
            "total_pages": 0,
            "page_contents": [],
            "tables": [],
            "word_count": 0,
            "char_count": 0,
            "source_type": "unknown",
            "error": "pdfplumber not installed. Install with: pip install pdfplumber",
        }

    def parse_page_range(page_range: str, total: int) -> list[int]:
        """Parse page range string like '1-5,7,9-11' into list of 1-indexed page numbers."""
        if not page_range:
            return list(range(1, total + 1))

        pages_to_extract = set()
        for part in page_range.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                try:
                    start = int(start.strip())
                    end = int(end.strip())
                    pages_to_extract.update(range(max(1, start), min(total, end) + 1))
                except ValueError:
                    pass
            else:
                try:
                    page_num = int(part)
                    if 1 <= page_num <= total:
                        pages_to_extract.add(page_num)
                except ValueError:
                    pass

        return sorted(pages_to_extract)

    temp_file = None
    source_type = "unknown"

    try:
        # Handle different input types
        if isinstance(pdf_source, str):
            if os.path.isfile(pdf_source):
                pdf_path = pdf_source
                source_type = "file"
            elif pdf_source.startswith("data:application/pdf"):
                # Data URL
                base64_data = pdf_source.split(",", 1)[-1]
                pdf_bytes = base64.b64decode(base64_data)
                temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
                temp_file.write(pdf_bytes)
                temp_file.close()
                pdf_path = temp_file.name
                source_type = "base64"
            else:
                # Assume base64-encoded string
                try:
                    pdf_bytes = base64.b64decode(pdf_source)
                    temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
                    temp_file.write(pdf_bytes)
                    temp_file.close()
                    pdf_path = temp_file.name
                    source_type = "base64"
                except Exception:
                    return {
                        "text": "",
                        "pages_extracted": 0,
                        "total_pages": 0,
                        "page_contents": [],
                        "tables": [],
                        "word_count": 0,
                        "char_count": 0,
                        "source_type": "unknown",
                        "error": "Could not decode PDF from source",
                    }
        elif isinstance(pdf_source, bytes):
            temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            temp_file.write(pdf_source)
            temp_file.close()
            pdf_path = temp_file.name
            source_type = "bytes"
        else:
            return {
                "text": "",
                "pages_extracted": 0,
                "total_pages": 0,
                "page_contents": [],
                "tables": [],
                "word_count": 0,
                "char_count": 0,
                "source_type": "unknown",
                "error": f"Invalid pdf_source type: {type(pdf_source)}",
            }

        # Open PDF
        all_text = []
        page_contents = []
        all_tables = []

        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)

            # Determine which pages to extract
            page_numbers = parse_page_range(pages, total_pages) if pages else list(range(1, total_pages + 1))

            for page_num in page_numbers:
                if page_num > total_pages:
                    continue

                page = pdf.pages[page_num - 1]  # 0-indexed in pdfplumber

                # Extract text
                text = page.extract_text() or ""

                page_contents.append({
                    "page": page_num,
                    "text": text,
                    "char_count": len(text),
                    "word_count": len(text.split()),
                })

                all_text.append(f"--- Page {page_num} ---\n{text}")

                # Extract tables if requested
                if extract_tables:
                    tables = page.extract_tables()
                    for i, table in enumerate(tables):
                        if table:
                            all_tables.append({
                                "page": page_num,
                                "table_index": i,
                                "rows": len(table),
                                "cols": len(table[0]) if table else 0,
                                "data": table,
                            })

        full_text = "\n\n".join(all_text)
        total_word_count = sum(p["word_count"] for p in page_contents)
        total_char_count = sum(p["char_count"] for p in page_contents)

        return {
            "text": full_text,
            "pages_extracted": len(page_contents),
            "total_pages": total_pages,
            "page_contents": page_contents,
            "tables": all_tables if extract_tables else [],
            "word_count": total_word_count,
            "char_count": total_char_count,
            "source_type": source_type,
            "error": None,
        }

    except Exception as e:
        return {
            "text": "",
            "pages_extracted": 0,
            "total_pages": 0,
            "page_contents": [],
            "tables": [],
            "word_count": 0,
            "char_count": 0,
            "source_type": source_type if "source_type" in dir() else "unknown",
            "error": f"PDF extraction error: {type(e).__name__}: {e}",
        }

    finally:
        # Clean up temp file
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except Exception:
                pass


async def extract_text(
    source: str | bytes,
    source_type: str = "auto",
    language: str = "eng",
    pages: str | None = None,
    extract_tables: bool = False,
) -> dict[str, Any]:
    """
    Universal text extraction from images or PDFs.

    Automatically detects file type based on:
    1. source_type hint ('image', 'pdf', 'auto')
    2. File extension (for file paths)
    3. Content sniffing (for bytes/base64)

    Args:
        source: File path, base64 string, or raw bytes.
        source_type: 'image', 'pdf', or 'auto' (default: auto-detect).
        language: OCR language for images.
        pages: Page range for PDFs.
        extract_tables: Extract tables from PDFs.

    Returns:
        Combined result dict with extraction details.
    """
    detected_type = source_type

    # Auto-detect type
    if source_type == "auto":
        if isinstance(source, str) and os.path.isfile(source):
            ext = os.path.splitext(source)[1].lower()
            if ext in (".pdf",):
                detected_type = "pdf"
            elif ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"):
                detected_type = "image"
            else:
                # Try PDF first, then image
                try:
                    with open(source, "rb") as f:
                        header = f.read(8)
                    if header.startswith(b"%PDF"):
                        detected_type = "pdf"
                    else:
                        detected_type = "image"
                except Exception:
                    detected_type = "image"
        elif isinstance(source, bytes):
            if source.startswith(b"%PDF"):
                detected_type = "pdf"
            else:
                detected_type = "image"
        elif isinstance(source, str):
            # Base64 or data URL
            if source.startswith("data:application/pdf"):
                detected_type = "pdf"
            elif source.startswith("data:image"):
                detected_type = "image"
            else:
                # Try to decode and check header
                try:
                    decoded = base64.b64decode(source[:100])
                    if decoded.startswith(b"%PDF"):
                        detected_type = "pdf"
                    else:
                        detected_type = "image"
                except Exception:
                    detected_type = "image"

    # Dispatch to appropriate extractor
    if detected_type == "pdf":
        result = await extract_text_from_pdf(
            pdf_source=source,
            pages=pages,
            extract_tables=extract_tables,
        )
        result["detected_type"] = "pdf"
    else:
        result = await extract_text_from_image(
            image_source=source,
            language=language,
        )
        result["detected_type"] = "image"

    return result


def format_ocr_result(result: dict[str, Any]) -> str:
    """Format OCR result for LLM context."""
    if result.get("error"):
        return f"<ocr_result>\n  <error>{result['error']}</error>\n</ocr_result>"

    detected_type = result.get("detected_type", "unknown")
    text = result.get("text", "")
    word_count = result.get("word_count", 0)
    char_count = result.get("char_count", 0)

    if detected_type == "pdf":
        pages_extracted = result.get("pages_extracted", 0)
        total_pages = result.get("total_pages", 0)
        tables = result.get("tables", [])
        table_info = f"\n  <tables_found>{len(tables)}</tables_found>" if tables else ""

        return (
            f"<ocr_result>\n"
            f"  <type>pdf</type>\n"
            f"  <pages>{pages_extracted}/{total_pages}</pages>\n"
            f"  <words>{word_count}</words>\n"
            f"  <chars>{char_count}</chars>{table_info}\n"
            f"  <content>\n{text}\n  </content>\n"
            f"</ocr_result>"
        )
    else:
        confidence = result.get("confidence", 0)
        language = result.get("language", "unknown")

        return (
            f"<ocr_result>\n"
            f"  <type>image</type>\n"
            f"  <language>{language}</language>\n"
            f"  <confidence>{confidence}%</confidence>\n"
            f"  <words>{word_count}</words>\n"
            f"  <chars>{char_count}</chars>\n"
            f"  <content>\n{text}\n  </content>\n"
            f"</ocr_result>"
        )