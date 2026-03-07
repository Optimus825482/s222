---
name: "skill-creator"
displayName: "Skill Creator"
description: "Create, test, and iteratively improve AI skills with eval-driven development. Includes grading, benchmarking, blind comparison, and description optimization. Use when building new skills, improving existing prompts, running evaluations, or measuring skill performance."
keywords:
  [
    "skill",
    "eval",
    "benchmark",
    "grading",
    "prompt-engineering",
    "skill-creator",
    "iterative-improvement",
  ]
author: "Anthropic (adapted for Kiro by Erkan)"
---

# Skill Creator

A comprehensive power for creating new AI skills and iteratively improving them through eval-driven development.

## Overview

Skill Creator packages the full skill development lifecycle:

1. Draft a skill based on user intent
2. Create test cases and run them (with-skill vs baseline)
3. Grade outputs against expectations
4. Benchmark performance with statistical analysis
5. Review results in an interactive HTML viewer
6. Iterate based on feedback until quality targets are met
7. Optimize skill descriptions for accurate triggering

This power adapts Anthropic's official skill-creator methodology for the Kiro ecosystem, adding an MCP server for programmatic access to grading, benchmarking, and eval operations.

## Available Steering Files

This power has three steering files for progressive disclosure:

- **skill-writing-guide** — How to write effective skills: anatomy, patterns, progressive disclosure, YAML frontmatter, bundled resources
- **eval-workflow** — Complete eval pipeline: spawning runs, grading, aggregating benchmarks, launching the HTML viewer, reading feedback, iteration loop
- **description-optimization** — Optimize skill descriptions for triggering accuracy: generating eval queries, train/test split, optimization loop

Read steering files on-demand based on the current task phase.

## Available MCP Server

### skill-creator-server

A Python-based MCP server providing programmatic access to skill evaluation tools.

**Tools:**

| Tool                   | Description                                                                                                                    |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `grade_skill_output`   | Grade a skill's output against expectations. Provide output text + expectations list, returns pass/fail with evidence for each |
| `aggregate_benchmark`  | Aggregate grading results from a workspace directory into benchmark.json with mean/stddev/delta statistics                     |
| `generate_eval_viewer` | Generate a standalone HTML eval viewer from a workspace directory for human review                                             |
| `validate_skill`       | Validate a SKILL.md file structure: checks frontmatter, description quality, line count, reference links                       |
| `search_skills`        | Search existing skills by keyword to find similar or related skills before creating new ones                                   |

## Quick Start

### Creating a New Skill

1. Capture intent — what should the skill do, when should it trigger, expected output format
2. Read the **skill-writing-guide** steering for writing patterns
3. Write the SKILL.md with proper frontmatter and instructions
4. Create test cases in evals/evals.json
5. Read the **eval-workflow** steering for the full test/grade/iterate loop

### Improving an Existing Skill

1. Use `validate_skill` tool to check current skill quality
2. Read the **eval-workflow** steering
3. Run test cases, grade, review, iterate
4. When satisfied, read **description-optimization** steering to optimize triggering

### Running Evaluations

Use the MCP tools for programmatic eval operations:

```
# Grade a single output
grade_skill_output(output="...", expectations=["includes X", "format is Y"])

# Aggregate results from workspace
aggregate_benchmark(workspace_dir="./my-skill-workspace/iteration-1", skill_name="my-skill")

# Generate viewer for human review
generate_eval_viewer(workspace_dir="./my-skill-workspace/iteration-1", skill_name="my-skill")
```

## Core Workflow Loop

```
Draft Skill → Create Test Cases → Run Tests → Grade → Benchmark → Review → Improve → Repeat
```

Each iteration produces:

- Grading results (pass/fail per expectation with evidence)
- Benchmark statistics (pass_rate, time, tokens with mean ± stddev)
- HTML viewer for qualitative human review
- Feedback JSON for structured iteration

## Skill Anatomy

```
skill-name/
├── SKILL.md          # Required: frontmatter + instructions
├── evals/
│   └── evals.json    # Test cases with expectations
└── Bundled Resources (optional)
    ├── scripts/      # Deterministic/repetitive tasks
    ├── references/   # Docs loaded into context as needed
    └── assets/       # Templates, icons, fonts
```

## Key Principles

- Explain the WHY behind instructions — LLMs respond better to reasoning than rigid rules
- Keep skills under 500 lines — use references/ for overflow
- Generalize from feedback — don't overfit to specific test cases
- Use progressive disclosure — metadata → SKILL.md body → bundled resources
- Draft assertions while tests run — don't waste idle time
- Always generate the eval viewer before making changes — get human feedback first

## Troubleshooting

### Skill Not Triggering

- Description may be too narrow — read description-optimization steering
- Use `validate_skill` to check frontmatter quality
- Ensure keywords cover common phrasings

### Low Pass Rates

- Check if expectations are too strict or ambiguous
- Read transcripts, not just outputs — understand execution patterns
- Look for repeated work across test cases — bundle common scripts

### Viewer Not Loading

- Ensure workspace has outputs/ directories with actual files
- Check that grading.json uses correct field names: `text`, `passed`, `evidence`
- Use `--static` flag for headless environments

## Configuration

**MCP Server Requirements:**

- Python 3.11+
- No external dependencies beyond stdlib (for core tools)
- anthropic package (for description optimization only)

---

**Adapted from:** Anthropic's official skill-creator
**License:** Apache 2.0
