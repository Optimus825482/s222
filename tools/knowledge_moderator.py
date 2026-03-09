"""
Knowledge Base Moderator — Prevents low-quality solutions from persisting.

Rules:
1. Confidence >= 0.85 required
2. At least 2 independent agent validations
3. Human approval queue via API (POST /api/moderate/solution)
4. Auto-reject if contradicts existing high-confidence knowledge

Usage:
    from tools.knowledge_moderator import moderator

    # Submit a solution for moderation
    result = await moderator.submit(
        solution="Use connection pooling for PG",
        confidence=0.92,
        source_agents=["researcher", "reasoner"],
        context={"task_type": "performance"},
    )
    # result.status: "approved" | "pending_review" | "rejected"
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("knowledge_moderator")


class ModerationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_HUMAN = "needs_human_review"


class ModerationResult(BaseModel):
    status: ModerationStatus
    solution_id: str = ""
    confidence: float = 0.0
    reason: str = ""
    validating_agents: list[str] = Field(default_factory=list)


class KnowledgeModerator:
    """
    Gates knowledge base writes with confidence + multi-agent validation.
    Solutions below threshold go to human review queue.
    """

    MIN_CONFIDENCE = 0.85
    MIN_VALIDATING_AGENTS = 2
    VALID_AGENT_ROLES = {"researcher", "reasoner", "thinker", "critic", "orchestrator", "speed"}

    def __init__(self):
        self._initialized = False

    def _get_conn(self):
        from tools.pg_connection import get_conn
        return get_conn()

    def _release(self, conn):
        from tools.pg_connection import release_conn
        release_conn(conn)

    def _ensure_table(self):
        if self._initialized:
            return
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_moderation_queue (
                        id SERIAL PRIMARY KEY,
                        solution_text TEXT NOT NULL,
                        confidence REAL NOT NULL DEFAULT 0,
                        source_agents TEXT[] DEFAULT '{}',
                        context JSONB DEFAULT '{}',
                        status VARCHAR(32) NOT NULL DEFAULT 'pending',
                        reviewer VARCHAR(64),
                        review_note TEXT DEFAULT '',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        reviewed_at TIMESTAMPTZ
                    )
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_kmod_status
                    ON knowledge_moderation_queue(status)
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS validated_knowledge (
                        id SERIAL PRIMARY KEY,
                        solution_text TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        source_agents TEXT[] DEFAULT '{}',
                        context JSONB DEFAULT '{}',
                        validation_count INTEGER DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
            conn.commit()
            self._release(conn)
            self._initialized = True
        except Exception as e:
            logger.warning(f"Knowledge moderation table init failed: {e}")

    async def submit(
        self,
        solution: str,
        confidence: float,
        source_agents: list[str],
        context: dict[str, Any] | None = None,
    ) -> ModerationResult:
        """
        Submit a solution for moderation.
        Auto-approves if confidence >= 0.85 AND >= 2 independent agent validations.
        Otherwise queues for human review.
        """
        self._ensure_table()
        ctx = context or {}

        # Validate agent roles
        valid_agents = [a for a in source_agents if a in self.VALID_AGENT_ROLES]
        unique_agents = list(set(valid_agents))

        # Check for contradiction with existing knowledge
        contradiction = await self._check_contradiction(solution)
        if contradiction:
            return ModerationResult(
                status=ModerationStatus.REJECTED,
                confidence=confidence,
                reason=f"Contradicts existing knowledge: {contradiction}",
                validating_agents=unique_agents,
            )

        # Auto-approve path
        if confidence >= self.MIN_CONFIDENCE and len(unique_agents) >= self.MIN_VALIDATING_AGENTS:
            solution_id = self._store_validated(solution, confidence, unique_agents, ctx)
            return ModerationResult(
                status=ModerationStatus.APPROVED,
                solution_id=str(solution_id),
                confidence=confidence,
                reason="Auto-approved: high confidence + multi-agent validation",
                validating_agents=unique_agents,
            )

        # Queue for human review
        queue_id = self._queue_for_review(solution, confidence, unique_agents, ctx)
        reason_parts = []
        if confidence < self.MIN_CONFIDENCE:
            reason_parts.append(f"confidence {confidence:.2f} < {self.MIN_CONFIDENCE}")
        if len(unique_agents) < self.MIN_VALIDATING_AGENTS:
            reason_parts.append(f"only {len(unique_agents)} agent(s), need {self.MIN_VALIDATING_AGENTS}")
        return ModerationResult(
            status=ModerationStatus.NEEDS_HUMAN,
            solution_id=str(queue_id),
            confidence=confidence,
            reason="Queued: " + ", ".join(reason_parts),
            validating_agents=unique_agents,
        )

    async def _check_contradiction(self, solution: str) -> str | None:
        """Check if solution contradicts existing validated knowledge."""
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT solution_text FROM validated_knowledge ORDER BY created_at DESC LIMIT 50"
                )
                rows = cur.fetchall()
            self._release(conn)

            solution_lower = solution.lower()
            negation_pairs = [
                ("always", "never"), ("enable", "disable"),
                ("increase", "decrease"), ("add", "remove"),
                ("use", "avoid"), ("should", "should not"),
            ]
            for row in rows:
                existing = row[0].lower()
                for pos, neg in negation_pairs:
                    if pos in solution_lower and neg in existing and _text_overlap(solution_lower, existing) > 0.4:
                        return row[0][:100]
                    if neg in solution_lower and pos in existing and _text_overlap(solution_lower, existing) > 0.4:
                        return row[0][:100]
            return None
        except Exception as e:
            logger.debug(f"Contradiction check failed: {e}")
            return None

    def _store_validated(
        self, solution: str, confidence: float, agents: list[str], ctx: dict
    ) -> int:
        """Store auto-approved solution in validated_knowledge."""
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO validated_knowledge
                       (solution_text, confidence, source_agents, context, validation_count)
                       VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                    (solution, confidence, agents, json.dumps(ctx), len(agents)),
                )
                row = cur.fetchone()
                kid = row[0] if row else 0
            conn.commit()
            self._release(conn)
            return kid
        except Exception as e:
            logger.warning(f"Failed to store validated knowledge: {e}")
            return 0

    def _queue_for_review(
        self, solution: str, confidence: float, agents: list[str], ctx: dict
    ) -> int:
        """Queue solution for human review."""
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO knowledge_moderation_queue
                       (solution_text, confidence, source_agents, context, status)
                       VALUES (%s, %s, %s, %s, 'pending') RETURNING id""",
                    (solution, confidence, agents, json.dumps(ctx)),
                )
                row = cur.fetchone()
                qid = row[0] if row else 0
            conn.commit()
            self._release(conn)
            return qid
        except Exception as e:
            logger.warning(f"Failed to queue for review: {e}")
            return 0

    def review(self, queue_id: int, approved: bool, reviewer: str = "human", note: str = "") -> bool:
        """Human reviews a queued solution. If approved, moves to validated_knowledge."""
        self._ensure_table()
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT solution_text, confidence, source_agents, context FROM knowledge_moderation_queue WHERE id = %s AND status = 'pending'",
                    (queue_id,),
                )
                row = cur.fetchone()
                if not row:
                    self._release(conn)
                    return False

                new_status = "approved" if approved else "rejected"
                cur.execute(
                    """UPDATE knowledge_moderation_queue
                       SET status = %s, reviewer = %s, review_note = %s, reviewed_at = NOW()
                       WHERE id = %s""",
                    (new_status, reviewer, note, queue_id),
                )

                if approved:
                    cur.execute(
                        """INSERT INTO validated_knowledge
                           (solution_text, confidence, source_agents, context, validation_count)
                           VALUES (%s, %s, %s, %s, 1)""",
                        (row[0], row[1], row[2], row[3]),
                    )
            conn.commit()
            self._release(conn)
            return True
        except Exception as e:
            logger.warning(f"Review failed: {e}")
            return False

    def get_pending_queue(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get pending solutions awaiting human review."""
        self._ensure_table()
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, solution_text, confidence, source_agents, context, created_at
                       FROM knowledge_moderation_queue
                       WHERE status = 'pending'
                       ORDER BY created_at DESC LIMIT %s""",
                    (limit,),
                )
                rows = cur.fetchall()
            self._release(conn)
            return [
                {
                    "id": r[0], "solution": r[1], "confidence": r[2],
                    "agents": r[3], "context": r[4], "created_at": str(r[5]),
                }
                for r in rows
            ]
        except Exception as e:
            logger.warning(f"Failed to get pending queue: {e}")
            return []


def _text_overlap(a: str, b: str) -> float:
    """Simple word overlap ratio between two texts."""
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    return len(intersection) / min(len(words_a), len(words_b))


# ── Singleton ────────────────────────────────────────────────────

_moderator: KnowledgeModerator | None = None


def get_moderator() -> KnowledgeModerator:
    global _moderator
    if _moderator is None:
        _moderator = KnowledgeModerator()
    return _moderator


moderator = get_moderator()
