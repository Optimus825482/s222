"""
OCR (Optical Character Recognition) endpointleri.
Görsel ve PDF dosyalarından metin çıkarma.
Desteklenen formatlar: PNG, JPG, JPEG, GIF, BMP, WEBP, PDF

Uses tools/ocr_service.py for extraction logic.
"""

import asyncio
import logging
import sys
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from pydantic import BaseModel, Field

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import get_current_user, _audit

# Import OCR service for advanced extraction
try:
    from tools.ocr_service import (
        extract_text_from_image as svc_extract_image,
        extract_text_from_pdf as svc_extract_pdf,
        extract_text as svc_extract_universal,
        format_ocr_result,
    )
    OCR_SERVICE_AVAILABLE = True
except ImportError:
    OCR_SERVICE_AVAILABLE = False
    svc_extract_image = None
    svc_extract_pdf = None
    svc_extract_universal = None
    format_ocr_result = None

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ocr"])

# ── Constants ─────────────────────────────────────────────────────

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB for OCR files
MAX_EXTRACTED_CHARS = 500_000  # Limit output size

IMAGE_EXTENSIONS: set[str] = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif"}
PDF_EXTENSION: str = ".pdf"

SUPPORTED_MIME_TYPES: set[str] = {
    "image/png", "image/jpeg", "image/jpg", "image/gif",
    "image/bmp", "image/webp", "image/tiff",
    "application/pdf",
}


# ── Pydantic Models ───────────────────────────────────────────────

class OcrExtractResponse(BaseModel):
    """OCR extraction response model."""
    success: bool
    text: str = Field(default="", description="Extracted text content")
    char_count: int = Field(default=0, description="Number of characters extracted")
    word_count: int = Field(default=0, description="Number of words extracted")
    page_count: int = Field(default=0, description="Number of pages processed (PDF only)")
    file_type: str = Field(default="", description="Detected file type")
    filename: str = Field(default="", description="Original filename")
    language: str = Field(default="auto", description="Language used for OCR")
    confidence: Optional[float] = Field(default=None, description="OCR confidence score if available")
    tables: Optional[list] = Field(default=None, description="Extracted tables from PDF (if requested)")
    formatted_result: Optional[str] = Field(default=None, description="LLM-formatted OCR result")
    error: Optional[str] = Field(default=None, description="Error message if extraction failed")


class OcrLanguagesResponse(BaseModel):
    """Available OCR languages response."""
    languages: list[str]
    default: str
    service_available: bool = Field(default=True, description="Whether OCR service is available")


class OcrExtractRequest(BaseModel):
    """Request model for base64-encoded OCR extraction."""
    source: str = Field(..., description="Base64-encoded file content or file path")
    source_type: str = Field(default="auto", description="'image', 'pdf', or 'auto' for detection")
    language: str = Field(default="eng", description="OCR language code")
    pages: Optional[str] = Field(default=None, description="Page range for PDFs (e.g., '1-5,7,9')")
    extract_tables: bool = Field(default=False, description="Extract tables from PDFs")
    preprocess: bool = Field(default=True, description="Preprocess images for better OCR")
    return_formatted: bool = Field(default=False, description="Return LLM-formatted result")


# ── Helper Functions ───────────────────────────────────────────────

def _detect_file_type(filename: str, content_type: str) -> str:
    """Detect file type from filename and content type."""
    ext = Path(filename).suffix.lower() if filename else ""
    
    if ext == ".pdf" or content_type == "application/pdf":
        return "pdf"
    elif ext in IMAGE_EXTENSIONS or content_type.startswith("image/"):
        return "image"
    else:
        return "unknown"


def _validate_file(filename: str, content_type: str, content: bytes) -> str:
    """Validate file and return its type. Raises HTTPException if invalid."""
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    file_type = _detect_file_type(filename, content_type)
    
    if file_type == "unknown":
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type. Supported: images (PNG, JPG, GIF, BMP, WEBP, TIFF) and PDF"
        )
    
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file cannot be processed")
    
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)} MB"
        )
    
    return file_type


