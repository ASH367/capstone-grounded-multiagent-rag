# Alternative agent designs vs current multi-agent and single-agent (held-out, 18 cases, 3 runs each)

Metric: exact coverage-decision accuracy (COVERED / NOT_COVERED / PARTLY_COVERED). Same retrieval index (index_v3), same cases.

| Design | Calls/case | Correct per run (of 18) | Mean | SD |
|---|---|---|---|---|
| Single-agent RAG | 1 | 12, 11, 10 | 11.0 (61%) | 0.8 |
| C: generate -> verify -> revise | 3 | 12, 11, 10 | 11.0 (61%) | 0.8 |
| D: majority vote of 3 single runs (compute-matched) | 3 | - | 11 (61%) | - |
| Current multi-agent (3 specialists + orchestrator) | 4 | 10, 11, 8 | 9.7 (54%) | 1.2 |
| B: advocate / skeptic + judge | 3 | 9, 7, 6 | 7.3 (41%) | 1.2 |
| A: planner + component agents + rule | ~2.7 + plan | 8, 9, 6 | 7.7 (43%) | 1.2 |

Guess baseline: 39%.

Findings
- No multi-agent design beat single-agent. C only matched it, and its revise step changed few decisions, so it adds cost without gain.
- A (rule-based aggregation) lands near the guess baseline (39%): requiring all components to agree pushes most cases to PARTLY_COVERED.
- B: advocate and skeptic disagreed on 7-8 of 18 cases per run, but the judge did not resolve those well (41%).
- Majority vote of single runs (D) equals single-agent at the same compute as the 3-call designs.
- n=18, SD about 1 case per run: differences of 1-2 cases are noise; the gaps for A and B (3-4 cases) are larger than run-to-run spread.
- Caveat: roles were played by Claude subagents via files; some subagents used many tool calls, so strict isolation between roles is not guaranteed.
