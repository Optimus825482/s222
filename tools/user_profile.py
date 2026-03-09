"""
User Profile & Personalization Engine

Learns from user behavior, preferences, and style to provide
personalized, proactive assistance.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from tools.pg_connection import get_conn, release_conn

logger = logging.getLogger(__name__)

# ── User Profile Management ───────────────────────────────────────

def get_or_create_user_profile(user_id: str) -> dict[str, Any]:
    """Get user profile or create if not exists."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT * FROM user_profiles WHERE user_id = %s""",
                (user_id,),
            )
            row = cur.fetchone()
            if row:
                return _row_to_profile(row)
            
            # Create new profile
            cur.execute(
                """INSERT INTO user_profiles (user_id, preferences, style_analysis, interaction_patterns)
                   VALUES (%s, %s, %s, %s)
                   RETURNING *""",
                (user_id, {}, {}, {}),
            )
            conn.commit()
            return _row_to_profile(cur.fetchone())
    finally:
        release_conn(conn)


def update_user_style(
    user_id: str,
    style_key: str,
    style_value: str | int | float | bool,
) -> None:
    """Update a specific style attribute for user."""
    profile = get_or_create_user_profile(user_id)
    style = profile.get("style_analysis", {})
    style[style_key] = style_value
    
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE user_profiles SET style_analysis = %s, updated_at = now()
                   WHERE user_id = %s""",
                (json.dumps(style), user_id),
            )
        conn.commit()
    finally:
        release_conn(conn)


def record_interaction_pattern(
    user_id: str,
    pattern_type: str,
    pattern_data: dict[str, Any],
) -> None:
    """Record and analyze interaction patterns."""
    profile = get_or_create_user_profile(user_id)
    patterns = profile.get("interaction_patterns", {})
    
    # Initialize or update pattern
    if pattern_type not in patterns:
        patterns[pattern_type] = {
            "count": 0,
            "examples": [],
            "last_occurrence": None,
        }
    
    patterns[pattern_type]["count"] += 1
    patterns[pattern_type]["last_occurrence"] = datetime.now(timezone.utc).isoformat()
    
    # Keep last 5 examples
    if len(patterns[pattern_type].get("examples", [])) >= 5:
        patterns[pattern_type]["examples"].pop(0)
    patterns[pattern_type]["examples"].append(pattern_data)
    
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE user_profiles SET interaction_patterns = %s, updated_at = now()
                   WHERE user_id = %s""",
                (json.dumps(patterns), user_id),
            )
        conn.commit()
    finally:
        release_conn(conn)