def _fallback_extract_image(image_path: Path, language: str = "auto") -> dict:
    """Fallback image extraction when OCR service is unavailable."""
    try:
        import pytesseract
        from PIL import Image
        
        img = Image.open(image_path)
        
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        
        lang = language if language != "auto" else None
        
        try:
            data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
            text = pytesseract.image_to_string(img, lang=lang)
            
            confidences = [
                int(conf) for conf, text_item in zip(data["conf"], data["text"])
                if conf != -1 and text_item.strip()
            ]
            avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else None
        except Exception:
            text = pytesseract.image_to_string(img, lang=lang)
            avg_confidence = None
        
        return {
            "text": text.strip(),
            "confidence": round(avg_confidence, 2) if avg_confidence else None,
            "word_count": len(text.split()),
            "error": None
        }
    
    except ImportError:
        return {
            "text": "",
            "confidence": None,
            "word_count": 0,
            "error": "pytesseract not installed. Install with: pip install pytesseract && apt-get install tesseract-ocr"
        }
    except Exception as e:
        logger.error(f"Image OCR error: {e}", exc_info=True)
        return {
            "text": "",
            "confidence": None,
            "word_count": 0,
            "error": str(e)
        }


def _fallback_extract_pdf(pdf_path: Path, language: str = "auto") -> dict:
    """Fallback PDF extraction when OCR service is unavailable."""
    try:
        import pdfplumber
        
        text_parts = []
        page_count = 0
        
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                
                if page_text.strip():
                    text_parts.append(f"--- Page {page_num + 1} ---\n{page_text.strip()}")
                else:
                    text_parts.append(f"--- Page {page_num + 1} ---\n[No extractable text - may be image-based]")
        
        full_text = "\n\n".join(text_parts)
        
        return {
            "text": full_text,
            "page_count": page_count,
            "word_count": len(full_text.split()),
            "confidence": None,
            "error": None
        }
    
    except ImportError:
        return {
            "text": "",
            "page_count": 0,
            "word_count": 0,
            "confidence": None,
            "error": "pdfplumber not installed. Install with: pip install pdfplumber"
        }
    except Exception as e:
        logger.error(f"PDF extraction error: {e}", exc_info=True)
        return {
            "text": "",
            "page_count": 0,
            "word_count": 0,
            "confidence": None,
            "error": str(e)
        }


# ── Endpoints ────────────────────────────────────────────────────

