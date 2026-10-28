"""Run the full pipeline live and time it.  Example:
   ANTHROPIC_API_KEY=... python3 -m rag.run_live --backend anthropic --out results/live_anthropic
   python3 -m rag.run_live --backend ollama --model llama3.1:8b --out results/live_ollama
Writes resp_*.json (same format as the saved-prompt runs) + timing.json, then run:  RUN_DIR=<out> python3 -m rag.pipeline assemble
Multi-agent latency = parallel (3 agents at once + orchestrator) and sequential (sum) ; single-agent = 1 call."""
import argparse, json, os, shutil, pathlib, subprocess, sys, time, statistics
from concurrent.futures import ThreadPoolExecutor
from rag import llm
ap = argparse.ArgumentParser(); ap.add_argument("--backend", required=True); ap.add_argument("--model"); ap.add_argument("--out", required=True); ap.add_argument("--limit", type=int); a = ap.parse_args()
SRC = pathlib.Path("results/llm_runs"); OUT = pathlib.Path(a.out); OUT.mkdir(parents=True, exist_ok=True); shutil.copy(SRC / "retrieved.json", OUT / "retrieved.json")
be = llm.get(a.backend, a.model)
P = {r: json.load(open(SRC / f"prompts_{r}.json")) for r in ("elig", "nec", "doc", "base")}
ids = [x["case_id"] for x in P["elig"]][: a.limit]
def run(role, cid, prompt, retries=2):
    for k in range(retries + 1):
        try:
            text, sec = be.call(prompt); d = llm.extract_json(text); d["case_id"] = cid; return d, sec
        except Exception as e:
            if k == retries: return {"case_id": cid, "verdict": "UNKNOWN", "decision": "NOT_COVERED", "reason": f"ERROR {e}", "findings": []}, 0.0
T = {cid: {} for cid in ids}; R = {r: [] for r in ("elig", "nec", "doc", "base", "orch")}
def wave1(cid):
    t0 = time.perf_counter(); res = {}
    with ThreadPoolExecutor(3) as ex:                       # three agents in parallel
        fs = {r: ex.submit(run, r, cid, next(x["prompt"] for x in P[r] if x["case_id"] == cid)) for r in ("elig", "nec", "doc")}
        for r, f in fs.items(): res[r] = f.result()
    return cid, res, time.perf_counter() - t0
def single(cid):
    return cid, run("base", cid, next(x["prompt"] for x in P["base"] if x["case_id"] == cid))
w1 = [wave1(c) for c in ids]; sg = [single(c) for c in ids]
for cid, res, wall in w1:
    for r, (d, sec) in res.items(): R[r].append(d); T[cid][r] = sec
    T[cid]["wave1_parallel_wall"] = wall
for cid, (d, sec) in sg: R["base"].append(d); T[cid]["base"] = sec
for r in ("elig", "nec", "doc", "base"): json.dump(R[r], open(OUT / f"resp_{r}.json", "w"), indent=1)
env = dict(os.environ, RUN_DIR=str(OUT))
subprocess.run([sys.executable, "-m", "rag.pipeline", "orch"], env=env, check=True)         # builds prompts_orch.json from live responses
O = json.load(open(OUT / "prompts_orch.json")); O = [x for x in O if x["case_id"] in ids]
for x in O:
    d, sec = run("orch", x["case_id"], x["prompt"]); R["orch"].append(d); T[x["case_id"]]["orch"] = sec
json.dump(R["orch"], open(OUT / "resp_orch.json", "w"), indent=1)
def agg(f): v = [f(c) for c in ids]; return dict(mean=round(statistics.mean(v), 2), median=round(statistics.median(v), 2), max=round(max(v), 2))
summ = dict(backend=be.name, cases=len(ids), single_agent_s=agg(lambda c: T[c]["base"]),
            multi_agent_parallel_s=agg(lambda c: T[c]["wave1_parallel_wall"] + T[c]["orch"]), multi_agent_sequential_s=agg(lambda c: T[c]["elig"] + T[c]["nec"] + T[c]["doc"] + T[c]["orch"]))
json.dump(dict(summary=summ, per_case=T), open(OUT / "timing.json", "w"), indent=1); print(json.dumps(summ, indent=1))
