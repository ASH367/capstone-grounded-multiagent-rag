#!/usr/bin/env python3
"""Blind probe: how well can a model guess the Council outcome from the FACTS ALONE (no policy text, no retrieval)?
That is the leak floor for an arm. The system only 'adds value' to the extent it beats this number on the same cases.
  export LLM_API_KEY=... LLM_BASE_URL=...
  python3 scripts/blind_probe.py --arm D_wide --set held --backend openai --model anthropic/claude-sonnet-5.5
"""
import argparse, glob, json, os, sys
sys.path.insert(0, "."); sys.path.insert(0, "scripts")
from rag import llm
import score_fair as S

P = ("Below are facts from a Medicare coverage appeal. Using only your general knowledge of how Medicare coverage appeals are decided, guess the final outcome.\n\n<facts>\n{facts}\n</facts>\n\n"
     'Reply with JSON only: {{"decision": "COVERED" | "NOT_COVERED" | "PARTLY_COVERED"}}')

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--arm", required=True); ap.add_argument("--set", required=True, choices=["dev", "held"]); ap.add_argument("--backend", default="mock"); ap.add_argument("--model")
    a = ap.parse_args(); be = llm.get(a.backend, a.model); out = f"results/fair/probe_{a.arm}_{a.set}"; os.makedirs(out, exist_ok=True); R = []
    for f in sorted(glob.glob(f"data/cases_v4/{a.arm}_{a.set}/*.json")):
        c = json.load(open(f)); facts = "\n".join(f"[{i+1}] {x}" for i, x in enumerate(c["facts"]))
        try: text, _ = be.call(P.format(facts=facts)); d = llm.extract_json(text)
        except Exception as e: d = {"decision": None, "error": str(e)}
        d["case_id"] = c["case_id"]; R.append(d)
    json.dump(R, open(f"{out}/resp_base.json", "w"), indent=1); json.dump(R, open(f"{out}/resp_orch.json", "w"), indent=1)
    os.system(f"python3 scripts/score_fair.py --arm {a.arm} --set {a.set} --runs {out}")
