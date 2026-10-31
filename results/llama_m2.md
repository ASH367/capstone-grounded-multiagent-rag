# LangGraph + Ollama llama3.1:8b, held-out 18 cases, 1 run (results/llama_r1)

Fully local: no Claude calls. Same prompts and retrieval (index_v3) as the other runs.

| System | Correct of 18 | Predictions |
|---|---|---|
| Multi-agent (LangGraph) | 8 (44%) | 16 COVERED, 2 NOT_COVERED, 0 PARTLY |
| Single-agent | 7 (39%) | 17 COVERED, 1 UNKNOWN |
| Always-COVERED baseline | 7 (39%) | - |

Reading: llama3.1:8b says COVERED for almost every case, so both systems sit at the majority baseline; the 8 vs 7 gap is one case and not meaningful. It never predicted PARTLY_COVERED correctly. No call errors. 1 of 258 findings was malformed (a string instead of an object; rag.pipeline assemble crashes on it, so accuracy was computed directly).
Latency (18 cases): multi 226.7 s, single 67.9 s per case (3.3x).
Caveat: one run, small model; this shows the pipeline runs end to end locally, not a model comparison.
