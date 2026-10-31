# Abstention and selective prediction, Milestone 2

Question: can the system say "I'm not sure" in a way that actually separates right from wrong decisions?
Signal tested: run-to-run agreement (three independent runs per case). Abstain when the three runs do not all give the same decision. Also tested: number of specialist agents that answered UNKNOWN.
Data: 18 held-out cases and 22 cleaned development cases, three runs each (files: results/heldout_r*/decisions.json, results/llm_runs_clean*/decisions.json). No new model calls.

| Set | System | Majority-vote accuracy, all cases | Accuracy when 3 runs agree | Accuracy when runs split |
|---|---|---|---|---|
| Held-out 18 | multi | 56% | 57% (14 cases) | 50% (4) |
| Held-out 18 | single | 61% | 64% (14) | 50% (4) |
| Dev 22 | multi | 77% | 83% (18) | 50% (4) |
| Dev 22 | single | 86% | 89% (19) | 67% (3) |
| Pooled 40 | multi | 68% | 72% (32) | 50% (8) |
| Pooled 40 | single | 75% | 79% (33) | 57% (7) |

Findings
- Run agreement is a real but weak abstention signal: abstaining on about 20% of cases (the ones where runs split) raises multi-agent accuracy from 68% to 72% and single-agent from 75% to 79%. Split cases are right about half the time.
- The count of UNKNOWN specialist verdicts did not predict correctness (e.g. held-out: 1 UNKNOWN 33% correct, 3 UNKNOWN 57%).
- Multi-agent has no abstention advantage over single-agent here.
- Caveat: small numbers (8 and 7 split cases). Treat as indicative. Abstaining by run agreement costs three model runs per decision, so it is a cost trade, not a free signal.
- Not yet tried: asking the model for a confidence score, or a verifier agent's support rating as the abstention signal (see verifier experiment).
