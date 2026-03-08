"""Agent social network — communities, discussions, swarm proposals, peer learning."""

import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import get_current_user, _audit
from shared_state import _AGENT_ROLES

router = APIRouter()


def _social():
    from tools.agent_social import get_social
    return get_social()


# ── Communities ────────────────────────────────────────────────

@router.get("/api/social/communities")
async def list_communities(user: dict = Depends(get_current_user)):
    """List all agent communities."""
    return {"communities": _social().list_communities()}


# ── Discussions ────────────────────────────────────────────────

@router.get("/api/social/discussions")
async def list_discussions(
    community_id: str | None = None,
    limit: int = 20,
    user: dict = Depends(get_current_user),
):
    """List discussions, optionally filtered by community."""
    return {"discussions": _social().list_discussions(community_id=community_id, limit=limit)}


@router.get("/api/social/discussions/{discussion_id}")
async def get_discussion(
    discussion_id: str,
    user: dict = Depends(get_current_user),
):
    """Get a single discussion with messages."""
    disc = _social().get_discussion(discussion_id)
    if not disc:
        raise HTTPException(404, "Discussion not found")
    return disc


class CreateDiscussionRequest(BaseModel):
    community_id: str
    topic: str
    starter: str
    message: str


@router.post("/api/social/discussions")
async def create_discussion(
    req: CreateDiscussionRequest,
    user: dict = Depends(get_current_user),
):
    """Start a new discussion in a community."""
    _audit("social_discussion_create", user["user_id"], detail=req.community_id)
    if req.starter not in _AGENT_ROLES:
        raise HTTPException(400, "Invalid starter role")
    try:
        return _social().start_discussion(
            community_id=req.community_id,
            topic=req.topic,
            starter=req.starter,
            initial_message=req.message,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


class PostMessageRequest(BaseModel):
    agent_role: str
    content: str


@router.post("/api/social/discussions/{discussion_id}/message")
async def post_discussion_message(
    discussion_id: str,
    body: PostMessageRequest,
    user: dict = Depends(get_current_user),
):
    """Post a message to a discussion."""
    if body.agent_role not in _AGENT_ROLES:
        raise HTTPException(400, "Invalid agent role")
    try:
        return _social().post_message(discussion_id, body.agent_role, body.content)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Swarm Proposals ────────────────────────────────────────────

class CreateProposalRequest(BaseModel):
    proposer: str
    title: str
    description: str


@router.post("/api/social/proposals")
async def create_proposal(
    req: CreateProposalRequest,
    user: dict = Depends(get_current_user),
):
    """Create a swarm proposal for collective voting."""
    _audit("social_proposal_create", user["user_id"], detail=req.title)
    if req.proposer not in _AGENT_ROLES:
        raise HTTPException(400, "Invalid proposer role")
    return _social().create_proposal(
        proposer=req.proposer,
        title=req.title,
        description=req.description,
    )


@router.get("/api/social/proposals")
async def list_proposals(
    status: str | None = None,
    limit: int = 30,
    user: dict = Depends(get_current_user),
):
    """List proposals (optionally by status)."""
    return {"proposals": _social().list_proposals(status=status, limit=limit)}


@router.post("/api/social/proposals/{proposal_id}/vote")
async def vote_proposal(
    proposal_id: str,
    voter: str,
    vote: str,
    user: dict = Depends(get_current_user),
):
    """Vote on a proposal (agree, disagree, abstain)."""
    if voter not in _AGENT_ROLES:
        raise HTTPException(400, "Invalid voter role")
    try:
        return _social().vote(proposal_id, voter, vote)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Collective decision policy (Faz 12.2) ───────────────────────

@router.get("/api/social/collective-policy")
async def get_collective_policy(user: dict = Depends(get_current_user)):
    """Get quorum, majority, tie-breaker and escalation policy."""
    from tools.collective_decision_policy import get_policy
    return {"policy": get_policy()}


class UpdatePolicyRequest(BaseModel):
    quorum_min_votes: int | None = None
    majority_ratio: float | None = None
    tie_breaker: str | None = None  # proposer_wins | reject | random | human
    allow_human_escalation: bool | None = None
    escalation_threshold_ratio: float | None = None


@router.patch("/api/social/collective-policy")
async def update_collective_policy(
    req: UpdatePolicyRequest,
    user: dict = Depends(get_current_user),
):
    """Update collective decision policy (quorum, majority, tie-breaker)."""
    _audit("social_policy_update", user["user_id"])
    from tools.collective_decision_policy import update_policy
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    return {"policy": update_policy(updates)}


class ResolveProposalRequest(BaseModel):
    resolution: str  # passed | rejected
    reason: str | None = None


@router.post("/api/social/proposals/{proposal_id}/resolve")
async def resolve_proposal_human(
    proposal_id: str,
    body: ResolveProposalRequest,
    user: dict = Depends(get_current_user),
):
    """Resolve a proposal in needs_human status (human escalation — Faz 12.2)."""
    _audit("social_proposal_resolve", user["user_id"], detail=proposal_id)
    try:
        return _social().resolve_proposal(
            proposal_id,
            resolution=body.resolution,
            reason=body.reason,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Peer Learning ──────────────────────────────────────────────

class ShareLearningRequest(BaseModel):
    teacher: str
    pattern: str
    community_id: str = "general"


@router.post("/api/social/learnings")
async def share_learning(
    req: ShareLearningRequest,
    user: dict = Depends(get_current_user),
):
    """Share a learned pattern to a community (peer learning)."""
    _audit("social_learning_share", user["user_id"], detail=req.teacher)
    if req.teacher not in _AGENT_ROLES:
        raise HTTPException(400, "Invalid teacher role")
    try:
        return _social().share_learning(
            teacher=req.teacher,
            pattern=req.pattern,
            community_id=req.community_id,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/api/social/learnings")
async def list_learnings(
    teacher: str | None = None,
    limit: int = 30,
    user: dict = Depends(get_current_user),
):
    """List peer learnings."""
    return {"learnings": _social().list_learnings(teacher=teacher, limit=limit)}


@router.post("/api/social/learnings/{learning_id}/adopt")
async def adopt_learning(
    learning_id: str,
    agent_role: str,
    user: dict = Depends(get_current_user),
):
    """Mark that an agent adopts this learning."""
    if agent_role not in _AGENT_ROLES:
        raise HTTPException(400, "Invalid agent role")
    try:
        return _social().adopt_learning(learning_id, agent_role)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/api/social/learnings/{learning_id}/reject")
async def reject_learning(
    learning_id: str,
    agent_role: str,
    user: dict = Depends(get_current_user),
):
    """Mark that an agent rejects this learning."""
    if agent_role not in _AGENT_ROLES:
        raise HTTPException(400, "Invalid agent role")
    try:
        return _social().reject_learning(learning_id, agent_role)
    except ValueError as e:
        raise HTTPException(404, str(e))
