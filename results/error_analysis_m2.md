# Error analysis (Milestone 2)

Source: results/milestone1_decisions.json, data/cases_v2. Both systems: 17/22 correct (0.773). Majority-class baseline 0.50.

## Where each system is wrong
- Both wrong (4): estate_gbr, m-11-1559, m_12_809, state_of_vt.
- Multi-agent only wrong: eagle_air_med. Single-agent only wrong: gold_cross_ambulance. The tie hides different errors.
- Prediction mix vs reference (COVERED / NOT_COVERED / PARTLY): reference 11/8/3, multi 11/10/1, single 10/10/2. Both under-predict PARTLY_COVERED and over-predict NOT_COVERED.
- Citations: multi-agent 96.9% mechanically valid (161 findings), single-agent 100% (64 findings).

## Failure categories (6 distinct wrong cases)
1. Policy not in the corpus (3): m-11-1559 and m_12_809 cite MBPM ch.6 / SNF rules (corpus has ch.1, 7, 10 only); state_of_vt turns on advance-notice liability rules outside the manuals. The retriever cannot find rules that were never indexed. Fix: add ch.8 and other cited chapters (data/NEXT_BATCH.md).
2. Partial coverage collapsed to a yes/no (eagle_air_med, state_of_vt): the decision was split (mileage limit, visit-level skilled care) and the system returned one verdict. Fix: have agents report per-component coverage and let the orchestrator decide PARTLY explicitly.
3. Judgment calls (estate_gbr, gold_cross_ambulance): close reads of "nearest appropriate facility" and medical necessity; agents returned UNKNOWN or disagreed. These are the cases the human gate should catch.

## Caveats
- Based on 22 cases; categories are my reading of the case notes and agent verdicts and are not yet human-verified.
- Reference outcomes come from decisions applying 2009-2012 policy.