@router.post("/api/ocr/extract", response_model=OcrExtractResponse)
async def extract_text_from_file(
    file: UploadFile = File(..., description="Image or PDF file to extract text from"),
    language: str = Form(default="eng", description="OCR language code (e.g., 'eng', 'tur', 'deu')"),
    pages: Optional[str] = Form(default=None, description="Page range for PDFs (e.g., '1-5,7,9')"),
    extract_tables: bool = Form(default=False, description="Extract tables from PDFs"),
    preprocess: bool = Form(default=True, description="Preprocess images for better OCR"),
    return_formatted: bool = Form(default=False, description="Return LLM-formatted result"),
    user: dict = Depends(get_current_user),
):
    """Extract text from uploaded image or PDF file using OCR.
    
    **Supported formats:**
    - Images: PNG, JPG, JPEG, GIF, BMP, WEBP, TIFF
    - Documents: PDF
    
    **Language codes:**
    - 'eng': English (default)
    - 'tur': Turkish
    - 'deu': German
    - 'fra': French
    - 'spa': Spanish
    - And more... Use /api/ocr/languages to see all available.
    
    **PDF Options:**
    - `pages`: Extract specific pages (e.g., '1-5,7,9-11')
    - `extract_tables`: Also extract tables as structured data
    
    **Returns:**
    - Extracted text content
    - Character and word count
    - Page count (for PDFs)
    - OCR confidence (for images)
    - Tables (if requested and PDF)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    # Read file content
    content = await file.read()
    content_type = file.content_type or ""
    
    # Validate file
    file_type = _validate_file(file.filename, content_type, content)
    
    # Save to temp file for processing
    ext = Path(file.filename).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    
    try:
        # Use OCR service if available
        if OCR_SERVICE_AVAILABLE and svc_extract_image and svc_extract_pdf:
            if file_type == "image":
                result = await svc_extract_image(
                    image_source=str(tmp_path),
                    language=language,
                    preprocess=preprocess,
                )
                page_count = 1
                tables = None
            else:  # PDF
                result = await svc_extract_pdf(
                    pdf_source=str(tmp_path),
                    pages=pages,
                    extract_tables=extract_tables,
                )
                page_count = result.get("pages_extracted", result.get("total_pages", 0))
                tables = result.get("tables") if extract_tables else None
            
            text = result.get("text", "")
            word_count = result.get("word_count", len(text.split()))
            confidence = result.get("confidence")
            error = result.get("error")
        else:
            # Fallback to inline implementation
            if file_type == "image":
                result = _fallback_extract_image(tmp_path, language)
                page_count = 1
                tables = None
            else:
                result = _fallback_extract_pdf(tmp_path, language)
                page_count = result.get("page_count", 0)
                tables = None
            
            text = result.get("text", "")
            word_count = result.get("word_count", len(text.split()))
            confidence = result.get("confidence")
            error = result.get("error")
        
        # Truncate if too large
        truncated = False
        if len(text) > MAX_EXTRACTED_CHARS:
            text = text[:MAX_EXTRACTED_CHARS]
            truncated = True
        
        # Format result for LLM if requested
        formatted = None
        if return_formatted and OCR_SERVICE_AVAILABLE and format_ocr_result:
            formatted = format_ocr_result({
                **result,
                "text": text,
                "detected_type": file_type,
            })
        
        # Audit log
        _audit(
            "ocr_extract",
            user["user_id"],
            detail=f"{file.filename} ({len(content)} bytes, {file_type})"
        )
        
        return OcrExtractResponse(
            success=error is None,
            text=text,
            char_count=len(text),
            word_count=word_count,
            page_count=page_count,
            file_type=file_type,
            filename=file.filename,
            language=language,
            confidence=confidence,
            tables=tables,
            formatted_result=formatted,
            error=error
        )
    
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OCR extraction failed: {str(e)}")
    
    finally:
        # Clean up temp file
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


@router.post("/api/ocr/extract-base64", response_model=OcrExtractResponse)
async def extract_text_from_base64(
    request: OcrExtractRequest = Body(...),
    user: dict = Depends(get_current_user),
):
    """Extract text from base64-encoded image or PDF.
    
    **Use case:** Direct extraction without file upload (e.g., from frontend canvas, clipboard).
    
    **Request body:**
    - `source`: Base64-encoded file content (with or without data URL prefix)
    - `source_type`: 'image', 'pdf', or 'auto' (default: auto-detect)
    - `language`: OCR language code (default: 'eng')
    - `pages`: Page range for PDFs (e.g., '1-5,7,9')
    - `extract_tables`: Extract tables from PDFs
    - `preprocess`: Preprocess images for better OCR
    - `return_formatted`: Return LLM-formatted result
    """
    if not OCR_SERVICE_AVAILABLE or not svc_extract_universal:
        raise HTTPException(
            status_code=503,
            detail="OCR service not available. Please ensure tools/ocr_service.py is installed."
        )
    
    try:
        result = await svc_extract_universal(
            source=request.source,
            source_type=request.source_type,
            language=request.language,
            pages=request.pages,
            extract_tables=request.extract_tables,
        )
        
        text = result.get("text", "")
        detected_type = result.get("detected_type", "unknown")
        word_count = result.get("word_count", len(text.split()))
        error = result.get("error")
        
        # Truncate if too large
        if len(text) > MAX_EXTRACTED_CHARS:
            text = text[:MAX_EXTRACTED_CHARS]
        
        # Format for LLM if requested
        formatted = None
        if request.return_formatted and format_ocr_result:
            formatted = format_ocr_result(result)
        
        # Audit log
        _audit(
            "ocr_extract_base64",
            user["user_id"],
            detail=f"base64 {detected_type}"
        )
        
        return OcrExtractResponse(
            success=error is None,
            text=text,
            char_count=len(text),
            word_count=word_count,
            page_count=result.get("pages_extracted", result.get("total_pages", 1)),
            file_type=detected_type,
            filename="base64",
            language=request.language,
            confidence=result.get("confidence"),
            tables=result.get("tables") if request.extract_tables else None,
            formatted_result=formatted,
            error=error,
        )
    
    except Exception as e:
        logger.error(f"OCR base64 extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OCR extraction failed: {str(e)}")


@router.get("/api/ocr/languages", response_model=OcrLanguagesResponse)
async def list_ocr_languages(user: dict = Depends(get_current_user)):
    """List available OCR languages.
    
    Returns the list of Tesseract language packs installed on the system.
    """
    try:
        import pytesseract
        
        langs = pytesseract.get_languages()
        return OcrLanguagesResponse(
            languages=sorted(langs),
            default="eng" if "eng" in langs else (langs[0] if langs else "auto"),
            service_available=OCR_SERVICE_AVAILABLE,
        )
    
    except ImportError:
        return OcrLanguagesResponse(
            languages=["eng"],
            default="eng",
            service_available=OCR_SERVICE_AVAILABLE,
        )
    except Exception as e:
        logger.error(f"Failed to list OCR languages: {e}")
        return OcrLanguagesResponse(
            languages=["eng", "tur", "deu", "fra", "spa"],
            default="eng",
            service_available=OCR_SERVICE_AVAILABLE,
        )


@router.post("/api/ocr/batch", response_model=list[OcrExtractResponse])
async def batch_extract_text(
    files: list[UploadFile] = File(..., description="Multiple image or PDF files"),
    language: str = Form(default="eng", description="OCR language code"),
    extract_tables: bool = Form(default=False, description="Extract tables from PDFs"),
    user: dict = Depends(get_current_user),
):
    """Extract text from multiple files in a single request.
    
    Processes up to 10 files at once. Each file is processed independently.
    """
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per batch")
    
    results = []
    
    for file in files:
        try:
            if not file.filename:
                results.append(OcrExtractResponse(
                    success=False,
                    error="Filename is required"
                ))
                continue
            
            content = await file.read()
            content_type = file.content_type or ""
            
            try:
                file_type = _validate_file(file.filename, content_type, content)
            except HTTPException as e:
                results.append(OcrExtractResponse(
                    success=False,
                    filename=file.filename or "",
                    error=e.detail
                ))
                continue
            
            # Process file
            ext = Path(file.filename).suffix.lower()
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)
            
            try:
                # Use OCR service if available
                if OCR_SERVICE_AVAILABLE and svc_extract_image and svc_extract_pdf:
                    if file_type == "image":
                        result = await svc_extract_image(str(tmp_path), language=language)
                        page_count = 1
                        tables = None
                    else:
                        result = await svc_extract_pdf(
                            str(tmp_path),
                            extract_tables=extract_tables,
                        )
                        page_count = result.get("pages_extracted", 0)
                        tables = result.get("tables") if extract_tables else None
                    
                    text = result.get("text", "")
                    word_count = result.get("word_count", len(text.split()))
                    confidence = result.get("confidence")
                    error = result.get("error")
                else:
                    # Fallback
                    if file_type == "image":
                        result = _fallback_extract_image(tmp_path, language)
                        page_count = 1
                        tables = None
                    else:
                        result = _fallback_extract_pdf(tmp_path, language)
                        page_count = result.get("page_count", 0)
                        tables = None
                    
                    text = result.get("text", "")
                    word_count = result.get("word_count", len(text.split()))
                    confidence = result.get("confidence")
                    error = result.get("error")
                
                # Truncate
                if len(text) > MAX_EXTRACTED_CHARS:
                    text = text[:MAX_EXTRACTED_CHARS]
                
                results.append(OcrExtractResponse(
                    success=error is None,
                    text=text,
                    char_count=len(text),
                    word_count=word_count,
                    page_count=page_count,
                    file_type=file_type,
                    filename=file.filename,
                    language=language,
                    confidence=confidence,
                    tables=tables,
                    error=error
                ))
            finally:
                tmp_path.unlink(missing_ok=True)
        
        except Exception as e:
            results.append(OcrExtractResponse(
                success=False,
                filename=file.filename or "",
                error=str(e)
            ))
    
    _audit("ocr_batch", user["user_id"], detail=f"{len(files)} files")
    
    return results