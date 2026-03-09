"""
Adaptive Tool Selection Engine for multi-agent system.

Analyzes agent performance, usage patterns, and task context to recommend
the optimal tool/agent combination for each query. Combines:
- Usage Pattern Analysis (which tools work best for which tasks)
- Performance Scoring (agent success rates)
- Contextual Knowledge (task type matching)
- User Behavior Learning (preferences from teachings)
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ── User Behavior Learning ────────────────────────────────────────
# Pattern detection for user preferences


class UsagePatternAnalyzer:
    """Analyzes tool/agent usage patterns from execution history."""

    def __init__(self):
        self.tool_usage: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.task_type_patterns: dict[str, list[str]] = defaultdict(list)
        self.success_by_tool: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.total_by_tool: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def record_usage(self, agent_role: str, tool_name: str, success: bool, task_context: str) -> None:
        """Record a tool usage event."""
        self.tool_usage[agent_role][tool_name] += 1
        self.total_by_tool[agent_role][tool_name] += 1
        if success:
            self.success_by_tool[agent_role][tool_name] += 1

        # Learn task context patterns
        task_type = self._categorize_task(task_context)
        if tool_name not in self.task_type_patterns[task_type]:
            self.task_type_patterns[task_type].append(tool_name)

    def _categorize_task(self, context: str) -> str:
        """Categorize a task based on its content."""
        context_lower = context.lower()

        if any(w in context_lower for w in ["araştır", "search", "find", "online", "web"]):
            return "research"
        elif any(w in context_lower for w in ["analiz", "analyze", "review", "evaluate"]):
            return "analysis"
        elif any(w in context_lower for w in ["kod", "code", "program", "script"]):
            return "coding"
        elif any(w in context_lower for w in ["hesapla", "calculate", "math", "number"]):
            return "calculation"
        elif any(w in context_lower for w in ["özetle", "summarize", "short", "quick"]):
            return "summarization"
        else:
            return "general"

    def get_top_tools_for_agent(self, agent_role: str, limit: int = 5) -> list[dict[str, Any]]:
        """Get tools ranked by success rate for a specific agent."""
        tool_scores = []
        for tool, total in self.total_by_tool[agent_role].items():
            success = self.success_by_tool[agent_role].get(tool, 0)
            rate = success / total if total > 0 else 0
            tool_scores.append({
                "tool": tool,
                "count": total,
                "success": success,
                "success_rate": round(rate * 100, 1),
            })
        tool_scores.sort(key=lambda x: x["success_rate"], reverse=True)
        return tool_scores[:limit]

    def get_tools_for_task_type(self, task_type: str) -> list[str]:
        """Get tools commonly used for a task type."""
        return self.task_type_patterns.get(task_type, [])

    def get_usage_matrix(self) -> dict[str, Any]:
        """Get full usage matrix for all agents."""
        matrix = {}
        for agent, tools in self.total_by_tool.items():
            matrix[agent] = {
                "total_calls": sum(tools.values()),
                "top_tools": self.get_top_tools_for_agent(agent, 3),
                "tool_diversity": len(tools),
            }
        return matrix


class ContextualToolScorer:
    """Scores tools based on task context and requirements."""

    def __init__(self):
        # Tool capabilities mapping
        self.tool_capabilities = {
            "web_search": ["research", "factual", "current-info"],
            "web_fetch": ["detailed", "article", "content-extraction"],
            "code_execute": ["coding", "testing", "automation"],
            "rag_query": ["knowledge-base", "documentation", "reference"],
            "save_memory": ["learning", "preference", "long-term"],
            "recall_memory": ["context", "history", "background"],
            "forecast": ["prediction", "trend", "forecasting"],
            "analytics_compute": ["stats", "data", "metrics"],
        }

    def score_tool(self, tool_name: str, task_context: str) -> float:
        """Score a tool for a specific task context (0-100)."""
        context_lower = task_context.lower()
        capabilities = self.tool_capabilities.get(tool_name, [])

        score = 50.0  # Base score

        # Capability matching
        for cap in capabilities:
            if any(word in context_lower for word in self._cap_to_words(cap)):
                score += 10

        # Special case matching
        if "image" in context_lower:
            if tool_name in ["code_execute", "rag_query"]:
                score += 5

        if any(w in context_lower for w in [" hız", "hızlı", "quick", "fast", "rapid"]):
            if tool_name in ["code_execute", "web_search"]:
                score += 15

        return min(100.0, score)

    def _cap_to_words(self, cap: str) -> list[str]:
        """Convert capability string to search words."""
        return cap.replace("-", " ").split()

    def get_best_tools(self, task_context: str, limit: int = 5) -> list[dict[str, Any]]:
        """Get top-scoring tools for a task."""
        all_tools = list(self.tool_capabilities.keys())
        scored = [(t, self.score_tool(t, task_context)) for t in all_tools]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [{"tool": t, "score": round(s, 1)} for t, s in scored[:limit]]


class PerformanceAwareSelector:
    """Selects tools/agents based on historical performance data."""

    def __init__(self):
        self.agent_performance: dict[str, dict[str, Any]] = {}
        self._load_agent_baselines()

    def _load_agent_baselines(self) -> None:
        """Load agent performance from PostgreSQL evaluations table."""
        try:
            from tools.pg_connection import get_conn, release_conn
            conn = get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT agent_role,
                               COUNT(*) as total,
                               AVG(score) as avg_score,
                               AVG(latency_ms) as avg_latency
                        FROM evaluations
                        GROUP BY agent_role
                    """)
                    rows = cur.fetchall()
                    for row in rows:
                        self.agent_performance[row["agent_role"]] = {
                            "total_tasks": row["total"],
                            "avg_score": float(row["avg_score"] or 0),
                            "avg_latency_ms": float(row["avg_latency"] or 0),
                        }
            finally:
                release_conn(conn)
        except Exception as e:
            logger.warning("Failed to load agent baselines: %s", e)



    def get_agent_score(self, agent_role: str, task_complexity: str = "medium") -> float:
        """Get overall score for an agent (0-100)."""
        perf = self.agent_performance.get(agent_role, {})
        base_score = perf.get("avg_score", 2.5) * 20  # Convert 0-5 to 0-100

        # Complexity bonus
        if task_complexity == "simple":
            base_score -= 5
        elif task_complexity == "complex":
            base_score += 5

        return max(0, min(100, base_score))

    def select_agent_for_task(self, task_context: str, required_skills: list[str] | None = None) -> str:
        """Select the best agent for a task context."""
        # Score each agent
        scores = {}
        for agent in ["thinker", "reasoner", "speed", "researcher", "critic"]:
            scores[agent] = self.get_agent_score(agent)

        # Adjust based on task type
        context_lower = task_context.lower()

        if any(w in context_lower for w in ["araştır", "research", "find", "scan"]):
            scores["researcher"] += 15
        if any(w in context_lower for w in ["analiz", "analyze", "evaluate", "deep"]):
            scores["thinker"] += 15
        if any(w in context_lower for w in ["hızlı", "quick", "fast", "simple"]):
            scores["speed"] += 15
        if any(w in context_lower for w in ["doğrula", "verify", "logic", "math"]):
            scores["reasoner"] += 15

        best = max(scores.items(), key=lambda x: x[1])
        return best[0]