def set_user_preference(
    user_id: str,
    key: str,
    value: Any,
    category: str = "general",
) -> None:
    """Set a user preference."""
    profile = get_or_create_user_profile(user_id)
    prefs = profile.get("preferences", {})
    
    if category not in prefs:
        prefs[category] = {}
    prefs[category][key] = value
    
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE user_profiles SET preferences = %s, updated_at = now()
                   WHERE user_id = %s""",
                (json.dumps(prefs), user_id),
            )
        conn.commit()
    finally:
        release_conn(conn)


def get_user_preferences(user_id: str) -> dict[str, Any]:
    """Get all user preferences."""
    profile = get_or_create_user_profile(user_id)
    return profile.get("preferences", {})


# ── Style Analysis ────────────────────────────────────────────────

def analyze_communication_style(user_id: str, messages: list[str]) -> dict[str, Any]:
    """Analyze user's communication style from their messages."""
    style = {
        "formality": "neutral",  # formal, neutral, casual
        "verbosity": "moderate",  # brief, moderate, detailed
        "tone": "professional",  # professional, friendly, technical
        "preferred_language": "tr",
        "emoji_usage": "rare",
        "question_style": "direct",  # direct, exploratory, mixed
    }
    
    if not messages:
        return style
    
    total_words = 0
    questions = 0
    exclamations = 0
    technical_terms = 0
    emojis = 0
    
    technical_keywords = [
        "api", "kod", "code", "sistem", "system", "veritabanı", "database",
        "algoritma", "algorithm", "optimize", "deployment", "server",
    ]
    
    for msg in messages:
        words = msg.split()
        total_words += len(words)
        questions += msg.count("?")
        exclamations += msg.count("!")
        emojis += sum(1 for c in msg if ord(c) > 0x1F000)
        technical_terms += sum(1 for kw in technical_keywords if kw.lower() in msg.lower())
    
    avg_words = total_words / len(messages) if messages else 0
    
    # Determine style
    if avg_words < 15:
        style["verbosity"] = "brief"
    elif avg_words > 50:
        style["verbosity"] = "detailed"
    
    if questions > len(messages) * 0.5:
        style["question_style"] = "exploratory"
    
    if technical_terms > len(messages) * 0.3:
        style["tone"] = "technical"
    
    if emojis > len(messages) * 0.2:
        style["emoji_usage"] = "frequent"
    
    # Save analysis
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE user_profiles SET style_analysis = %s, updated_at = now()
                   WHERE user_id = %s""",
                (json.dumps(style), user_id),
            )
        conn.commit()
    finally:
        release_conn(conn)
    
    return style


# ── Context Generation for Agents ─────────────────────────────────

def get_personalization_context(user_id: str) -> str:
    """Generate context string for agent system prompts."""
    profile = get_or_create_user_profile(user_id)
    prefs = profile.get("preferences", {})
    style = profile.get("style_analysis", {})
    patterns = profile.get("interaction_patterns", {})
    
    lines = ["### KULLANICI PROFİLİ ###"]
    
    # Style preferences
    if style:
        lines.append("\n**İletişim Tarzı:**")
        formality = style.get("formality", "neutral")
        verbosity = style.get("verbosity", "moderate")
        tone = style.get("tone", "professional")
        lines.append(f"- Formalite: {formality}")
        lines.append(f"- Detay seviyesi: {verbosity}")
        lines.append(f"- Ton: {tone}")
    
    # User preferences
    if prefs:
        lines.append("\n**Tercihler:**")
        for category, items in prefs.items():
            if isinstance(items, dict):
                for k, v in items.items():
                    lines.append(f"- [{category}] {k}: {v}")
    
    # Interaction patterns
    if patterns:
        lines.append("\n**Davranış Kalıpları:**")
        for pattern_type, data in patterns.items():
            count = data.get("count", 0)
            if count > 2:  # Only show patterns with 3+ occurrences
                lines.append(f"- {pattern_type}: {count} kez")
    
    lines.append("\n**Kişiselleştirme Kuralları:**")
    lines.append("- Kullanıcının tarzına uygun yanıt ver")
    lines.append("- Öğrendiğin tercihleri uygula")
    lines.append("- Proaktif öneriler sun")
    lines.append("- Her zaman destekleyici ve yardımcı ol")
    
    lines.append("\n### PROFİL SONU ###")
    
    return "\n".join(lines)


# ── Database Migration ───────────────────────────────────────────

def ensure_user_profiles_table() -> None:
    """Create user_profiles table if not exists."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) UNIQUE NOT NULL,
                    preferences JSONB DEFAULT '{}',
                    style_analysis JSONB DEFAULT '{}',
                    interaction_patterns JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
        conn.commit()
        logger.info("user_profiles table ensured")
    except Exception as e:
        logger.error(f"Failed to create user_profiles table: {e}")
    finally:
        release_conn(conn)


# ── Helper ───────────────────────────────────────────────────────

def _row_to_profile(row: Any) -> dict[str, Any]:
    if not row:
        return {}
    return {
        "id": row[0] if len(row) > 0 else None,
        "user_id": row[1] if len(row) > 1 else None,
        "preferences": row[2] if len(row) > 2 else {},
        "style_analysis": row[3] if len(row) > 3 else {},
        "interaction_patterns": row[4] if len(row) > 4 else {},
        "created_at": str(row[5]) if len(row) > 5 else None,
        "updated_at": str(row[6]) if len(row) > 6 else None,
    }