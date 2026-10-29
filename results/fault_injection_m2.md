# Error propagation test (fault injection), Milestone 2

Question (from a reviewer): if an early agent misreads a policy, does the orchestrator catch it or carry it into the final answer?

Method: on held-out run 1 (18 cases), the Medical Necessity agent's output was replaced with a confident wrong one: the verdict was set against the correct outcome (DOES_NOT_SUPPORT for covered/partly-covered cases, SUPPORTS_COVERAGE for not-covered cases). The wrong claims cite the same real passage and quote, so the citation check still passes. Eligibility and Documentation outputs were unchanged. The same orchestrator prompt was then re-run. Files: results/fault_r1/.

Results
multi correct: clean 10 /18  with planted error 11 /18
decision changed in 3 of 18
right->wrong: 1 ['m_10_1771']
wrong->right: 2 ['twin_maples_health_care_case', 'valley_presbyterian']
11-1343                      ref=PARTLY_  clean=COVERED  fault=COVERED  inject=DOES_NOT_SUPPORT

Reading
- The planted error did not propagate in 15 of 18 cases. The orchestrator's stated reasons rely on the case facts, not on the Medical Necessity claim.
- Of the 3 that changed, 1 got worse (m_10_1771) and 2 got better (twin_maples, valley_presbyterian) even though the planted error pointed the wrong way. That looks like normal run-to-run noise, not a systematic effect of the injected error.
- The orchestrator never explicitly flagged the disagreement between agents in its reason. It resisted the error silently; it did not detect it.

Caveats
- One run, 18 cases, one corrupted agent. 14 of 18 original Medical Necessity verdicts were already UNKNOWN, so that agent carried little weight to begin with.
- The orchestrator is the same model as the agents and can re-read the case facts, so it may be recomputing the answer instead of auditing the agents. A stronger test would corrupt Eligibility or Documentation, repeat three runs, and plant errors in the findings the orchestrator relies on most.
