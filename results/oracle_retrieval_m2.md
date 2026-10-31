# Oracle-retrieval ablation, Milestone 2

Question: is retrieval the bottleneck? Give the system the manual sections the Council actually cited (capped at 12 passages per case, ranked by TF-IDF to the facts) instead of retrieved passages, and compare with the normal run on the same cases.
Cases: 10 held-out cases that have a manual-section key present in the index (gr excluded: its cited section is not in the index). Three runs each. Files: results/oracle_r1..r3, rag/oracle.py.

```
cases 10
multi: retrieved [7, 8, 6] mean 7.0/10 (70%) | gold sections [7, 8, 6] mean 7.0/10 (70%)
single: retrieved [9, 7, 7] mean 7.7/10 (77%) | gold sections [6, 7, 7] mean 6.7/10 (67%)
```

Reading
- Perfect sections did not help: multi-agent 70% to 70%, single-agent 77% to 67% (differences within run noise at n=10).
- So retrieval is not what limits accuracy here. The errors come from reasoning over the facts and from label ambiguity (especially PARTLY_COVERED), not from missing policy text.
- Consequence for the capstone: improving retrieval (dense or hybrid) will mostly help traceability (finding the right citation), not decision accuracy.
- Caveats: n=10; the oracle gives the sections the Council cited, which can include sections about liability or procedure that distract; three runs of the same prompts.
