---
description: "Run a deployment readiness checklist for this workspace before build or release."
name: "Deploy Readiness Check"
argument-hint: "Branch or target environment (optional)"
agent: "agent"
---

Perform a deployment-readiness check for this workspace.

## Input

- Target: ${input:target}

## Checklist

1. Confirm changed files and summarize deployment risk areas.
2. Validate environment assumptions against .env.example and docker-compose.yaml.
3. Run minimum relevant quality checks based on changed areas:
   - Backend-focused changes: pytest tests -q
   - Frontend-focused changes: npm --prefix frontend run lint
   - Cross-cutting or build-sensitive changes: npm --prefix frontend run build
4. Verify service/port expectations:
   - Local dev defaults: backend 8001, frontend 3015
   - Docker/runtime may expose 8000/3000
5. Flag known pitfalls explicitly (type strictness, route registration, env drift).
6. Output a concise go/no-go summary with:
   - Passed checks
   - Failed checks
   - Blocking issues
   - Recommended next command

## Output format

- "Readiness: GO" or "Readiness: NO-GO"
- Bullet list of findings and next action.
