# Agent Performance Optimization — Reference

## Phase 1: Commands and data

**Gather performance data:**
```
Use: context-manager
Command: analyze-agent-performance $ARGUMENTS --days 30
```

**Baseline report template:**
```
Performance Baseline:
- Task Success Rate: [X%]
- Average Corrections per Task: [Y]
- Tool Call Efficiency: [Z%]
- User Satisfaction Score: [1-10]
- Average Response Latency: [Xms]
- Token Efficiency Ratio: [X:Y]
```

## Phase 2: Prompt patterns

**Chain-of-thought (prompt-engineer):**
```
Use: prompt-engineer
Technique: chain-of-thought-optimization
```
- Add: "Let's approach this step-by-step..."
- Add: "Before proceeding, verify that..."
- Recursive decomposition for complex tasks; reasoning trace for debugging.

**Few-shot example structure:**
```
Good Example:
Input: [User request]
Reasoning: [Step-by-step thought process]
Output: [Successful response]
Why this works: [Key success factors]

Bad Example:
Input: [Similar request]
Output: [Failed response]
Why this fails: [Specific issues]
Correct approach: [Fixed version]
```

**Constitutional principles (self-correction):**
1. Verify factual accuracy before responding
2. Self-check for potential biases or harmful content
3. Validate output format matches requirements
4. Ensure response completeness
5. Maintain consistency with previous responses

Flow: initial response → self-critique against principles → revision if needed → final validation.

## Phase 3: A/B testing and metrics

**A/B config:**
```
Use: parallel-test-runner
Config:
  - Agent A: Original version
  - Agent B: Improved version
  - Test set: 100 representative tasks
  - Metrics: Success rate, speed, token usage
  - Evaluation: Blind human review + automated scoring
```
- Minimum sample: 100 tasks per variant; 95% confidence (p < 0.05); effect size (e.g. Cohen's d); power analysis.

**Test categories:** Golden path, previously failed (regression), edge cases, stress (multi-step), adversarial, cross-domain.

## Phase 4: Versioning and rollback

**Version format:** `agent-name-v[MAJOR].[MINOR].[PATCH]`  
Example: `customer-support-v2.3.1`  
MAJOR: capability changes; MINOR: prompt/examples; PATCH: fixes.

**Rollback process:** Detect → Alert → Switch to previous stable → Analyze root cause → Fix and re-test before retry.

**Rollback triggers:** Success rate −>10%; critical errors +>5%; complaint spike; cost per task +>20%; safety violations.

---

## Prompt analysis structure (Kiro prompt-engineer)

Treat every prompt as an input to improve. First analyze, then output the optimized prompt.

**Analysis fields:**
- **Simple Change**: yes/no
- **Reasoning**: Does it use chain of thought?
- **Structure**: Well defined?
- **Examples**: Has few-shot examples?
- **Complexity**: 1–5
- **Specificity**: 1–5
- **Prioritization**: Top 1–3 categories to address
- **Conclusion**: Max 30 words on what to change

**Guidelines:** Understand task objectives, goals, requirements, constraints. Minimal changes for simple prompts; enhance complex ones. Encourage reasoning before conclusions. Include high-quality examples with [placeholders] when helpful. Explicit output format (length, syntax, structure). Preserve user content and rubrics.

**Output structure:** [Concise instruction first line] → [Details] → [Steps optional] → [Output Format required] → [Examples optional] → [Notes optional].
