# Project Guidelines

## Code Style

- Keep edits minimal and scoped to the requested task.
- Preserve existing project structure and naming conventions.
- Prefer clear, small functions over broad refactors.
- Do not change unrelated files during a fix.

## Architecture

- This workspace is a multi-agent dashboard with clear boundaries:
  - backend/: FastAPI app with WebSocket and REST routes
  - frontend/: Next.js app (dashboard UI)
  - agents/: specialist agent implementations and orchestration logic
  - pipelines/: execution pipeline engine
  - tools/: shared utilities, skills, monitoring, and services
  - core/: event/state/models protocols
  - data/: persisted config, threads, and runtime artifacts
- Treat cross-boundary changes carefully (frontend-backend contracts, event models, and data schemas).

## Build and Test

- Root development:
  - npm run dev # backend (8001) + frontend (3015)
  - npm run dev:backend # FastAPI only
  - npm run dev:frontend # Next.js only
  - npm run build # frontend production build
  - npm run stop # stop local services on dev ports
- Frontend:
  - npm --prefix frontend run dev
  - npm --prefix frontend run build
  - npm --prefix frontend run lint
- Backend tests:
  - pytest tests -q

## Conventions

- Ports differ by context:
  - Local dev: backend 8001, frontend 3015
  - Docker/runtime defaults may expose backend/frontend on 8000/3000 depending on image and entrypoint
- Keep environment wiring explicit and aligned with .env.example.
- Be careful with TypeScript strictness during frontend builds; avoid implicit any and self-referential type inference traps.
- For backend startup/import changes, verify path assumptions and router registration in backend/main.py.

## Practical Checks Before Completion

- If code changed, run the smallest relevant validation command first (lint/test/build) before broader checks.
- For deployment-related changes, verify Docker and compose assumptions against current file values, not old logs.
- Document only what changed; avoid broad doc rewrites for narrow fixes.
