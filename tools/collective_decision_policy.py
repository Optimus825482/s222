"""
Faz 12.2 — Kolektif Karar Alma policy.
Quorum, çoğunluk kuralı, tie-breaker ve insan escalation yapılandırması.
"""

from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
POLICY_PATH = DATA_DIR / "collective_decision_policy.json"

DEFAULT_POLICY = {
    "quorum_min_votes": 4,
    "majority_ratio": 0.6,
    "tie_breaker": "proposer_wins",  # proposer_wins | reject | random | human
    "allow_human_escalation": True,
    "escalation_threshold_ratio": 0.55,  # if 0.45 <= agree_ratio <= 0.55 → needs_human (optional)
}


def load_policy() -> dict:
    if not POLICY_PATH.exists():
        return dict(DEFAULT_POLICY)
    try:
        with open(POLICY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        out = dict(DEFAULT_POLICY)
        out.update({k: v for k, v in data.items() if k in out})
        return out
    except Exception as e:
        logger.warning("collective_decision_policy: load failed %s", e)
        return dict(DEFAULT_POLICY)


def save_policy(policy: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    allowed = set(DEFAULT_POLICY.keys())
    to_save = {k: v for k, v in policy.items() if k in allowed}
    with open(POLICY_PATH, "w", encoding="utf-8") as f:
        json.dump(to_save, f, indent=2, ensure_ascii=False)


def get_policy() -> dict:
    return load_policy()


def update_policy(updates: dict) -> dict:
    policy = load_policy()
    allowed = set(DEFAULT_POLICY.keys())
    for k, v in updates.items():
        if k in allowed:
            policy[k] = v
    save_policy(policy)
    return policy


def compute_result(
    agrees: int,
    disagrees: int,
    abstains: int,
    proposer: str,
    policy: dict | None = None,
) -> tuple[str, str | None]:
    """
    Returns (status, reason).
    status: "passed" | "rejected" | "needs_human" | "open"
    """
    policy = policy or load_policy()
    total = agrees + disagrees + abstains
    quorum = policy.get("quorum_min_votes", 4)
    majority_ratio = policy.get("majority_ratio", 0.6)
    tie_breaker = policy.get("tie_breaker", "proposer_wins")
    allow_escalation = policy.get("allow_human_escalation", True)
    escalation_threshold = policy.get("escalation_threshold_ratio", 0.55)

    if total < quorum:
        return ("open", f"Quorum not reached ({total}/{quorum})")

    # Only count agree vs disagree for ratio (abstain does not block)
    voting = agrees + disagrees
    if voting == 0:
        return ("open", "No agree/disagree votes yet")

    agree_ratio = agrees / voting
    disagree_ratio = disagrees / voting

    # Close call → human escalation if allowed
    if allow_escalation and escalation_threshold:
        low = 1.0 - escalation_threshold
        if low <= agree_ratio <= escalation_threshold:
            return ("needs_human", f"Close vote (agree {agree_ratio:.0%}) — human decision required")

    if agree_ratio > majority_ratio:
        return ("passed", f"Majority agreed ({agree_ratio:.0%})")
    if disagree_ratio > majority_ratio:
        return ("rejected", f"Majority rejected ({disagree_ratio:.0%})")

    # Tie or no clear majority
    if tie_breaker == "human" and allow_escalation:
        return ("needs_human", "Tie — human decision required")
    if tie_breaker == "proposer_wins":
        return ("passed", "Tie — proposer wins")
    if tie_breaker == "reject":
        return ("rejected", "Tie — default reject")
    # random: treat as needs_human so UI can resolve
    if tie_breaker == "random":
        return ("needs_human", "Tie — random resolution (resolve via API)")
    return ("needs_human", "Tie — human decision required")
