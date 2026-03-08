"""
Agent Social Network — peer learning, swarm voting, discussions.
In-memory store; can be backed by PostgreSQL later.
Aligned with powers/autonomous-agent-ecosystem/steering/agent-social-network.md
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

_utc = timezone.utc


@dataclass
class Community:
    id: str
    name: str
    type: str  # general, topic, project
    description: str
    members: list[str]
    created_at: str = field(default_factory=lambda: datetime.now(_utc).isoformat())


@dataclass
class Discussion:
    id: str
    community_id: str
    topic: str
    messages: list[dict] = field(default_factory=list)
    started_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(_utc).isoformat())
    is_active: bool = True


@dataclass
class SwarmProposal:
    id: str
    proposer: str
    title: str
    description: str
    votes: dict[str, str] = field(default_factory=dict)  # role -> agree | disagree | abstain
    status: str = "open"  # open, passed, rejected, needs_human (Faz 12.2)
    resolution_reason: str | None = None  # reason from policy or human
    created_at: str = field(default_factory=lambda: datetime.now(_utc).isoformat())


@dataclass
class PeerLearning:
    id: str
    teacher: str
    pattern: str
    community_id: str = "general"
    adopted_by: list[str] = field(default_factory=list)
    rejected_by: list[str] = field(default_factory=list)
    confidence: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(_utc).isoformat())


class AgentSocialNetwork:
    def __init__(self):
        self.communities: dict[str, Community] = {}
        self.discussions: dict[str, Discussion] = {}
        self.proposals: dict[str, SwarmProposal] = {}
        self.learnings: list[PeerLearning] = []
        self._init_default_communities()

    def _init_default_communities(self) -> None:
        defaults = [
            Community(
                id="general",
                name="Genel",
                type="general",
                description="Tüm ajanlar — serbest tartışma",
                members=["orchestrator", "thinker", "speed", "researcher", "reasoner", "critic"],
            ),
            Community(
                id="code-patterns",
                name="Kod Kalıpları",
                type="topic",
                description="Kod kalıpları ve en iyi uygulamalar",
                members=["thinker", "speed", "reasoner"],
            ),
            Community(
                id="research-hub",
                name="Araştırma Merkezi",
                type="topic",
                description="Araştırma bulguları ve veri analizi",
                members=["researcher", "reasoner", "thinker"],
            ),
        ]
        for c in defaults:
            self.communities[c.id] = c

    def list_communities(self) -> list[dict[str, Any]]:
        return [
            {
                "id": c.id,
                "name": c.name,
                "type": c.type,
                "description": c.description,
                "members": c.members,
                "created_at": c.created_at,
            }
            for c in self.communities.values()
        ]

    def start_discussion(
        self,
        community_id: str,
        topic: str,
        starter: str,
        initial_message: str,
    ) -> dict[str, Any]:
        if community_id not in self.communities:
            raise ValueError(f"Community {community_id} not found")
        disc_id = f"disc-{uuid.uuid4().hex[:8]}"
        disc = Discussion(
            id=disc_id,
            community_id=community_id,
            topic=topic,
            started_by=starter,
            messages=[{
                "role": starter,
                "content": initial_message,
                "timestamp": datetime.now(_utc).isoformat(),
            }],
        )
        self.discussions[disc_id] = disc
        return {
            "id": disc.id,
            "community_id": disc.community_id,
            "topic": disc.topic,
            "started_by": disc.started_by,
            "messages": disc.messages,
            "created_at": disc.created_at,
            "message_count": len(disc.messages),
        }

    def post_message(self, discussion_id: str, agent_role: str, content: str) -> dict[str, Any]:
        disc = self.discussions.get(discussion_id)
        if not disc:
            raise ValueError(f"Discussion {discussion_id} not found")
        msg = {
            "role": agent_role,
            "content": content[:2000],
            "timestamp": datetime.now(_utc).isoformat(),
        }
        disc.messages.append(msg)
        return msg

    def list_discussions(self, community_id: str | None = None, limit: int = 20) -> list[dict]:
        discs = list(self.discussions.values())
        if community_id:
            discs = [d for d in discs if d.community_id == community_id]
        discs.sort(key=lambda d: d.created_at, reverse=True)
        out = []
        for d in discs[:limit]:
            out.append({
                "id": d.id,
                "community_id": d.community_id,
                "topic": d.topic,
                "started_by": d.started_by,
                "message_count": len(d.messages),
                "created_at": d.created_at,
            })
        return out

    def get_discussion(self, discussion_id: str) -> dict[str, Any] | None:
        disc = self.discussions.get(discussion_id)
        if not disc:
            return None
        return {
            "id": disc.id,
            "community_id": disc.community_id,
            "topic": disc.topic,
            "started_by": disc.started_by,
            "messages": disc.messages,
            "created_at": disc.created_at,
        }

    def create_proposal(self, proposer: str, title: str, description: str) -> dict[str, Any]:
        prop_id = f"prop-{uuid.uuid4().hex[:8]}"
        prop = SwarmProposal(
            id=prop_id,
            proposer=proposer,
            title=title,
            description=description,
        )
        self.proposals[prop_id] = prop
        if len(self.proposals) > 100:
            by_date = sorted(self.proposals.items(), key=lambda x: x[1].created_at)
            for k, _ in by_date[:20]:
                del self.proposals[k]
        return {
            "id": prop.id,
            "proposer": prop.proposer,
            "title": prop.title,
            "description": prop.description,
            "votes": prop.votes,
            "status": prop.status,
            "created_at": prop.created_at,
        }

    def vote(self, proposal_id: str, voter: str, vote: str) -> dict[str, Any]:
        if vote not in ("agree", "disagree", "abstain"):
            raise ValueError("vote must be agree, disagree, or abstain")
        prop = self.proposals.get(proposal_id)
        if not prop:
            raise ValueError("Proposal not found")
        if prop.status not in ("open", "needs_human"):
            return {
                "proposal_id": proposal_id,
                "status": prop.status,
                "votes": dict(prop.votes),
                "resolution_reason": getattr(prop, "resolution_reason", None),
            }
        prop.votes[voter] = vote
        if prop.status == "needs_human":
            return {
                "proposal_id": proposal_id,
                "status": prop.status,
                "votes": dict(prop.votes),
                "resolution_reason": getattr(prop, "resolution_reason", None),
            }
        agrees = sum(1 for v in prop.votes.values() if v == "agree")
        disagrees = sum(1 for v in prop.votes.values() if v == "disagree")
        abstains = sum(1 for v in prop.votes.values() if v == "abstain")
        from tools.collective_decision_policy import load_policy, compute_result
        policy = load_policy()
        status, reason = compute_result(agrees, disagrees, abstains, prop.proposer, policy)
        prop.status = status
        prop.resolution_reason = reason
        return {
            "proposal_id": proposal_id,
            "status": prop.status,
            "votes": dict(prop.votes),
            "resolution_reason": prop.resolution_reason,
        }

    def resolve_proposal(self, proposal_id: str, resolution: str, reason: str | None = None) -> dict[str, Any]:
        """Human escalation: resolve a proposal in needs_human status (Faz 12.2)."""
        if resolution not in ("passed", "rejected"):
            raise ValueError("resolution must be passed or rejected")
        prop = self.proposals.get(proposal_id)
        if not prop:
            raise ValueError("Proposal not found")
        if prop.status != "needs_human":
            raise ValueError(f"Proposal is not awaiting human resolution (status={prop.status})")
        prop.status = resolution
        prop.resolution_reason = reason or f"Human resolution: {resolution}"
        return {
            "proposal_id": proposal_id,
            "status": prop.status,
            "votes": dict(prop.votes),
            "resolution_reason": prop.resolution_reason,
        }

    def list_proposals(self, status: str | None = None, limit: int = 30) -> list[dict]:
        props = list(self.proposals.values())
        if status:
            props = [p for p in props if p.status == status]
        props.sort(key=lambda p: p.created_at, reverse=True)
        return [
            {
                "id": p.id,
                "proposer": p.proposer,
                "title": p.title,
                "description": p.description,
                "votes": p.votes,
                "status": p.status,
                "resolution_reason": getattr(p, "resolution_reason", None),
                "created_at": p.created_at,
            }
            for p in props[:limit]
        ]

    def share_learning(
        self,
        teacher: str,
        pattern: str,
        community_id: str = "general",
    ) -> dict[str, Any]:
        learn_id = f"learn-{uuid.uuid4().hex[:8]}"
        learning = PeerLearning(
            id=learn_id,
            teacher=teacher,
            pattern=pattern[:3000],
            community_id=community_id,
        )
        self.learnings.append(learning)
        if len(self.learnings) > 100:
            self.learnings[:] = self.learnings[-80:]
        return {
            "id": learning.id,
            "teacher": learning.teacher,
            "pattern": learning.pattern,
            "community_id": learning.community_id,
            "adopted_by": learning.adopted_by,
            "rejected_by": learning.rejected_by,
            "created_at": learning.created_at,
        }

    def adopt_learning(self, learning_id: str, agent_role: str) -> dict[str, Any]:
        for L in self.learnings:
            if L.id == learning_id:
                if agent_role not in L.adopted_by:
                    L.adopted_by.append(agent_role)
                if agent_role in L.rejected_by:
                    L.rejected_by.remove(agent_role)
                return {
                    "id": L.id,
                    "adopted_by": L.adopted_by,
                    "rejected_by": L.rejected_by,
                }
        raise ValueError("Learning not found")

    def reject_learning(self, learning_id: str, agent_role: str) -> dict[str, Any]:
        for L in self.learnings:
            if L.id == learning_id:
                if agent_role not in L.rejected_by:
                    L.rejected_by.append(agent_role)
                if agent_role in L.adopted_by:
                    L.adopted_by.remove(agent_role)
                return {
                    "id": L.id,
                    "adopted_by": L.adopted_by,
                    "rejected_by": L.rejected_by,
                }
        raise ValueError("Learning not found")

    def list_learnings(self, teacher: str | None = None, limit: int = 30) -> list[dict]:
        items = list(self.learnings)
        if teacher:
            items = [L for L in items if L.teacher == teacher]
        items.sort(key=lambda L: L.created_at, reverse=True)
        return [
            {
                "id": L.id,
                "teacher": L.teacher,
                "pattern": L.pattern,
                "community_id": L.community_id,
                "adopted_by": L.adopted_by,
                "rejected_by": L.rejected_by,
                "created_at": L.created_at,
            }
            for L in items[:limit]
        ]


_social: AgentSocialNetwork | None = None


def get_social() -> AgentSocialNetwork:
    global _social
    if _social is None:
        _social = AgentSocialNetwork()
    return _social
