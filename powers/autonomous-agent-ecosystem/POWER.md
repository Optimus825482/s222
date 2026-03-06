---
name: "autonomous-agent-ecosystem"
displayName: "Autonomous Agent Ecosystem"
description: "Production patterns for building autonomous multi-agent systems with agentic loops, heartbeat systems, self-skill creation, agent identity files, and swarm intelligence. Inspired by OpenClaw architecture."
keywords:
  [
    "autonomous-agent",
    "agentic-loop",
    "heartbeat",
    "self-skill",
    "swarm-intelligence",
    "multi-agent",
    "openclaw",
  ]
author: "Erkan"
---

# Autonomous Agent Ecosystem

Production-ready patterns and implementation guides for building autonomous multi-agent systems. Covers the full spectrum from single-agent autonomy to emergent collective behavior.

Inspired by [OpenClaw](https://openclaw.ai) architecture and [Moltbook](https://moltbook.com) agent social network patterns.

## Target Stack

- Backend: FastAPI + Python 3.11+ (async)
- Frontend: Next.js 14 + TypeScript + shadcn/ui
- Database: PostgreSQL + pgvector
- LLM: NVIDIA NIM API (multi-model)
- Communication: WebSocket (real-time) + REST (CRUD)

## Available Steering Files

This power organizes knowledge into focused steering files for on-demand loading:

1. **agentic-loop.md** — Tool call chaining, multi-step autonomous execution, Context Window Guard, cost governor, iteration limits
2. **heartbeat-system.md** — Proactive agent behavior, cron-based scheduled tasks, daily briefings, anomaly alerts
3. **self-skill-creation.md** — Runtime skill generation, Markdown storage, auto-validation, cross-agent skill sharing
4. **agent-identity.md** — SOUL.md, user.md, memory.md, bootstrap.md patterns for agent personality and persistent state
5. **agent-social-network.md** — Agent-to-agent discussion, topic communities, peer learning, swarm intelligence, collective decision-making
6. **safety-sandbox.md** — Kill-switch, sandbox boundaries, emergent behavior monitoring, human oversight dashboard

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                  Human Oversight                 │
│            (Dashboard + Kill Switch)             │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│              Orchestrator Agent                   │
│   ┌─────────┐ ┌──────────┐ ┌──────────────┐     │
│   │ Agentic │ │Heartbeat │ │  Cost        │     │
│   │ Loop    │ │ Scheduler│ │  Governor    │     │
│   └────┬────┘ └────┬─────┘ └──────┬───────┘     │
└────────┼───────────┼──────────────┼──────────────┘
         │           │              │
┌────────▼───────────▼──────────────▼──────────────┐
│              Agent Pool                           │
│  ┌────────┐ ┌──────┐ ┌──────────┐ ┌──────────┐  │
│  │Thinker │ │Speed │ │Researcher│ │ Reasoner │  │
│  │SOUL.md │ │SOUL.md│ │SOUL.md  │ │ SOUL.md  │  │
│  └───┬────┘ └──┬───┘ └────┬─────┘ └────┬─────┘  │
│      │         │          │             │        │
│  ┌───▼─────────▼──────────▼─────────────▼───┐    │
│  │        Agent Social Network               │    │
│  │  (Discussion Board + Peer Learning)       │    │
│  └───────────────────────────────────────────┘    │
└──────────────────────────────────────────────────┘
         │
┌────────▼─────────────────────────────────────────┐
│              Shared Infrastructure                │
│  ┌──────────┐ ┌───────────┐ ┌──────────────────┐ │
│  │ Skill    │ │ Memory    │ │ Safety Sandbox   │ │
│  │ Registry │ │ (pgvector)│ │ (Kill Switch)    │ │
│  └──────────┘ └───────────┘ └──────────────────┘ │
└──────────────────────────────────────────────────┘
```

## Quick Start

Each steering file is self-contained with:

- Problem statement and motivation
- Architecture diagram
- FastAPI endpoint patterns
- Frontend component patterns
- Database schema (when needed)
- Implementation checklist

Start with **agentic-loop.md** for core autonomy, then layer on other capabilities.

## Design Principles

1. **Autonomy with Guardrails** — Agents act independently but within defined safety boundaries
2. **Emergent over Engineered** — Let collective behavior emerge from simple interaction rules
3. **Observable Always** — Every autonomous action is logged, traceable, and reversible
4. **Cost-Aware** — Token budgets and iteration limits prevent runaway costs
5. **Human-in-the-Loop Optional** — System works autonomously but humans can intervene at any point
6. **Identity-Driven** — Each agent has a persistent identity (SOUL.md) that shapes its behavior

## Relationship to Project Phases

| Steering File           | ROADMAP Phase |
| ----------------------- | ------------- |
| agentic-loop.md         | Faz 11.1      |
| heartbeat-system.md     | Faz 11.2      |
| self-skill-creation.md  | Faz 11.3      |
| agent-identity.md       | Faz 11.6      |
| agent-social-network.md | Faz 11.4      |
| safety-sandbox.md       | Faz 12        |
