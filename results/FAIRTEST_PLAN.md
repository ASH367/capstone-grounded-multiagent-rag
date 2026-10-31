# Fair test on the Council decisions (built Oct 30, 2026)

## Two problems found
1. **The answer key was unfair.** 5 of the 18 held-out cases (baptist_health_care, conn_dept_social_services, connecticut11, ny, stfrances_memorial) were decided on liability, notice or procedure, not on a Medicare coverage criterion. Coverage-only key and merits filter: `data/council_issue_tags.json`. Both keys are always reported (`scripts/score_fair.py`).
2. **The system saw 9-10% of each decision**, and Council-curated sentences were in it. `rag/fairtest.py` rebuilds the cases from the raw decisions: everything except the Council's verdict, reasoning, law text, ALJ recital and procedure/liability lines, every sentence an exact copy.

## The arms (each case, each set: `data/cases_v4/<arm>_<dev|held>/`)
| arm | contains | use |
|---|---|---|
| A_strict | dated / numbered / record-sourced facts + party submissions | leak-controlled floor |
| B_gaps | A + "record does not show..." statements | |
| C_prior | B + contractor / QIC denial narrative (what the client submitted and got rejected) | |
| D_wide | C + weaker facts + record-report sentences the Council quotes | **primary** (closest to "everything but verdict and reasoning") |
| E_aljfacts | D + dated/numbered narrative from ALJ-recital paragraphs | exploratory, built after seeing held-out (`scripts/build_arm_E.py`) |

## Protocol (fixed before any model run)
- Rules tuned on the 22 dev decisions only, hashed (`results/fairtest_freeze.json`), applied to the 18 held-out once. One amendment afterward (v1.1, order-language cue) is recorded in that file.
- Eligible case = merits case (coverage key) **and** `evidence_ok` (strict arm >= 60 words and wide arm >= 150 words). Dev 20 (11 COVERED, 8 NOT_COVERED, 1 PARTLY); held-out 11 (7 COVERED, 2 NOT_COVERED, 2 PARTLY). Pooled 31, majority 58%.
- Primary comparison: single vs multi on D_wide, exact McNemar and bootstrap CI. Sensitivity: A_strict (and E_aljfacts).
- **Blind probe** (`scripts/blind_probe.py`): same facts, no policy text. That score is the leak floor; the system adds value only above it.
- Dev numbers are not clean for the system (earlier prompt/retrieval work used dev); held-out is the clean read. Report both, pooled only for power.

## Run
```
export LLM_API_KEY=...           # and LLM_BASE_URL=https://openrouter.ai/api/v1 if you use OpenRouter
bash scripts/run_fair_eval.sh                       # held-out: D_wide + A_strict, one run each, with blind probe
ARMS="D_wide" SETS="held dev" REPS=3 bash scripts/run_fair_eval.sh
```
Outputs `results/fair/<arm>_<set>/score.txt` and `probe_score.txt`.

## What this can and cannot show
- n is 11 (held-out) to 31 (pooled). A 10-point gap needs about 155-233 paired cases; with 31 only gaps of about 25 points or more are detectable. Report effect sizes with intervals, not significance claims.
- Denial cases are evidence-poor in non-reasoning text (the Council adopts the ALJ or rests on a legal point), so the testable set leans COVERED.
- Residual leakage: the Council chooses which record sentences to recite. No rule removes that; the blind probe measures it.
- Tagging is rules, checked against the earlier AI leak audit (A: 5/22 dev and 1/10 held-out audited-leak facts still present, mostly curated record statements or word-overlap false positives; D adds earlier-level denials) and by reading dev samples. A model-based second opinion is not yet run.

## Tell Prof. Homan
Label change (coverage-only key, both reported); the held-out restriction was made after aggregate results were known; held-out sentences were read during audits; arm E and word floors are exploratory; rules frozen on dev, one amendment disclosed.
