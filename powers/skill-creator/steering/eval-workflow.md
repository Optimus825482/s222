# Eval Workflow

Complete evaluation pipeline for testing, grading, benchmarking, and iterating on skills.

---

## Overview

The eval workflow is one continuous sequence:

1. Spawn all runs (with-skill AND baseline) simultaneously
2. While runs execute, draft quantitative assertions
3. Capture timing data as runs complete
4. Grade, aggregate, and launch the viewer
5. Read user feedback
6. Improve the skill and repeat

## Step 1: Create Test Cases

Come up with 2-3 realistic test prompts — what a real user would actually say. Save to `evals/evals.json`:

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's task prompt",
      "expected_output": "Description of expected result",
      "files": [],
      "expectations": ["The output includes X", "The format is Y"]
    }
  ]
}
```

## Step 2: Run Tests

For each test case, spawn two runs simultaneously:

**With-skill run:**

- Provide skill path and eval prompt
- Save outputs to `<workspace>/iteration-N/eval-ID/with_skill/outputs/`

**Baseline run:**

- New skill: no skill at all (same prompt, no skill path) → `without_skill/outputs/`
- Improving existing: snapshot old version → `old_skill/outputs/`

Create `eval_metadata.json` for each test case:

```json
{
  "eval_id": 0,
  "eval_name": "descriptive-name-here",
  "prompt": "The user's task prompt",
  "assertions": []
}
```

## Step 3: Draft Assertions While Runs Execute

Good assertions are:

- Objectively verifiable
- Descriptive names (readable in benchmark viewer)
- Not forced onto subjective outputs

Update `eval_metadata.json` and `evals/evals.json` with assertions.

## Step 4: Capture Timing

When each run completes, save timing data immediately to `timing.json`:

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

## Step 5: Grade

Grade each run's assertions against outputs. Use the `grade_skill_output` MCP tool or grade inline.

Grading criteria:

- **PASS**: Clear evidence + genuine task completion (not surface compliance)
- **FAIL**: No evidence, contradicting evidence, or superficial compliance

Save to `grading.json` with fields: `text`, `passed`, `evidence` (the viewer depends on these exact names).

For programmatically checkable assertions, write and run a script rather than eyeballing.

## Step 6: Aggregate Benchmark

Use the `aggregate_benchmark` MCP tool or run:

```bash
python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>
```

Produces `benchmark.json` with pass_rate, time, tokens for each configuration (mean ± stddev + delta).

## Step 7: Analyst Pass

Surface patterns the aggregate stats might hide:

- Assertions that always pass regardless of skill (non-discriminating)
- High-variance evals (possibly flaky)
- Time/token tradeoffs
- Surprising results

## Step 8: Launch Viewer

Use the `generate_eval_viewer` MCP tool or run:

```bash
python generate_review.py <workspace>/iteration-N --skill-name "my-skill" --benchmark <benchmark.json>
```

For iteration 2+, pass `--previous-workspace` for comparison.
For headless environments, use `--static <output_path>`.

Tell the user: "Results are ready for review. The Outputs tab shows each test case with feedback boxes. The Benchmark tab shows quantitative comparison."

## Step 9: Read Feedback

Read `feedback.json` after user review:

```json
{
  "reviews": [
    {
      "run_id": "eval-0-with_skill",
      "feedback": "missing axis labels",
      "timestamp": "..."
    }
  ],
  "status": "complete"
}
```

Empty feedback = user thought it was fine. Focus improvements on specific complaints.

## Improvement Principles

1. **Generalize from feedback** — don't overfit to test examples
2. **Keep the prompt lean** — remove what isn't pulling its weight
3. **Explain the why** — reasoning > rigid rules
4. **Look for repeated work** — bundle common scripts
5. **Read transcripts** — understand execution patterns, not just outputs

## Iteration Loop

After improving:

1. Apply improvements to skill
2. Rerun all test cases into `iteration-N+1/`
3. Launch viewer with `--previous-workspace`
4. Wait for user review
5. Read feedback, improve, repeat

Stop when:

- User is happy
- All feedback is empty
- No meaningful progress being made

## Blind Comparison (Advanced)

For rigorous A/B comparison between skill versions:

1. Give two outputs to an independent judge without revealing which is which
2. Judge evaluates on content (correctness, completeness, accuracy) and structure (organization, formatting, usability)
3. Analyze why the winner won — extract actionable improvement suggestions

## JSON Schemas

### grading.json

```json
{
  "expectations": [{ "text": "...", "passed": true, "evidence": "..." }],
  "summary": { "passed": 2, "failed": 1, "total": 3, "pass_rate": 0.67 },
  "execution_metrics": { "tool_calls": {}, "total_tool_calls": 15 },
  "claims": [
    { "claim": "...", "type": "factual", "verified": true, "evidence": "..." }
  ],
  "eval_feedback": { "suggestions": [], "overall": "..." }
}
```

### benchmark.json

```json
{
  "metadata": { "skill_name": "...", "timestamp": "..." },
  "runs": [
    {
      "eval_id": 1,
      "configuration": "with_skill",
      "run_number": 1,
      "result": { "pass_rate": 0.85 }
    }
  ],
  "run_summary": {
    "with_skill": { "pass_rate": { "mean": 0.85, "stddev": 0.05 } },
    "without_skill": { "pass_rate": { "mean": 0.35, "stddev": 0.08 } },
    "delta": { "pass_rate": "+0.50" }
  },
  "notes": []
}
```
