# Description Optimization

Optimize skill descriptions for accurate triggering using eval-driven iteration with train/test split.

---

## Overview

The description field in SKILL.md frontmatter is the primary mechanism that determines whether an AI invokes a skill. This workflow optimizes descriptions for triggering accuracy.

## Step 1: Generate Trigger Eval Queries

Create 20 eval queries — mix of should-trigger (8-10) and should-not-trigger (8-10):

```json
[
  { "query": "realistic user prompt with detail", "should_trigger": true },
  {
    "query": "near-miss that shares keywords but needs something different",
    "should_trigger": false
  }
]
```

### Query Quality Guidelines

**Good queries are:**

- Realistic — what a real user would type
- Detailed — file paths, personal context, column names, company names
- Varied — mix of lengths, some casual/abbreviated, some formal
- Edge-case focused — not clear-cut

**Bad queries:** `"Format this data"`, `"Extract text from PDF"` — too generic, too easy.

**Should-trigger queries (8-10):**

- Different phrasings of the same intent
- Cases where user doesn't name the skill but clearly needs it
- Uncommon use cases
- Competitive cases where this skill should win

**Should-not-trigger queries (8-10):**

- Near-misses sharing keywords but needing something different
- Adjacent domains with ambiguous phrasing
- Cases where a naive keyword match would trigger but shouldn't

## Step 2: Review with User

Present the eval set for user review. Let them edit queries, toggle should-trigger, add/remove entries.

## Step 3: Run Optimization Loop

The loop:

1. Split eval set: 60% train, 40% held-out test
2. Evaluate current description (3 runs per query for reliability)
3. Propose improved description based on failures
4. Re-evaluate on both train and test
5. Iterate up to 5 times
6. Select best by TEST score (not train) to avoid overfitting

### How Triggering Works

Skills appear in the AI's available list with name + description. The AI decides whether to consult a skill based on that description. Important: simple one-step queries may not trigger skills regardless of description quality — the AI handles those directly. Eval queries should be substantive enough that consulting a skill would be beneficial.

## Step 4: Apply Result

Take the best description and update SKILL.md frontmatter. Show before/after comparison and report scores.

## Metrics

For each iteration, track:

- Train accuracy (precision, recall)
- Test accuracy (held-out, prevents overfitting)
- Per-query trigger rates
- False positives and false negatives
