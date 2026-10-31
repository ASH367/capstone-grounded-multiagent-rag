# Verifier agent, Milestone 2

A Verifier agent reads each finding (claim, quoted case fact, quoted policy text) and labels it SUPPORTED / PARTLY / NOT_SUPPORTED. It sees nothing else (no human labels, no decision).
Files: results/verifier/.

1. Calibration against my human labels (the 60 CP3 findings): agreement 73%, Cohen's kappa 0.45 (the earlier AI reviewers: 0.35). The verifier is stricter than I was: of the 44 findings I called SUPPORTED, it called 13 PARTLY. It almost never says NOT_SUPPORTED.
2. Same 60 findings, share fully SUPPORTED:
   - multi-agent: human 80%, verifier 53%
   - single-agent: human 67%, verifier 57%
3. Held-out findings (3 runs, 375 findings): multi-agent 56% SUPPORTED (257 findings), single-agent 57% (118). NOT_SUPPORTED about 1 to 2% for both.
4. As an abstention signal: for multi-agent, decisions where at least half the findings were verified SUPPORTED were right 58% of the time versus 44% otherwise; for single-agent the pattern reversed (59% vs 67%). Not a reliable signal.

Reading
- The earlier "multi-agent is more grounded" result (80% vs 67%) came from one human reader on 30 findings per system. A stricter AI verifier on the same findings, and on 375 held-out findings, shows no difference (about 55% vs 57%).
- Safest claim: both systems rarely invent unsupported claims (about 1 to 2% NOT_SUPPORTED by the verifier, 0% by me), and a multi-agent groundedness advantage is not confirmed.
- Multi-agent's remaining case is traceability (per-component findings with citations), not higher accuracy or higher support.
