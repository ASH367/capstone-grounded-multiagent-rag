# Per-component orchestrator experiment (Milestone 2)

Change: the orchestrator first splits the claim into components (e.g. transport vs extra mileage), decides each, then returns COVERED / NOT_COVERED / PARTLY_COVERED (ORCH_V2=1 in rag/pipeline.py). Specialist and baseline outputs unchanged; three runs (results/orch_v2a,b,c) vs the original orchestrator (results/llm_runs_clean*).

| Multi-agent correct of 22 | Run A | Run B | Run C | Mean |
|---|---|---|---|---|
| Original orchestrator | 18 | 17 | 15 | 16.7 |
| Per-component orchestrator | 17 | 17 | 17 | 17.0 |
| Single-agent (reference) | 19 | 20 | 17 | 18.7 |

Result: no meaningful gain. PARTLY_COVERED predictions went from 1 to 0 across 66 case-runs, so the intended fix did not work. The variance across runs shrank (the gold_cross and kaweah flips disappeared), but 0.3 cases is within noise.
Interpretation: the PARTLY failures originate upstream. For eagle_air_med all three specialists return DOES_NOT_SUPPORT for the whole claim, so the orchestrator has no component-level evidence to split. Single-agent sees passages and facts directly and does return PARTLY.
Caveat: the change was chosen after inspecting errors on these same 22 cases, and still did not help, so this is not an overfitting concern; it is a negative result.
Next hypothesis: have specialists report per-component verdicts.
