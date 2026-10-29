# Latency, Milestone 2

Setup: LangGraph graph (rag/langgraph_app.py), local Ollama llama3.1:8b on a MacBook Air, first 5 held-out cases, no call errors. Files: results/langgraph_ollama/.

| System | Mean seconds per case |
|---|---|
| Single-agent (1 call) | 75 |
| Multi-agent, specialists run in parallel by LangGraph (3 calls at once + orchestrator) | 242 (3.2x single) |
| Multi-agent if the 4 calls ran one after another (sum of call times) | 465 (6.2x single) |

Notes
- Multi-agent makes 4 model calls per case versus 1, so it is slower by construction.
- Parallelism helps only partly here (242 s vs 465 s) because all three specialists share one laptop's compute. Separate API calls to a hosted model would run truly in parallel, so wall-clock time would be closer to the slowest specialist plus the orchestrator.
- Small model, 5 cases, one machine: absolute numbers are specific to this setup. The ratio (about 3x) is the finding. Accuracy of this llama run was not evaluated and is not claimed.
