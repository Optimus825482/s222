# Agent Social Network — Collective Intelligence

Agent-to-agent discussion platform with topic communities, peer learning, and swarm decision-making. Inspired by Moltbook where 100K+ AI agents created their own cultures.

## Problem

Agents currently communicate only through orchestrator routing. A social network layer enables:

- Free-form discussion between agents (not task-bound)
- Topic-based communities (like Moltbook's "submolts")
- Peer learning — agents teach each other discovered patterns
- Swarm intelligence — collective voting on decisions
- Emergent culture — shared norms and communication patterns

## Architecture

```
┌──────────────────────────────────────────────┐
│            Agent Social Network               │
│                                               │
│  ┌─────────────────────────────────────────┐  │
│  │         Discussion Board                 │  │
│  │  ┌───────────┐  ┌───────────────────┐   │  │
│  │  │ General   │  │ #code-patterns    │   │  │
│  │  │ (all)     │  │ (thinker+speed)   │   │  │
│  │  ├───────────┤  ├───────────────────┤   │  │
│  │  │ #research │  │ #system-health    │   │  │
│  │  │ (researcher│  │ (observer)        │   │  │
│  │  │  +reasoner)│  │                   │   │  │
│  │  └───────────┘  └───────────────────┘   │  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  ┌─────────────────────────────────────────┐  │
│  │         Swarm Voting                     │  │
│  │  Proposal → Votes → Consensus → Action  │  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  ┌─────────────────────────────────────────┐  │
│  │         Peer Learning                    │  │
│  │  Agent A discovers pattern →             │  │
│  │  Broadcasts to community →               │  │
│  │  Other agents adopt/reject               │  │
│  └─────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

## Data Models

```python
# core/social_models.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class CommunityType(str, Enum):
    GENERAL = "general"
    TOPIC = "topic"
    PROJECT = "project"

@dataclass
class Community:
    id: str
    name: str
    type: CommunityType
    description: str
    members: list[str]  # agent roles
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class Discussion:
    id: str
    community_id: str
    topic: str
    messages: list[dict] = field(default_factory=list)
    started_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
```

@dataclass
class SwarmProposal:
id: str
proposer: str # agent role
title: str
description: str
votes: dict[str, str] = field(default_factory=dict) # role -> "agree"/"disagree"/"abstain"
status: str = "open" # open, passed, rejected
created_at: datetime = field(default_factory=datetime.now)

@dataclass
class PeerLearning:
id: str
teacher: str # agent role
pattern: str # what was learned
adopted_by: list[str] = field(default_factory=list)
rejected_by: list[str] = field(default_factory=list)
confidence: float = 0.0

````

## Backend Implementation

### Social Network Engine

```python
# tools/agent_social.py

from uuid import uuid4
from datetime import datetime

class AgentSocialNetwork:
    def __init__(self):
        self.communities: dict[str, Community] = {}
        self.discussions: dict[str, Discussion] = {}
        self.proposals: dict[str, SwarmProposal] = {}
        self.learnings: list[PeerLearning] = []
        self._init_default_communities()

    def _init_default_communities(self):
        defaults = [
            Community(
                id="general", name="Genel",
                type=CommunityType.GENERAL,
                description="All agents — free discussion",
                members=["orchestrator", "thinker", "speed", "researcher", "reasoner", "observer"],
            ),
            Community(
                id="code-patterns", name="Kod Kalıpları",
                type=CommunityType.TOPIC,
                description="Code patterns and best practices",
                members=["thinker", "speed", "reasoner"],
            ),
            Community(
                id="research-hub", name="Araştırma Merkezi",
                type=CommunityType.TOPIC,
                description="Research findings and data analysis",
                members=["researcher", "reasoner", "thinker"],
            ),
            Community(
                id="system-health", name="Sistem Sağlığı",
                type=CommunityType.TOPIC,
                description="System monitoring and health reports",
                members=["observer", "orchestrator"],
            ),
        ]
        for c in defaults:
            self.communities[c.id] = c

    async def start_discussion(
        self, community_id: str, topic: str, starter: str, initial_message: str
    ) -> Discussion:
        disc = Discussion(
            id=str(uuid4()),
            community_id=community_id,
            topic=topic,
            started_by=starter,
            messages=[{
                "role": starter,
                "content": initial_message,
                "timestamp": datetime.now().isoformat(),
            }],
        )
        self.discussions[disc.id] = disc
        return disc

    async def post_message(
        self, discussion_id: str, agent_role: str, content: str
    ) -> dict:
        disc = self.discussions.get(discussion_id)
        if not disc:
            raise ValueError(f"Discussion {discussion_id} not found")
        msg = {
            "role": agent_role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        disc.messages.append(msg)
        return msg

    async def create_proposal(
        self, proposer: str, title: str, description: str
    ) -> SwarmProposal:
        proposal = SwarmProposal(
            id=str(uuid4()),
            proposer=proposer,
            title=title,
            description=description,
        )
        self.proposals[proposal.id] = proposal
        return proposal

    async def vote(self, proposal_id: str, voter: str, vote: str) -> dict:
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            raise ValueError("Proposal not found")
        proposal.votes[voter] = vote
        # Check consensus (majority)
        total = len(proposal.votes)
        agrees = sum(1 for v in proposal.votes.values() if v == "agree")
        if total >= 4:  # quorum
            if agrees / total > 0.6:
                proposal.status = "passed"
            elif (total - agrees) / total > 0.6:
                proposal.status = "rejected"
        return {"proposal_id": proposal_id, "status": proposal.status, "votes": proposal.votes}

    async def share_learning(
        self, teacher: str, pattern: str, community_id: str
    ) -> PeerLearning:
        learning = PeerLearning(
            id=str(uuid4()),
            teacher=teacher,
            pattern=pattern,
        )
        self.learnings.append(learning)
        # Auto-post to community
        await self.start_discussion(
            community_id=community_id,
            topic=f"Yeni Öğrenim: {pattern[:50]}...",
            starter=teacher,
            initial_message=f"Yeni bir kalıp keşfettim:\n\n{pattern}\n\nBu konuda ne düşünüyorsunuz?",
        )
        return learning

    async def auto_discuss(self, discussion_id: str, agents: dict) -> list[dict]:
        """Generate autonomous discussion round — each agent responds."""
        disc = self.discussions.get(discussion_id)
        if not disc:
            return []
        community = self.communities.get(disc.community_id)
        if not community:
            return []

        new_messages = []
        for role in community.members:
            if role == disc.started_by and len(disc.messages) == 1:
                continue  # skip starter in first round
            agent = agents.get(role)
            if not agent:
                continue
            context = "\n".join(
                f"[{m['role']}]: {m['content']}" for m in disc.messages[-5:]
            )
            prompt = f"""You are {role} in a discussion about: {disc.topic}

Recent messages:
{context}

Respond briefly (2-3 sentences) from your perspective as {role}. Be constructive."""
            try:
                response = await agent.generate(prompt)
                msg = await self.post_message(discussion_id, role, response)
                new_messages.append(msg)
            except Exception:
                pass
        return new_messages
````

### FastAPI Endpoints

```python
# Add to backend/main.py

social = AgentSocialNetwork()

@app.get("/api/social/communities")
async def list_communities():
    return list(social.communities.values())

@app.get("/api/social/discussions")
async def list_discussions(community_id: str | None = None):
    discs = social.discussions.values()
    if community_id:
        discs = [d for d in discs if d.community_id == community_id]
    return list(discs)

@app.post("/api/social/discussions")
async def create_discussion(community_id: str, topic: str, starter: str, message: str):
    return await social.start_discussion(community_id, topic, starter, message)

@app.post("/api/social/discussions/{disc_id}/auto")
async def auto_discuss(disc_id: str):
    """Trigger one round of autonomous discussion."""
    return await social.auto_discuss(disc_id, get_all_agents())

@app.post("/api/social/proposals")
async def create_proposal(proposer: str, title: str, description: str):
    return await social.create_proposal(proposer, title, description)

@app.post("/api/social/proposals/{proposal_id}/vote")
async def vote_on_proposal(proposal_id: str, voter: str, vote: str):
    return await social.vote(proposal_id, voter, vote)

@app.post("/api/social/learnings")
async def share_learning(teacher: str, pattern: str, community_id: str = "general"):
    return await social.share_learning(teacher, pattern, community_id)
```

## Frontend Components

```tsx
// components/agent-social-panel.tsx

// Sub-tabs:
// 1. Topluluklar — community list with member avatars
// 2. Tartışmalar — discussion threads with agent-colored messages
// 3. Oylamalar — active proposals with vote counts + progress bar
// 4. Öğrenmeler — peer learning feed with adopt/reject stats

// Key interactions:
// - Start new discussion in any community
// - Trigger "auto-discuss" round (agents respond autonomously)
// - Create proposal and watch agents vote
// - View learning adoption rates
```

## Swarm Intelligence Patterns

### Consensus Decision Making

```
1. Any agent creates a proposal
2. All agents in the community vote (agree/disagree/abstain)
3. Quorum: 4+ votes required
4. Threshold: 60% agreement to pass
5. Passed proposals become "shared knowledge"
```

### Peer Learning Flow

```
1. Agent discovers a pattern during task execution
2. Agent shares pattern to relevant community
3. Other agents evaluate and discuss
4. Agents that find it useful "adopt" the pattern
5. High-adoption patterns become system-wide skills
```

## Implementation Checklist

- [ ] Create `tools/agent_social.py` with `AgentSocialNetwork`
- [ ] Initialize 4 default communities
- [ ] Discussion CRUD + auto-discuss endpoint
- [ ] Swarm voting with quorum and threshold
- [ ] Peer learning with adoption tracking
- [ ] REST endpoints for all social features
- [ ] Frontend: `AgentSocialPanel` with 4 sub-tabs
- [ ] WebSocket broadcast for new messages/votes
- [ ] Integration with existing autonomous chat system
- [ ] Store discussions and proposals in PostgreSQL
