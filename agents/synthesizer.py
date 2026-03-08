"""
Synthesizer Agent — merges multi-agent outputs into a unified response.
Uses confidence scoring to weight contributions and resolve contradictions.
Runs on the Speed model (Step 3.5 Flash) for fast synthesis.
"""

from __future__ import annotations

from agents.base import BaseAgent
from core.models import AgentRole, EventType, Thread
from tools.confidence import (
    detect_contradictions,
    score_confidence,
    weighted_synthesis_scores,
)


class SynthesizerAgent(BaseAgent):
    """
    Merges outputs from multiple specialist agents into a single
    coherent response, weighted by confidence scores.
    """

    role = AgentRole.SPEED
    model_key = "speed"

    def system_prompt(self) -> str:
        return (
            "You are a Synthesis specialist. Your job is to merge insights from "
            "multiple AI agents into a single, coherent, high-quality response.\n\n"
            "SYNTHESIS RULES:\n"
            "1. Integrate insights from ALL agents, giving more weight to higher-confidence outputs.\n"
            "2. When agents contradict each other, explicitly acknowledge the disagreement "
            "and provide a balanced resolution with reasoning.\n"
            "3. Cite which agent provided which insight using [Agent: role] notation.\n"
            "4. Remove redundancy — don't repeat the same point from multiple agents.\n"
            "5. Produce a structured, actionable conclusion.\n"
            "6. Respond in the SAME LANGUAGE as the user's original question.\n"
            "7. If one agent clearly has higher expertise for the topic, weight it accordingly.\n"
            "8. Preserve important nuances and caveats from individual agents.\n"
            "9. Keep the response focused — synthesis should be shorter than the sum of inputs.\n"
            "10. Do NOT add a confidence analysis section — it will be provided separately.\n\n"
            "OUTPUT FORMAT:\n"
            "- Start with a direct answer / executive summary\n"
            "- Organize by topic, not by agent\n"
            "- Use clear headings and structure\n\n"
            "CRITICAL: NEVER fabricate information. Only synthesize what the agents provided. "
            "If all agents lack information on a point, say so honestly."
        )

    async def synthesize(
        self,
        agent_results: dict[str, str],
        user_input: str,
        thread: Thread,
        confidence_data: dict | None = None,
    ) -> tuple[str, str]:
        """
        Synthesize multiple agent outputs into a unified response.

        Args:
            agent_results: Mapping of agent_role -> raw output text.
            user_input: The original user query.
            thread: Current conversation thread.
            confidence_data: Pre-computed confidence data (optional).
                             If None, computed here.

        Returns:
            Tuple of (synthesized_response, confidence_footer).
        """
        # Step 1: Score confidence for each agent result
        conf_scores: dict[str, dict] = {}
        task_type = _detect_task_type_simple(user_input)

        for role, output in agent_results.items():
            if confidence_data and role in confidence_data:
                conf_scores[role] = confidence_data[role]
            else:
                conf_scores[role] = score_confidence(output, role, task_type)

        # Step 2: Detect contradictions across all outputs
        contradictions = detect_contradictions(agent_results)

        # Step 3: Calculate synthesis weights
        weights = weighted_synthesis_scores(conf_scores)

        # Step 4: Build the synthesis prompt
        synthesis_prompt = _build_synthesis_prompt(
            agent_results=agent_results,
            user_input=user_input,
            conf_scores=conf_scores,
            contradictions=contradictions,
            weights=weights,
        )

        # Step 5: Log synthesis event
        thread.add_event(
            event_type=EventType.SYNTHESIS,
            content=f"Synthesizing {len(agent_results)} agent outputs",
            agent_role=self.role,
            confidence_scores={r: c["confidence_score"] for r, c in conf_scores.items()},
            contradictions_found=len(contradictions),
            weights=weights,
        )

        # Step 6: Execute LLM synthesis
        result = await self.execute(synthesis_prompt, thread)

        # Step 7: Build confidence footer separately
        footer = _build_confidence_footer(conf_scores, contradictions, weights)

        # Step 8: Emit confidence analysis as separate extra field via live monitor
        if self._live_monitor:
            self._live_monitor.emit(
                "confidence_analysis",
                self.role.value,
                footer,
                confidence_data={
                    role: {
                        "score": s.get("confidence_score", 0),
                        "level": s.get("confidence_level", "unknown"),
                        "weight": weights.get(role, 0),
                    }
                    for role, s in conf_scores.items()
                },
                contradictions_count=len(contradictions),
            )

        # Return main text and confidence footer as separate values
        return result, footer


