# Grounded Multi-Agent RAG for Healthcare Workflow Automation

CSCI 788 capstone, Rochester Institute of Technology. Student: Ashish Ubale. Instructor: Prof. Leon Reznik.
(Faculty advisor: under discussion; see the weekly status updates.)

## What this is
A pipeline that checks Medicare coverage questions against public CMS policy. Three specialist agents
(Eligibility, Medical Necessity, Documentation) retrieve and cite policy passages, and an orchestrator returns
COVERED / NOT_COVERED / PARTLY_COVERED with the cited passages. A single-agent RAG system is the baseline.
Research question: does splitting the task across agents improve grounded, auditable decisions over one agent?
Success measures (project specification): groundedness, hallucination rate, decision accuracy, latency.

## Data (all public, nothing synthetic)
- Policies: Medicare Benefit Policy Manual ch.1, 6, 7, 8, 10 (cms.gov, unmodified). Indexes: `data/index_v2` (ch.1/7/10, 463 chunks), `data/index_v3` (adds ch.6/8, 692 chunks).
- Cases: real HHS Departmental Appeals Board / Medicare Appeals Council decisions. Patient facts are copied verbatim, outcomes stripped; the answer key is the manual sections the decision cites.
  `data/cases_v2` (22 original), `data/cases_v2_clean` (adjudicator-finding facts removed), `data/cases_v3_heldout_clean` (18 held-out, never used for tuning).
- Raw files: `data/raw`.

## Results so far (details in `results/*.md`)
- Held-out (18 cases, 3 runs): single-agent 11.0/18 (61%), multi-agent 9.7/18 (54%), majority baseline 39% (`results/heldout_m2.md`).
- Original 22 cases, cleaned, 3 runs: multi 16.7 +/- 1.5, single 18.7 +/- 1.5 (`results/repeat_runs_m2.md`).
- Leak audit: removing facts that reveal the outcome did not inflate results (`results/leak_ablation_m2.md`).
- Human review by the author (112 items, `results/review/human_labels.json`): finding support 80% multi-agent vs 67% single-agent, 0% unsupported in either (30 findings each); Cohen's kappa vs AI reviewers 0.35 (finding support), 0.54 (retrieval).
- Negative result: a per-component orchestrator did not help (`results/orchestrator_v2_m2.md`).
- Not yet done: latency in seconds (live backend run), dense-embedding retrieval, LangGraph wrapper, second human reviewer.

## Layout
`rag/` Milestone 2 pipeline, retrieval, review layer; `data/`; `results/`; `src/`, `scripts/`, `tests/` Milestone 1 early prototype (see below).

## Milestone 2 additions
- `rag/retrievers.py`, `rag/eval_retrieval_v2.py`: TF-IDF vs BM25 vs LSA vs hybrids. Chosen on the development cases only; the test cases were scored once. Result: LSA looked better on dev but did not beat TF-IDF on test, so TF-IDF stays (results/retrieval_m2.json). `rag/embed_retriever.py` is an untested dense-embedding option to run on a machine that can download models.
- `rag/review.py`: human-in-the-loop layer. `python3 -m rag.review build` writes results/review/reviewer.html (open in a browser). Four checkpoints: CP4 flagged decisions a person must decide, CP3 whether sampled findings are supported, CP2 whether retrieved passages contain the needed rule, CP1 whether case data matches the source decision. Export the labels as results/review/human_labels.json, then `python3 -m rag.review apply results/review/human_labels.json` (add a second reviewer's file for Cohen's kappa).
- `rag/llm.py`, `rag/run_live.py`: live backends (Anthropic API, local Ollama) with per-call timing; run, then `RUN_DIR=<out> python3 -m rag.pipeline assemble`. Tested only with a mock backend in the sandbox.
- Stability: results/llm_runs_run2 holds a second independent run of the same prompts.
- data/NEXT_BATCH.md lists the next decisions and manual chapter to download.

### AI review results (not human)
`results/review/ai_labels.json` holds labels from three blind Claude subagent reviewers. These are AI judgments, not human verification, and are summarized separately in `results/review/review_summary_ai.json`. The human labels are in `human_labels.json`.

## Archived: early prototype (superseded)
`src/`, `scripts/build_iro_cases.py`, `tests/smoke_cases` and `data/cases` hold an earlier rule-based prototype for facet-joint prior authorization (LCD L38765, Texas IRO decisions). It was replaced by the Medicare coverage pipeline above and is not part of the reported results. Its smoke-test cases are made up and are not results.


### Added Oct 28
- `rag/langgraph_app.py`: LangGraph version of the multi-agent graph (three specialists in parallel, then the orchestrator) with a pluggable backend and per-call timing. Tested with a mock backend only (`results/_mock_harness_test_NOT_RESULTS`, not a result).
- `rag/eval_dense_heldout.py`: TF-IDF vs dense retrieval on the held-out cases (TF-IDF result in `results/retrieval_heldout_m2.txt`; dense needs a local embedding model).
- `results/sensitivity_m2.md`, `results/fault_injection_m2.md`: sensitivity analysis and error-propagation test.