class UserBehaviorLearner:
    """ Learns user preferences from teaching interactions."""

    def __init__(self):
        self.usage_history: list[dict[str, Any]] = []
        self.preferences: dict[str, Any] = {}

    def record_task(self, input_text: str, tool_used: str, agent_used: str,
                   success: bool, user_feedback: str | None = None) -> None:
        """Record a task completion."""
        self.usage_history.append({
            "input": input_text[:100],
            "tool": tool_used,
            "agent": agent_used,
            "success": success,
            "feedback": user_feedback,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Learn from success/failure
        if success:
            self._learn_preference(input_text, tool_used, agent_used)
        elif user_feedback:
            self._learn_from_negative(input_text, user_feedback)

    def _learn_preference(self, input_text: str, tool: str, agent: str) -> None:
        """Learn successful patterns."""
        # Store pattern for future matching
        keywords = self._extract_keywords(input_text)
        for kw in keywords:
            pattern_key = f"task:{kw}"
            if pattern_key not in self.preferences:
                self.preferences[pattern_key] = {"tools": [], "agents": []}
            if tool not in self.preferences[pattern_key]["tools"]:
                self.preferences[pattern_key]["tools"].append(tool)
            if agent not in self.preferences[pattern_key]["agents"]:
                self.preferences[pattern_key]["agents"].append(agent)

    def _learn_from_negative(self, input_text: str, feedback: str) -> None:
        """Learn from negative feedback."""
        if "hızlı" in feedback or "slow" in feedback.lower():
            self.preferences["avoid_slow_tools"] = True
        if "yanlış" in feedback or "wrong" in feedback.lower():
            self.preferences["needs_verification"] = True

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract important keywords from text."""
        # Simple keyword extraction - in production, use TF-IDF or similar
        words = re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]+", text.lower())
        # Filter common words
        stop_words = {"the", "and", "or", "for", "with", "about", "into", "like"}
        return [w for w in words if len(w) > 3 and w not in stop_words]

    def get_suggested_tool(self, input_text: str) -> str | None:
        """Get a suggested tool based on learned preferences."""
        keywords = self._extract_keywords(input_text)
        for kw in keywords:
            pattern_key = f"task:{kw}"
            if pattern_key in self.preferences:
                tools = self.preferences[pattern_key]["tools"]
                if tools:
                    return tools[0]  # Return most successful tool for this pattern
        return None

    def get_preferences(self) -> dict[str, Any]:
        """Get all learned preferences."""
        return self.preferences


# ── Main Selector Engine ──────────────────────────────────────────

class AdaptiveToolSelector:
    """Main engine that combines all selectors."""

    def __init__(self):
        self.pattern_analyzer = UsagePatternAnalyzer()
        self.context_scorer = ContextualToolScorer()
        self.performance_selector = PerformanceAwareSelector()
        self.user_behavior = UserBehaviorLearner()
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the selector with baseline data."""
        if self._initialized:
            return
        self._initialized = True
        logger.info("AdaptiveToolSelector initialized")

    def analyze_task(self, task_input: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Analyze a task and return tool/agent recommendations."""
        self.initialize()

        # Get scores from each component
        context_scores = self.context_scorer.get_best_tools(task_input, 5)
        user_suggestion = self.user_behavior.get_suggested_tool(task_input)

        # Build recommendation
        recommendation = {
            "input_summary": task_input[:50],
            "context_analysis": {
                "primary_type": self.pattern_analyzer._categorize_task(task_input),
                "key_requirements": self._extract_requirements(task_input),
            },
            "context_scores": context_scores,
            "user_suggestion": user_suggestion,
            "suggested_agent": self.performance_selector.select_agent_for_task(task_input),
            "confidence": self._calculate_confidence(context_scores, user_suggestion),
        }

        return recommendation

    def _extract_requirements(self, text: str) -> list[str]:
        """Extract task requirements from text."""
        requirements = []
        text_lower = text.lower()

        if any(w in text_lower for w in ["faktör", "factor", "statistic"]):
            requirements.append("factual-accuracy")
        if any(w in text_lower for w in ["deep", "detailed", "comprehensive"]):
            requirements.append("deep-analysis")
        if any(w in text_lower for w in ["hız", "quick", "fast"]):
            requirements.append("speed-priority")
        if any(w in text_lower for w in ["kod", "code", "program"]):
            requirements.append("coding-capability")

        return requirements

    def _calculate_confidence(self, context_scores: list, user_suggestion: str | None) -> float:
        """Calculate confidence score for recommendation."""
        if not context_scores:
            return 50.0

        top_score = context_scores[0].get("score", 50)

        # Boost if user behavior matches
        if user_suggestion and user_suggestion == context_scores[0].get("tool"):
            top_score += 20

        return min(100.0, top_score)

    def record_success(self, agent_role: str, tool_name: str,
                       task_input: str, context: dict[str, Any] | None = None) -> None:
        """Record a successful tool usage for learning."""
        self.pattern_analyzer.record_usage(agent_role, tool_name, True, task_input)
        self.user_behavior.record_task(task_input, tool_name, agent_role, True)

    def record_failure(self, agent_role: str, tool_name: str,
                       task_input: str, feedback: str, context: dict[str, Any] | None = None) -> None:
        """Record a failed tool usage for learning."""
        self.pattern_analyzer.record_usage(agent_role, tool_name, False, task_input)
        self.user_behavior.record_task(task_input, tool_name, agent_role, False, feedback)

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about learned patterns."""
        return {
            "pattern_matrix": self.pattern_analyzer.get_usage_matrix(),
            "learned_preferences": self.user_behavior.get_preferences(),
            "context_categories": list(self.pattern_analyzer.task_type_patterns.keys()),
        }


# ── Module-level Singleton ────────────────────────────────────────

_selector: AdaptiveToolSelector | None = None


def get_adaptive_tool_selector() -> AdaptiveToolSelector:
    """Get the global AdaptiveToolSelector singleton."""
    global _selector
    if _selector is None:
        _selector = AdaptiveToolSelector()
    return _selector
