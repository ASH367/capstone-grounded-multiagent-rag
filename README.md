# Grounded Multi-Agent RAG for Healthcare Workflow Automation - Milestone 1

CSCI 788 capstone (RIT). Advisor: Prof. Xumin Liu.

## What this is
A pipeline that takes a prior-authorization request for facet joint interventions and returns a
decision in CMS vocabulary (provisional affirmation / partial affirmation / non-affirmation),
where every finding cites the exact policy passage it relies on.

## Data (all public; nothing in the evaluation set is written by us)
- **Policies:** CMS OPD Prior Authorization FAQ (Nov 14, 2024) and LCD L38765 *Facet Joint Interventions for Pain Management*
  (v27), unmodified. See `data/policies/SOURCES.md`.
- **Cases (15):** 14 real, name-redacted Texas Dept. of Insurance Independent Review Organization decisions on facet /
  medial branch block / radiofrequency procedures (each with the real outcome, upheld or overturned) + 1 open-access
  published case report (PMC13276552). See `data/cases/MAPPING_NOTES.md`.
- **Code smoke tests (made up, NOT results):** `tests/smoke_cases/`.

## Pipeline
1. `src/ingest.py` - chunks the two documents into 85 citable units
   (62 FAQ questions, 23 LCD criterion/limitation blocks) -> `data/index/chunks.json`.
2. `src/retriever.py` - TF-IDF + cosine similarity baseline, restricted per agent to its document.
3. `src/agents.py` - Eligibility (FAQ), Medical Necessity (LCD), Documentation (LCD). Each criterion is
   evaluated by explicit rules on the case fields and cited with the retrieved chunk.
4. `src/orchestrator.py` - aggregates per-service decisions (incl. the LCD 1-2 level limit) -> `results/milestone1_output.json`.

Run: `pip install -r requirements.txt && python src/ingest.py && python src/orchestrator.py`

## Milestone 1 results (15 real cases)
| Measure | Result |
|---|---|
| Citations verified present in the index | 172/172 |
| Retrieval hit@1 / hit@3 vs hand-labelled gold chunk | 172/172 / 172/172 (queries are close to policy wording; optimistic) |
| System decision | 14 NON-AFFIRMATION, 1 INSUFFICIENT INFORMATION |
| vs. real IRO outcome | upheld denials: 9/9 non-affirmed; overturned denials: 0/5 affirmed |
| Cases where the reviewer cited radiculopathy (4) | system hard-failed the radiculopathy criterion in 4/4 |

What the results mean
- The system is far stricter than the real reviewers: it fails 13/14 cases on "no non-facet pathology", because the
  rule treats any listed disc finding as disqualifying. The LCD names fracture/tumor/infection/significant deformity.
  That rule is too blunt. It was NOT tuned to these labels (that would overfit); fixing it needs a held-out split (Milestone 2).
- Redacted/summarised records leave most criteria UNKNOWN (e.g., 14/14 have no disability scale, no pain duration).
- The reviewers used ODG/ACOEM, not LCD L38765, so agreement with the outcome is an external check, not LCD accuracy.
- The 5/5 and 72/72 numbers from the made-up smoke tests are not reported as results.

## Honest limitations
- Decisions are rule-based and extractive; no LLM generates text yet.
- Retrieval queries are written close to the policy wording, so retrieval scores are optimistic.
- Case facts come from decision summaries, not full medical records; no case has an LCD-based label yet.
- 15 cases, no held-out split, rules not tuned. This is a baseline, not an accuracy claim.

## Milestone 2 plan
LangGraph orchestration; LLM-generated rationales under the same citation contract; larger,
harder case set (incl. adversarial queries not phrased like the policy); dense-embedding retrieval vs
this TF-IDF baseline; single-agent vs multi-agent comparison on groundedness, hallucination rate,
decision accuracy and latency.


## Milestone 2 additions
- `rag/retrievers.py`, `rag/eval_retrieval_v2.py`: TF-IDF vs BM25 vs LSA vs hybrids. Chosen on the development cases only; the test cases were scored once. Result: LSA looked better on dev but did not beat TF-IDF on test, so TF-IDF stays (results/retrieval_m2.json). `rag/embed_retriever.py` is an untested dense-embedding option to run on a machine that can download models.
- `rag/review.py`: human-in-the-loop layer. `python3 -m rag.review build` writes results/review/reviewer.html (open in a browser). Four checkpoints: CP4 flagged decisions a person must decide, CP3 whether sampled findings are supported, CP2 whether retrieved passages contain the needed rule, CP1 whether case data matches the source decision. Export the labels as results/review/human_labels.json, then `python3 -m rag.review apply results/review/human_labels.json` (add a second reviewer's file for Cohen's kappa).
- `rag/llm.py`, `rag/run_live.py`: live backends (Anthropic API, local Ollama) with per-call timing; run, then `RUN_DIR=<out> python3 -m rag.pipeline assemble`. Tested only with a mock backend in the sandbox.
- Stability: results/llm_runs_run2 holds a second independent run of the same prompts.
- data/NEXT_BATCH.md lists the next decisions and manual chapter to download.

### AI review results (not human)
`results/review/ai_labels.json` holds labels from three blind Claude subagent reviewers (A: decisions and retrieval, B: finding support, C: data fidelity). These are AI judgments, not human verification, and `review_summary.json` says so. Treat them as a stand-in until a person labels `results/review/reviewer.html`. The same model family produced the outputs, so the numbers may be optimistic. CP1 did not re-check outcome labels.
