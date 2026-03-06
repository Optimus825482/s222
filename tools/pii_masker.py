"""
PII Auto-Masker — detects and masks personal data in agent outputs.

Supports Turkish and English PII patterns:
- Email addresses
- Phone numbers (TR/US/international)
- Turkish TC Kimlik numbers (11-digit)
- Credit card numbers
- IBAN numbers
- IP addresses
- Turkish plate numbers

Usage:
    from tools.pii_masker import mask_pii, detect_pii

    masked = mask_pii("Beni 05551234567 numaradan arayın")
    # → "Beni [TELEFON] numaradan arayın"

    findings = detect_pii("Email: test@example.com, TC: 12345678901")
    # → [{"type": "email", "value": "test@example.com", ...}, ...]
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class PIIMatch:
    """A detected PII occurrence."""
    pii_type: str
    original: str
    masked: str
    start: int
    end: int


# ── Pattern Definitions ──────────────────────────────────────────

_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    # Email
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "[E-POSTA]",
    ),
    # Turkish phone: 05xx xxx xx xx (various formats)
    (
        "phone_tr",
        re.compile(r"\b0?5\d{2}[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}\b"),
        "[TELEFON]",
    ),
    # International phone: +90 5xx ...
    (
        "phone_intl",
        re.compile(r"\+\d{1,3}[\s.-]?\d{3,4}[\s.-]?\d{3,4}[\s.-]?\d{2,4}\b"),
        "[TELEFON]",
    ),
    # Turkish TC Kimlik (11 digits, starts with non-zero)
    (
        "tc_kimlik",
        re.compile(r"\b[1-9]\d{10}\b"),
        "[TC_KIMLIK]",
    ),
    # Credit card (16 digits, various formats)
    (
        "credit_card",
        re.compile(r"\b\d{4}[\s.-]?\d{4}[\s.-]?\d{4}[\s.-]?\d{4}\b"),
        "[KREDI_KARTI]",
    ),
    # IBAN (TR or international)
    (
        "iban",
        re.compile(r"\b[A-Z]{2}\d{2}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{2,4}\b"),
        "[IBAN]",
    ),
    # IPv4 address
    (
        "ip_address",
        re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"),
        "[IP_ADRESI]",
    ),
    # Turkish plate number (34 ABC 1234)
    (
        "plate_tr",
        re.compile(r"\b\d{2}\s?[A-Z]{1,3}\s?\d{2,4}\b"),
        "[PLAKA]",
    ),
]

# Context keywords that increase confidence of TC Kimlik detection
_TC_CONTEXT = re.compile(
    r"(tc|kimlik|t\.?c\.?|vatandaş|nüfus|identity|citizen)",
    re.IGNORECASE,
)


# ── Core Functions ───────────────────────────────────────────────

def detect_pii(text: str) -> list[dict[str, Any]]:
    """
    Detect PII in text. Returns list of findings with type, value, position.
    """
    findings: list[dict[str, Any]] = []

    for pii_type, pattern, mask_label in _PATTERNS:
        for match in pattern.finditer(text):
            value = match.group()

            # TC Kimlik: reduce false positives — require context keyword nearby
            if pii_type == "tc_kimlik":
                context_window = text[max(0, match.start() - 50):match.end() + 50]
                if not _TC_CONTEXT.search(context_window):
                    continue

            findings.append({
                "type": pii_type,
                "value": value,
                "masked": mask_label,
                "start": match.start(),
                "end": match.end(),
            })

    # Sort by position (reverse for safe replacement)
    findings.sort(key=lambda f: f["start"])
    return findings


def mask_pii(text: str) -> str:
    """
    Mask all detected PII in text. Returns masked version.
    """
    findings = detect_pii(text)
    if not findings:
        return text

    # Replace from end to start to preserve positions
    result = text
    for finding in reversed(findings):
        result = (
            result[:finding["start"]]
            + finding["masked"]
            + result[finding["end"]:]
        )
    return result


def mask_pii_in_response(response: str, enabled: bool = True) -> str:
    """
    Mask PII in an agent response. No-op if disabled.
    Returns the (possibly masked) response.
    """
    if not enabled:
        return response
    return mask_pii(response)


def pii_stats(text: str) -> dict[str, Any]:
    """
    Get PII detection statistics for a text.
    """
    findings = detect_pii(text)
    type_counts: dict[str, int] = {}
    for f in findings:
        type_counts[f["type"]] = type_counts.get(f["type"], 0) + 1

    return {
        "total_pii_found": len(findings),
        "types": type_counts,
        "has_pii": len(findings) > 0,
    }
