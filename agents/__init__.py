# Agents module - Orchestrator + Specialist agents
from agents.synthesizer import SynthesizerAgent
from agents.critic import CriticAgent

__all__ = ["SynthesizerAgent", "CriticAgent", "create_agent"]

_AGENT_REGISTRY: dict[str, type] = {}


def _ensure_registry() -> None:
    """Lazy-load all agent classes into the registry."""
    if _AGENT_REGISTRY:
        return
    from agents.orchestrator import OrchestratorAgent
    from agents.thinker import ThinkerAgent
    from agents.speed import SpeedAgent
    from agents.researcher import ResearcherAgent
    from agents.reasoner import ReasonerAgent

    for cls in [
        OrchestratorAgent,
        ThinkerAgent,
        SpeedAgent,
        ResearcherAgent,
        ReasonerAgent,
        CriticAgent,
        SynthesizerAgent,
    ]:
        _AGENT_REGISTRY[cls.role.value if hasattr(cls.role, "value") else str(cls.role)] = cls


def create_agent(role: str):
    """Factory: create an agent instance by role name string."""
    _ensure_registry()
    cls = _AGENT_REGISTRY.get(role)
    if cls is None:
        raise ValueError(f"Unknown agent role: {role}. Available: {list(_AGENT_REGISTRY.keys())}")
    return cls()
