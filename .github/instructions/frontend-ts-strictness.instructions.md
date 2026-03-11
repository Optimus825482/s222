---
description: "Use when editing frontend TypeScript or Next.js files to prevent strict-mode and build-time type failures."
applyTo: "frontend/src/**/*.ts, frontend/src/**/*.tsx, frontend/*.ts, frontend/*.tsx"
---

# Frontend TypeScript Strictness

## Goals

- Keep TypeScript strict-build safe for Next.js production builds.

## Rules

- Avoid implicit any in function params, local variables, and callback signatures.
- Avoid self-referential initializers that produce implicit any cycles.
- Prefer explicit exported types for shared contracts in frontend/src/types.
- Keep runtime-safe guards around nullable and unknown values.

## Next.js and Build Stability

- Prefer stable, narrow types at API boundaries and hook return values.
- Avoid broad any propagation from utility modules into page/component code.
- For middleware/proxy related updates, follow current Next.js conventions in the repo.

## Validation

- Run fast checks after meaningful TS changes:
  - npm --prefix frontend run lint
  - npm --prefix frontend run build (when change impacts typing across modules)

## Known Pitfall Pattern

- If a variable is "referenced directly or indirectly in its own initializer", split expression into smaller typed steps and annotate intermediate values.
