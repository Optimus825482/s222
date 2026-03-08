# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

See `package.json` for all npm scripts. Key commands:

```bash
npm run dev              # Start both backend (8001) and frontend (3015)
npm run dev:backend      # Backend only (FastAPI on port 8001)
npm run dev:frontend     # Frontend only (Next.js on port 3015)
npm run build            # Build frontend
npm run stop             # Stop all servers
```

## Architecture Overview

### High-Level Structure

```
multi-agent-dashboard/
├── backend/           # FastAPI server - WebSocket + REST API
├── frontend/          # Next.js 14 app - React 18 + Tailwind + Zustand
├── agents/            # 6 specialist agent implementations
├── pipelines/         # Pipeline execution engine
├── tools/             # Shared utilities, skills, and services
├── core/              # Data models, state management, events
└── data/              # Persistent storage (threads, skills, MCP config)
```

### Agent Architecture

6 specialist agents orchestrated by a central controller. Model configurations defined in `config.py` (MODELS dictionary):

| Agent        | Model           | Role                                             |
| ------------ | --------------- | ------------------------------------------------ |
| Orchestrator | Qwen3 80B       | Task analysis, decomposition, routing, synthesis |
| Thinker      | MiniMax M2.1    | Deep reasoning, analysis, planning               |
| Speed        | Step 3.5 Flash  | Quick responses, code generation, formatting     |
| Researcher   | GLM 4.7         | Web search, data gathering, summarization        |
| Reasoner     | Nemotron 3 Nano | Chain-of-thought, math, logic, verification      |
| Critic       | DeepSeek Chat   | Code review, fact-checking, quality gate         |

**Key files:** `agents/base.py`, `agents/orchestrator.py`, `config.py`

### Pipeline System

7 execution patterns in `pipelines/engine.py`:

1. **Sequential** - A → B → C (each builds on previous output)
2. **Parallel** - [A, B, C] simultaneously → merge results
3. **Consensus** - All agents answer same question → compare
4. **Iterative** - Evaluator-optimizer loop with scoring
5. **Deep Research** - Parallel gather → synthesis
6. **Idea-to-Project** - Multi-phase: PRD → Architecture → Scaffold
7. **Brainstorm** - 3-round debate: perspectives → cross-challenge → synthesis

### Tool Categories

Utilities organized by function in `tools/`:

- **Core** - Registry, sandbox, MCP client
- **Skills** - Dynamic skills, skill finder, hygiene, domain expertise
- **Memory** - RAG, teachability, caching
- **Quality** - Agent eval, confidence scoring, circuit breaker, reflexion
- **Monitoring** - Benchmark suite, error patterns, cost tracking, optimization
- **Services** - Workflow engine/scheduler, export, chart generation, presentations

### Backend API

`backend/main.py` provides:

- **WebSocket**: `/ws/chat` - Real-time event streaming
- **Auth**: Bearer token with bcrypt passwords, HMAC-signed tokens
- **REST**: `/api/*` endpoints for threads, agents, tools, workflows, benchmarks

### Frontend

- **Entry**: `frontend/src/app/desktop/page.tsx` - Main dashboard
- **State**: Zustand stores
- **Components**: 50+ React components organized by feature
- **Styling**: Tailwind CSS with Radix UI primitives

### Data Models

`core/models.py` defines:

- `Thread` - Unified execution state
- `Task` / `SubTask` - Task decomposition with agent assignment
- `Event` - Serialized event log
- `AgentMetrics` - Cumulative performance tracking
- Enums: `AgentRole`, `TaskStatus`, `PipelineType`, `EventType`

### External Services

- **PostgreSQL + pgvector** - Vector embeddings and persistent storage
- **Whoogle** - Self-hosted Google proxy for web search
- **MCP** - Model Context Protocol for external tool integration
- **NVIDIA API** - Primary LLM provider
- **DeepSeek API** - Critic agent

## Configuration

See `.env.example` for all environment variables. Key settings:

- **Database**: `DATABASE_URL` (PostgreSQL with SQLite fallback)
- **API Keys**: `NVIDIA_API_KEY`, `DEEPSEEK_API_KEY`
- **Ports**: Configured in `package.json` (backend: 8001, frontend: 3015)
- **Rate limiting**: 120 requests/minute per IP

## Development Notes

- Backend uses `sys.path.insert()` to import sibling modules
- Iterative pipeline has `auto/fast/full` modes with configurable thresholds (see `config.py`)
- Circuit breaker pattern for agent fallback on failures
- Skill injection via XML tags in agent context
- Thread state persisted to JSON files in `data/threads/`

## Related Documentation

- `ROADMAP.md` - Development roadmap and phase status
- `.env.example` - Environment variable reference
