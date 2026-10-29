"""LangGraph implementation of the multi-agent system (the project specification names LangGraph).
Graph per case:  START -> {eligibility, necessity, documentation} (parallel) -> orchestrator -> END
Same prompts as the saved-prompt runs (RUN_DIR/prompts_*.json), pluggable backend from rag/llm.py.
  CASES_DIR=data/cases_v3_heldout_clean INDEX_DIR=data/index_v3 RUN_DIR=results/heldout_r1 \
  python3 -m rag.langgraph_app --backend mock --out results/langgraph_mock --limit 3
Backends: mock (harness test only, NOT a result), ollama, anthropic. Writes resp_*.json + timing.json,
then:  RUN_DIR=<out> python3 -m rag.pipeline assemble   (copy retrieved.json is done here)."""
import argparse, json, os, pathlib, shutil, time
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END
from rag import llm

class S(TypedDict, total=False):
    case_id: str
    elig: dict; nec: dict; doc: dict; orch: dict
    t_elig: float; t_nec: float; t_doc: float; t_orch: float

def build(backend, prompts, orch_prompt):
    def run(role):
        def node(s):
            p = next(x["prompt"] for x in prompts[role] if x["case_id"] == s["case_id"])
            try:
                text, sec = backend.call(p); d = llm.extract_json(text)
            except Exception as e:
                d, sec = {"verdict": "UNKNOWN", "findings": [], "error": str(e)}, 0.0
            d["case_id"] = s["case_id"]
            return {role: d, f"t_{role}": sec}
        return node
    def orch(s):
        p = orch_prompt(s)
        try:
            text, sec = backend.call(p); d = llm.extract_json(text)
        except Exception as e:
            d, sec = {"decision": "NOT_COVERED", "reason": f"ERROR {e}", "passage_ids": []}, 0.0
        d["case_id"] = s["case_id"]
        return {"orch": d, "t_orch": sec}
    g = StateGraph(S)
    for r in ("elig", "nec", "doc"):
        g.add_node(r, run(r)); g.add_edge(START, r); g.add_edge(r, "orch")   # fan-out, then join
    g.add_node("orch", orch); g.add_edge("orch", END)
    return g.compile()

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--backend", required=True); ap.add_argument("--model"); ap.add_argument("--out", required=True); ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    from rag import pipeline as P                       # uses CASES_DIR / INDEX_DIR / RUN_DIR env vars
    src = P.RUN; out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    shutil.copy(src / "retrieved.json", out / "retrieved.json")
    prompts = {r: json.load(open(src / f"prompts_{r}.json")) for r in ("elig", "nec", "doc", "base")}
    def orch_prompt(s):
        blocks = ""
        for nm, k in (("Eligibility Agent", "elig"), ("Medical Necessity Agent", "nec"), ("Documentation Agent", "doc")):
            r = s[k]; blocks += f"<agent name=\"{nm}\" verdict=\"{r.get('verdict','UNKNOWN')}\">\n" + "\n".join(f"- {f['claim']} (source passage {f['passage_id']}: \"{f['quote']}\")" for f in r.get("findings", [])) + "\n</agent>\n"
        return ("You are the Orchestrator in a Medicare coverage-review system. Three specialist agents have reviewed the case. Combine their findings into one decision. "
                "Use ONLY the agents' findings and the case facts; do not use outside knowledge. Cite the passage ids your decision relies on. COVERED = coverage is supported; NOT_COVERED = it is not; PARTLY_COVERED = part of the service or period is covered and part is not.\n\n"
                f"<case_facts>\n{P.facts_text(P.cases[s['case_id']])}\n</case_facts>\n\n{blocks}\n"
                'Reply with JSON only: {"decision": "COVERED" | "NOT_COVERED" | "PARTLY_COVERED", "reason": "one or two sentences", "passage_ids": [<int>, ...]}')
    be = llm.get(a.backend, a.model); graph = build(be, prompts, orch_prompt)
    ids = [x["case_id"] for x in prompts["elig"]][: a.limit]
    R = {k: [] for k in ("elig", "nec", "doc", "base", "orch")}; T = {}
    for cid in ids:
        t0 = time.perf_counter(); s = graph.invoke({"case_id": cid}); wall = time.perf_counter() - t0
        for k in ("elig", "nec", "doc", "orch"): R[k].append(s[k])
        b = next(x["prompt"] for x in prompts["base"] if x["case_id"] == cid); t1 = time.perf_counter()
        try: text, _ = be.call(b); d = llm.extract_json(text)
        except Exception as e: d = {"decision": "NOT_COVERED", "reason": f"ERROR {e}", "findings": []}
        d["case_id"] = cid; R["base"].append(d)
        T[cid] = {"multi_graph_wall_s": wall, "single_s": time.perf_counter() - t1, **{k: s[k] for k in ("t_elig", "t_nec", "t_doc", "t_orch")}}
    for k, v in R.items(): json.dump(v, open(out / f"resp_{k}.json", "w"), indent=1)
    json.dump({"backend": be.name, "per_case": T}, open(out / "timing.json", "w"), indent=1)
    mw = [t["multi_graph_wall_s"] for t in T.values()]; sw = [t["single_s"] for t in T.values()]
    print(f"{be.name}: cases={len(ids)} multi(LangGraph, parallel specialists) mean {sum(mw)/len(mw):.2f}s | single mean {sum(sw)/len(sw):.2f}s")
if __name__ == "__main__": main()
