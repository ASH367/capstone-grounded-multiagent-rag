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
                d, sec = llm.call_json(backend, p)
            except Exception as e:
                d, sec = {"verdict": "UNKNOWN", "findings": [], "error": str(e)}, 0.0
            d["case_id"] = s["case_id"]
            return {role: d, f"t_{role}": sec}
        return node
    def orch(s):
        p = orch_prompt(s)
        try:
            d, sec = llm.call_json(backend, p)
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
    ap = argparse.ArgumentParser(); ap.add_argument("--backend", required=True); ap.add_argument("--model"); ap.add_argument("--out", required=True); ap.add_argument("--limit", type=int); ap.add_argument("--redo-errors", action="store_true", help="re-run ONLY cases whose saved responses contain an error/fallback, and patch them into the existing resp_*.json")
    a = ap.parse_args()
    from rag import pipeline as P                       # uses CASES_DIR / INDEX_DIR / RUN_DIR env vars
    src = P.RUN; out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if src.resolve() != out.resolve(): shutil.copy(src / "retrieved.json", out / "retrieved.json")
    prompts = {r: json.load(open(src / f"prompts_{r}.json")) for r in ("elig", "nec", "doc", "base")}
    def orch_prompt(s):
        blocks = ""
        for nm, k in (("Eligibility Agent", "elig"), ("Medical Necessity Agent", "nec"), ("Documentation Agent", "doc")):
            r = s[k]; blocks += f"<agent name=\"{nm}\" verdict=\"{r.get('verdict','UNKNOWN')}\">\n" + "\n".join(f"- {f.get('claim','')} (source passage {f.get('passage_id')}: \"{f.get('quote','')}\")" for f in r.get("findings", []) if isinstance(f, dict)) + "\n</agent>\n"
        return ("You are the Orchestrator in a Medicare coverage-review system. Three specialist agents have reviewed the case. Combine their findings into one decision. "
                "Use ONLY the agents' findings and the case facts; do not use outside knowledge. Cite the passage ids your decision relies on. COVERED = coverage is supported; NOT_COVERED = it is not; PARTLY_COVERED = part of the service or period is covered and part is not.\n\n"
                f"<case_facts>\n{P.facts_text(P.cases[s['case_id']])}\n</case_facts>\n\n{blocks}\n"
                'Reply with JSON only: {"decision": "COVERED" | "NOT_COVERED" | "PARTLY_COVERED", "reason": "one or two sentences", "passage_ids": [<int>, ...]}')
    be = llm.get(a.backend, a.model); graph = build(be, prompts, orch_prompt)
    ids = [x["case_id"] for x in prompts["elig"]][: a.limit]
    old = {}
    if a.redo_errors:
        old = {k: json.load(open(out / f"resp_{k}.json")) for k in ("elig", "nec", "doc", "base", "orch")}
        bad = lambda x: ("error" in x) or str(x.get("reason", "")).startswith("ERROR")
        ids = sorted({x["case_id"] for k in old for x in old[k] if bad(x)}, key=ids.index)
        print(f"redo-errors: {len(ids)} cases to re-run: {ids}")
    R = {k: [] for k in ("elig", "nec", "doc", "base", "orch")}; T = {}
    for cid in ids:
        t0 = time.perf_counter(); s = graph.invoke({"case_id": cid}); wall = time.perf_counter() - t0
        for k in ("elig", "nec", "doc", "orch"): R[k].append(s[k])
        b = next(x["prompt"] for x in prompts["base"] if x["case_id"] == cid); t1 = time.perf_counter()
        try: d, _ = llm.call_json(be, b)
        except Exception as e: d = {"decision": "NOT_COVERED", "reason": f"ERROR {e}", "findings": []}
        d["case_id"] = cid; R["base"].append(d)
        T[cid] = {"multi_graph_wall_s": wall, "single_s": time.perf_counter() - t1, **{k: s[k] for k in ("t_elig", "t_nec", "t_doc", "t_orch")}}
    if a.redo_errors:
        for k in R:
            failed = lambda x: ("error" in x) or str(x.get("reason", "")).startswith("ERROR")
            new = {x["case_id"]: x for x in R[k] if not failed(x)}; R[k] = [new.get(x["case_id"], x) for x in old[k]]   # keep the old entry if the re-run failed again
    for k, v in R.items(): json.dump(v, open(out / f"resp_{k}.json", "w"), indent=1)
    if not a.redo_errors: json.dump({"backend": be.name, "per_case": T}, open(out / "timing.json", "w"), indent=1)
    print(f"spend this process: ${llm.Spend.usd:.2f} over {llm.Spend.calls} calls")
    if not T: print("nothing to do"); return
    mw = [t["multi_graph_wall_s"] for t in T.values()]; sw = [t["single_s"] for t in T.values()]
    print(f"{be.name}: cases={len(ids)} multi(LangGraph, parallel specialists) mean {sum(mw)/len(mw):.2f}s | single mean {sum(sw)/len(sw):.2f}s")
if __name__ == "__main__": main()
