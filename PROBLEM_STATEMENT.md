# PROBLEM STATEMENT (anchor: re-read before proposing any experiment)

Source of truth: Ashish_Ubale_Project_Specification.pdf (quoted, not paraphrased). The earlier "completeness checker" reframing is NOT the problem statement; it is a secondary finding (see bottom).

## Spec: the goal (verbatim)
"Build a multi-agent RAG system that produces healthcare workflow decisions where every claim is explicitly traceable to a retrieved source document."

## Spec: the gap (verbatim)
"Few systems combine agent-level task decomposition with explicit, measured grounding evaluation in a healthcare workflow setting."
Connected problem: "grounding is assumed, not measured."

## Spec: final deliverable (verbatim)
"An end-to-end multi-agent RAG system (LangGraph) producing structured, cited decisions across eligibility, medical necessity, and documentation checks."

## Spec: four evaluation dimensions (verbatim definitions)
1. Groundedness: "% of output claims traceable to a retrieved source passage"
2. Hallucination Rate: "% of claims with no supporting evidence in retrieved text"
3. Decision Accuracy: "Agreement with known-correct outcomes on held-out cases"
4. Latency: "End-to-end response time vs. a single-agent baseline"
Timeline also lists: "Build RAG ingestion pipeline and single-agent baseline" (early Oct) and "compare against baseline" (mid Nov).

## Known deviations from the spec (disclose in every writeup)
- Spec says cases are "synthetically generated". We use real, public Medicare Appeals Council decisions (de-identified), with their outcomes as ground truth. n is small (18 held-out).
- Policy source: Medicare Benefit Policy Manual ch.1, 6, 7, 8, 10 (spec says CMS coverage/prior-auth guidelines).
- Case facts are the Council's summaries, not original clinical records; no public prior-authorization requests exist.

## Status against the four dimensions (see results/EXPERIMENT_LOG.md)
- Groundedness / hallucination: mechanical exact-quote citation check. Sonnet 5.5: 98-100% valid; weaker models 53-80%. Gap: validity of quote != quote supports claim (verifier agent kappa 0.45 vs humans).
- Decision accuracy: multi 50-54%, single 56-61% (guess baseline 39%).
- Latency: multi slower (Sonnet 14 s vs 10 s; llama 8B about 3.3x).

## Secondary finding (not the problem statement)
Criteria-tree checker: model flags missing evidence correctly when a cited fact is removed (20 detected, 9 redundant, 0 unsupported, n=29), but 78% of leaves are NO_INFORMATION because case facts are thin.
