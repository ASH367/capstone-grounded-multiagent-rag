# Leakage audit and ablation (Milestone 2)

Trigger: human data check (CP1) found case "facts" that are an earlier adjudicator's findings (e.g. "the record did not indicate...", "the QIC noted...").
Audit: a Claude reviewer (AI, not human) classified all 151 facts: 110 patient/claim, 19 party argument, 7 adjudicator finding, 15 mixed. 14 of 22 cases had at least one leaking fact (results/review/leak_audit.json).
Ablation: the 22 flagged facts (adjudicator-finding + mixed) were dropped entirely (data/cases_v2_clean) and the full pipeline was rerun (results/llm_runs_clean).

| Decision agreement | Original | Cleaned |
|---|---|---|
| All 22, multi-agent | 0.773 (17) | 0.818 (18) |
| All 22, single-agent | 0.773 (17) | 0.864 (19) |
| Test 10, multi / single | 0.80 / 0.90 | 0.70 / 0.80 |
| Dev 12, multi / single | 0.75 / 0.667 | 0.917 / 0.917 |

Reading: removing the leaking sentences did not lower accuracy, so there is no evidence the leaks inflated the results. Multi-agent still shows no advantage.
Caveats: one run per condition; run-to-run noise exists (state_of_vt changed prediction with identical facts), so differences of 1-2 cases are not meaningful. The audit labels are AI judgments, partly checked by the human CP1 review. Dropping whole facts also removes some legitimate content in MIXED facts.
Cleaned multi-agent citation validity: 164/164 findings mechanically valid.
