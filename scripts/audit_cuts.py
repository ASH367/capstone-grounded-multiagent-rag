#!/usr/bin/env python3
"""DEV-ONLY audit of candidate cuts: how many dropped sentences each variant recovers, how many words of story, and samples to READ."""
import json, random, sys, collections
sys.path.insert(0, ".")
from rag import fairtest as ft, cutvariants as cv
info = ft.tags_info(); dev = sorted(k for k, v in info.items() if v["set"] == "dev")
random.seed(5); tot = collections.defaultdict(lambda: [0, 0]); pool = collections.defaultdict(list); base = 0
for cid in dev:
    S = json.load(open(f"data/cases_v4/tags/{cid}.json"))["sentences"]
    base += sum(len(x["text"].split()) for x in S if x["tag"] in ft.ARMS["A_strict"])
    for v in "SMW":
        for r in cv.recovered(S, v):
            tot[v][0] += 1; tot[v][1] += len(r["kept"].split()); pool[v].append((cid, r))
print(f"DEV decisions {len(dev)} | strict-arm story words now: {base}")
for v in "SMW": print(f"variant {v}: +{tot[v][0]} pieces, +{tot[v][1]} words ({100*tot[v][1]/base:.0f}% more story)")
with open("results/review/cut_audit_dev.md", "w") as f:
    f.write("# Cut audit (DEV only). For each recovered piece: is it a record FACT (ok) or does it carry the Council's conclusion (leak)?\n")
    for v in "SMW":
        f.write(f"\n## Variant {v}\n")
        for cid, r in random.sample(pool[v], min(25, len(pool[v]))):
            f.write(f"- [{cid}] KEPT: {r['kept'][:300]}\n    ORIG({r['tag']}): {r['orig'][:300]}\n")
print("wrote results/review/cut_audit_dev.md")