# ── Private helpers ──────────────────────────────────────────────

def _detect_task_type_simple(query: str) -> str:
    """Lightweight task type detection for confidence scoring."""
    q = query.lower()
    mapping = {
        "research": ["araştır", "research", "investigate", "analiz"],
        "coding": ["kod", "code", "implement", "function", "class"],
        "creative": ["yaz", "write", "essay", "article", "blog"],
        "comparison": ["karşılaştır", "compare", "vs", "fark"],
        "planning": ["planla", "plan", "strateji", "mimari"],
    }
    for task_type, keywords in mapping.items():
        if any(kw in q for kw in keywords):
            return task_type
    return "general"


def _build_synthesis_prompt(
    agent_results: dict[str, str],
    user_input: str,
    conf_scores: dict[str, dict],
    contradictions: list[dict],
    weights: dict[str, float],
) -> str:
    """Construct the prompt sent to the LLM for synthesis."""
    parts: list[str] = [
        f"## Original User Request\n{user_input}\n",
        "## Agent Outputs (with confidence weights)\n",
    ]

    for role, output in agent_results.items():
        score = conf_scores.get(role, {})
        conf_val = score.get("confidence_score", 0)
        conf_lvl = score.get("confidence_level", "unknown")
        weight = weights.get(role, 0)
        parts.append(
            f"### [{role.upper()}] "
            f"(confidence: {conf_val:.0%} {conf_lvl}, weight: {weight:.0%})\n"
            f"{output}\n"
        )

    if contradictions:
        parts.append("## Detected Contradictions\n")
        for c in contradictions:
            agents = " vs ".join(c["agents"])
            parts.append(
                f"- **{agents}** ({c['severity']}): {c['detail']}\n"
                f"  Shared topics: {', '.join(c['shared_topics'][:5])}\n"
            )

    parts.append(
        "\n## Your Task\n"
        "Synthesize the above agent outputs into a single, coherent response. "
        "Weight higher-confidence agents more heavily. "
        "Resolve any contradictions explicitly. "
        "Do NOT add a confidence analysis section at the end."
    )

    return "\n".join(parts)


def _build_confidence_footer(
    conf_scores: dict[str, dict],
    contradictions: list[dict],
    weights: dict[str, float],
) -> str:
    """Build a structured confidence analysis footer."""
    lines: list[str] = ["---", "📊 **Güven Analizi**\n"]

    # Per-agent confidence
    lines.append("| Agent | Güven | Seviye | Ağırlık |")
    lines.append("|-------|-------|--------|---------|")
    for role, score in conf_scores.items():
        conf = score.get("confidence_score", 0)
        level = score.get("confidence_level", "?")
        weight = weights.get(role, 0)
        level_tr = {
            "very_high": "🟢 Çok Yüksek",
            "high": "🟢 Yüksek",
            "medium": "🟡 Orta",
            "low": "🔴 Düşük",
        }.get(level, level)
        lines.append(f"| {role} | {conf:.0%} | {level_tr} | {weight:.0%} |")

    # Overall confidence
    if conf_scores:
        avg = sum(s["confidence_score"] for s in conf_scores.values()) / len(conf_scores)
        lines.append(f"\n**Genel Güven:** {avg:.0%}")

    # Contradictions summary
    if contradictions:
        lines.append(f"\n⚠️ **{len(contradictions)} çelişki tespit edildi** — sentezde çözümlendi.")
    else:
        lines.append("\n✅ Ajanlar arası çelişki tespit edilmedi.")

    # Sources aggregate
    all_sources: list[str] = []
    for score in conf_scores.values():
        all_sources.extend(score.get("sources_used", []))
    if all_sources:
        unique = sorted(set(all_sources))
        lines.append(f"\n📎 **Kaynaklar:** {len(unique)} benzersiz kaynak kullanıldı.")

    return "\n".join(lines)
