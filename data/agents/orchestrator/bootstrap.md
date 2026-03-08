---
agent: "orchestrator"
version: 1
---

# Bootstrap Protocol

## On Startup
1. Load SOUL.md — establish identity
2. Load user.md — understand user preferences
3. Load memory.md — restore cross-session context
4. Check pending tasks from last session
5. Report ready status to Orchestrator

## On New Task
1. Check memory.md for related past work
2. Review SOUL.md boundaries — am I the right agent?
3. If not → suggest delegation to appropriate agent
4. If yes → proceed with task using identity-consistent approach

## On Session End
1. Update memory.md with new learnings
2. Update user.md if preferences changed
3. Report session summary to Orchestrator
