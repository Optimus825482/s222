# Skill Writing Guide

Comprehensive guide for writing effective AI skills with proper structure, patterns, and progressive disclosure.

---

## Skill Anatomy

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/    - Executable code for deterministic/repetitive tasks
    ├── references/ - Docs loaded into context as needed
    └── assets/     - Files used in output (templates, icons, fonts)
```

## YAML Frontmatter

Every SKILL.md must start with:

```yaml
---
name: skill-name
description: What it does and when to use it. Be specific and slightly "pushy" to combat undertriggering. Example - "Build dashboards for data visualization. Use whenever the user mentions dashboards, metrics, charts, or wants to display any kind of data, even if they don't explicitly ask for a dashboard."
---
```

## Progressive Disclosure

Skills use a three-level loading system:

1. **Metadata** (name + description) — Always in context (~100 words)
2. **SKILL.md body** — In context when skill triggers (<500 lines ideal)
3. **Bundled resources** — Loaded as needed (unlimited size, scripts execute without loading)

Key patterns:

- Keep SKILL.md under 500 lines; use references/ for overflow
- Reference files clearly from SKILL.md with guidance on when to read them
- For large reference files (>300 lines), include a table of contents

## Writing Patterns

### Imperative Form

Use verb-first instructions: "Extract the data", "Validate the output", not "You should extract the data".

### Defining Output Formats

```markdown
## Report Structure

ALWAYS use this exact template:

# [Title]

## Executive summary

## Key findings

## Recommendations
```

### Examples Pattern

```markdown
## Commit Message Format

**Example 1:**
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication
```

### Domain Organization

When a skill supports multiple domains/frameworks:

```
cloud-deploy/
├── SKILL.md (workflow + selection logic)
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```

The model reads only the relevant reference file.

## Writing Style

- Explain WHY things are important — LLMs are smart and respond to reasoning
- Avoid heavy-handed MUSTs — reframe with reasoning instead
- Use theory of mind — make skills general, not narrow to specific examples
- If writing ALWAYS or NEVER in caps, that's a yellow flag — try explaining the reasoning instead
- Draft first, then review with fresh eyes and improve

## Capturing Intent

Before writing, clarify:

1. What should this skill enable the AI to do?
2. When should this skill trigger? (what user phrases/contexts)
3. What's the expected output format?
4. Should test cases be set up? (yes for objectively verifiable outputs, optional for subjective ones)

## Interview and Research

Proactively ask about:

- Edge cases and input/output formats
- Example files and success criteria
- Dependencies and environment requirements
- Check available tools/MCPs for research

## Bundled Scripts

When test runs show all cases independently writing similar helper scripts, that's a signal to bundle the script:

- Write it once in scripts/
- Reference from SKILL.md
- Saves every future invocation from reinventing the wheel

## Reference Links

All bundled resources must be properly linked in SKILL.md:

- `[filename.md](./references/filename.md)` — not bare backtick references
- `[script.py](./scripts/script.py)` — for scripts
- `[template.html](./assets/template.html)` — for assets
