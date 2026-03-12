# Agentic Evaluation Patterns

Self-improvement through iterative evaluation and refinement. Generate → Evaluate → Critique → Refine → Output.

## When to Apply

- Quality-critical generation: code, reports, analysis requiring high accuracy
- Tasks with clear evaluation criteria or defined success metrics
- Content requiring specific standards: style guides, compliance, formatting

## Core Patterns

### Pattern 1: Basic Reflection

Evaluate own output against criteria, refine if any criterion fails.

- Use structured JSON for critique parsing
- PASS/FAIL per criterion with specific feedback

### Pattern 2: Evaluator-Optimizer

Separate generation and evaluation into distinct roles.

- Generator produces output
- Evaluator scores with rubric (0-1 scale)
- Optimizer refines based on feedback
- Loop until score >= threshold or convergence

### Pattern 3: Rubric-Based Scoring

Weighted multi-dimensional evaluation. Available rubrics:

- `general`: accuracy(25%), completeness(25%), clarity(20%), actionability(15%), coherence(15%)
- `code`: correctness(30%), completeness(20%), readability(15%), efficiency(15%), error_handling(10%), documentation(10%)
- `analysis`: accuracy(25%), depth(25%), evidence(20%), clarity(15%), actionability(15%)
- `prd`: completeness(25%), clarity(20%), feasibility(20%), user_focus(15%), measurability(10%), prioritization(10%)
- `architecture`: scalability(20%), maintainability(20%), correctness(20%), completeness(15%), security(15%), cost_efficiency(10%)

## Convergence Detection

Stop iterating when:

- Score improvement < min_delta for 2+ consecutive rounds (stagnation)
- Score oscillates (up-down-up pattern with 2+ sign changes)
- Score >= threshold (approved)
- Max iterations reached

## Best Practices

- Set max iterations 3-5 to prevent infinite loops
- Use 0.8 as default score threshold
- Log full iteration history for debugging
- Always keep best output (not necessarily last)
- Detect task type automatically for rubric selection
- Use structured JSON output for reliable evaluation parsing
