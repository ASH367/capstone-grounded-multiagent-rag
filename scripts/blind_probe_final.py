#!/usr/bin/env python3
"""Blind probe on the FINAL sets: model sees the facts only (no policy, no retrieval). Leak floor.  python3 scripts/blind_probe_final.py --arm D_wide --set final_held --backend openai --model anthropic/claude-sonnet-5.5"""
import argparse, glob, json, os, sys
sys.path.insert(0, ".")
from rag import llm
P = ("Below are facts from a Medicare coverage appeal. Using only your general knowledge of how Medicare coverage appeals are decided, guess the final outcome.\n\n<facts>\n{facts}\n</facts>\n\n"
     'Reply with JSON only: {{"decision": "COVERED" | "NOT_COVERED" | "PARTLY_COVERED"}}')
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--arm", required=True); ap.add_argument("--set", required=True); ap.add_argument("--backend", default="mock"); ap.add_argument("--model"); a = ap.parse_args()
    be = llm.get(a.backend, a.model); out = f"results/fair/probe_{a.arm}_{a.set}"; os.makedirs(out, exist_ok=True); R = []
    done = {x["case_id"]: x for x in json.load(open(f"{out}/resp_base.json"))} if os.path.exists(f"{out}/resp_base.json") else {}   # resume: keep finished answers, redo only failed (decision None)
    for f in sorted(glob.glob(f"data/cases_v4/{a.arm}_{a.set}/*.json")):
        c = json.load(open(f))
        if done.get(c["case_id"], {}).get("decision"): R.append(done[c["case_id"]]); continue
        facts = "\n".join(f"[{i+1}] {x}" for i, x in enumerate(c["facts"]))
        try: d, _ = llm.call_json(be, P.format(facts=facts))
        except Exception as e: d = {"decision": None, "error": str(e)}
        d["case_id"] = c["case_id"]; R.append(d)
    json.dump(R, open(f"{out}/resp_base.json", "w"), indent=1)
