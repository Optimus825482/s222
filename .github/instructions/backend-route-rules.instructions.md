---
description: "Use when adding or updating FastAPI routes, websocket endpoints, or backend API wiring in this workspace."
applyTo: "backend/routes/**/*.py, backend/main.py, backend/deps.py, core/**/*.py"
---

# Backend Route Rules

## Scope

- Apply these rules when implementing or changing API routes in backend.

## Route Design

- Keep route handlers thin: validation, orchestration, and response shaping only.
- Push business logic into services/core layers instead of route files.
- Keep endpoint names and tags consistent with existing route modules.

## Safety and Contracts

- Do not break existing response contracts without explicit migration note.
- Keep frontend-backend contract alignment in mind for websocket and REST events.
- Validate request inputs early and return explicit error payloads.

## Wiring and Registration

- When adding a new route module, verify registration in backend/main.py.
- For dependency changes, verify backend/deps.py integration and import paths.
- Keep imports robust; avoid fragile path assumptions.

## Verification

- For backend route changes, run at least one relevant test before completion:
  - pytest tests -q
- If websocket or messaging behavior changed, run targeted tests in tests/ related to ws/messaging routes.
