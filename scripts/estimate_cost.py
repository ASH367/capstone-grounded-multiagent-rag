#!/usr/bin/env python3
"""Cost estimate BEFORE spending.   python3 scripts/estimate_cost.py [--arms D_wide A_strict] [--sets final_held final_dev] [--runs 1] [--notes] [--redo-fraction 0.1]
Counts the saved prompts (run `prepare` first, which is free) and prices them. Token count = characters / 4 (rough). Output-token sizes are typical values, not measured.
PRICE: export LLM_PRICE_IN / LLM_PRICE_OUT = USD per 1M tokens for YOUR model (defaults 3 / 15 are only an assumption - check OpenRouter's model page).
After a real run, `LLM_USAGE_LOG=usage.jsonl` records true per-call cost; compare with this estimate and set CAL=<actual/estimate> to calibrate.
Hard stop at run time: export MAX_USD=8  (rag/llm.py aborts once the running total passes it; finished work is kept and the same command resumes)."""
import argparse, glob, json, os, pathlib
ap = argparse.ArgumentParser(); ap.add_argument("--arms", nargs="+", default=["D_wide", "A_strict"]); ap.add_argument("--sets", nargs="+", default=["final_held", "final_dev"])
ap.add_argument("--runs", type=int, default=1); ap.add_argument("--notes", action="store_true"); ap.add_argument("--probe", type=int, default=1); ap.add_argument("--redo-fraction", type=float, default=1.0, help="share of cases actually (re)run, e.g. 0.1 for a failed-only rerun")
a = ap.parse_args()
PI, PO, CAL = float(os.environ.get("LLM_PRICE_IN", 3)), float(os.environ.get("LLM_PRICE_OUT", 15)), float(os.environ.get("CAL", 1))
OUT = dict(role=500, base=500, orch=150, probe=15, note=450)
tot = 0.0; print(f"price assumption: ${PI}/M in, ${PO}/M out, calibration x{CAL}, runs={a.runs}, notes={a.notes}, redo-fraction={a.redo_fraction}")
for arm in a.arms:
    for st in a.sets:
        pd = pathlib.Path(f"results/fair/{arm}_{st}/prompts")
        if not (pd / "prompts_elig.json").exists(): print(f"  {arm}_{st}: no saved prompts - run: CASES_DIR=data/cases_v4/{arm}_{st} RUN_DIR={pd} python3 -m rag.pipeline prepare"); continue
        P = {r: json.load(open(pd / f"prompts_{r}.json")) for r in ("elig", "nec", "doc", "base")}
        n = len(P["elig"]); tin = tout = 0
        for r in ("elig", "nec", "doc", "base"):
            tin += sum(len(x["prompt"]) for x in P[r]) / 4; tout += n * OUT["role" if r != "base" else "base"]
        facts = [len(x["prompt"].split("<case_facts>")[1].split("</case_facts>")[0]) for x in P["elig"]]
        tin += sum(f + 1800 + 900 for f in facts) / 4; tout += n * OUT["orch"]                       # orchestrator
        tin *= a.runs; tout *= a.runs
        if a.probe: tin += sum(f + 400 for f in facts) / 4; tout += n * OUT["probe"]
        if a.notes: tin += 0.45 * sum(f + 5000 for f in facts) / 4 * a.runs; tout += 0.45 * n * OUT["note"] * a.runs
        usd = (tin * PI + tout * PO) / 1e6 * CAL * a.redo_fraction; tot += usd
        print(f"  {arm:9s} {st:11s} cases={n:3d}  ~{tin*a.redo_fraction/1e3:6.0f}k in / {tout*a.redo_fraction/1e3:5.0f}k out tokens   ~${usd:5.2f}")
print(f"ESTIMATED TOTAL ~${tot:.2f}   (a rough guess, not a quote; use MAX_USD as the hard stop)")
