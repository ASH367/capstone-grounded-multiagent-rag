#!/usr/bin/env python3
"""DEV-ONLY. Build candidate 'story-keeping' arms for the dev part of the FINAL set, WITHOUT touching the frozen arms:
   A_plus  = A_strict + clean weak facts          A_plusW = A_plus + record-fact clauses recovered from reasoning sentences
Writes data/cases_v5/<arm>_final_dev/<case>.json (same fields as A_strict_final_dev, new facts) + results/review/cut_build_dev.json."""
import json, sys, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from rag import fairtest as F, cutvariants as CV
sys.path.insert(0, str(ROOT / "scripts")); import build_units as BU
FINAL = json.load(open(ROOT / "results/FINAL_SET.json")); V5 = ROOT / "data/cases_v5"
UNITS = {u["uid"]: u for u in BU.U}; cache = {}; rep = []
VAR = {"A_plus": "plus", "A_plusW": "plusW"}
for arm in VAR: (V5 / f"{arm}_final_dev").mkdir(parents=True, exist_ok=True)
for m in FINAL:
    if m["set"] != "dev" or m["status"] != "MAIN": continue
    cid = m["id"]; base = json.load(open(ROOT / "data/cases_v4/A_strict_final_dev" / f"{cid}.json"))
    parent = m["parent"]
    if parent not in cache: cache[parent] = F.analyze(parent)
    paras, sents = cache[parent]
    if m["kind"] == "unit":
        u = UNITS[cid]; sel = []
        for a, z in u["ranges"]:
            own = BU.owners(paras, a, z) if u["service"] else {}
            for s in sents:
                if not (a <= s["pi"] < z): continue
                if u["service"] and own.get(s["pi"]) and u["service"] not in own[s["pi"]]: continue
                if s not in sel: sel.append(s)
        sel.sort(key=lambda s: (s["pi"], s["si"]))
    else: sel = sents
    row = dict(id=cid, label=m["label"], wordsA=base["evidence_words_A"])
    for arm, v in VAR.items():
        rs = CV.retag(sel, v); fu = F.units(rs, F.ARMS["A_strict"])
        c = dict(base); c.update(facts=fu, arm=arm, build=dict(tool="scripts/build_cut_dev.py", variant=v, dev_only=True, tagger_sha=F.rules_hash()))
        json.dump(c, open(V5 / f"{arm}_final_dev" / f"{cid}.json", "w"), indent=1)
        row[arm] = sum(len(x.split()) for x in fu)
    row["A_strict"] = sum(len(x.split()) for x in base["facts"]); rep.append(row)
json.dump(rep, open(ROOT / "results/review/cut_build_dev.json", "w"), indent=1)
print(f"{'case':34s}{'label':13s}{'strict':>7s}{'A_plus':>8s}{'A_plusW':>9s}")
for r in rep: print(f"{r['id']:34s}{r['label']:13s}{r['A_strict']:7d}{r['A_plus']:8d}{r['A_plusW']:9d}")
print("TOTAL words:", {k: sum(r[k] for r in rep) for k in ("A_strict", "A_plus", "A_plusW")}, "| cases below the 60-word floor now:", sum(r["A_strict"] < 60 for r in rep), "-> A_plus:", sum(r["A_plus"] < 60 for r in rep))
