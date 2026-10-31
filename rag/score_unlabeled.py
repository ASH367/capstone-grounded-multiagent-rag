"""Scorer for runs on cases WITHOUT outcome labels (e.g. data/cases_pmc_pilot). No accuracy; reports what can be measured:
decision distribution, mechanical citation validity per role (exact quote in cited manual passage AND exact case fact in the case), mean latency.
  CASES_DIR=data/cases_pmc_pilot INDEX_DIR=data/index_v3 python3 -m rag.score_unlabeled results/pmc_pilot_sonnet"""
import glob, json, os, re, sys, collections
chunks = {c["chunk_id"]: c for c in json.load(open(os.environ.get("INDEX_DIR", "data/index_v3") + "/chunks.json"))["chunks"]}
cases = {c["case_id"]: c for c in (json.load(open(f)) for f in glob.glob(os.environ.get("CASES_DIR", "data/cases_pmc_pilot") + "/*.json"))}
n = lambda s: re.sub(r"\s+", " ", s or "").strip().lower()
def valid(f, cid):
    if not isinstance(f, dict): return False
    ch = chunks.get(f.get("passage_id")); facts = n("\n".join(f"[{i+1}] {x}" for i, x in enumerate(cases[cid]["facts"])))
    return bool(ch) and bool(n(f.get("quote"))) and n(f["quote"]) in n(ch["text"]) and n(f.get("case_fact")) in facts
for d in sys.argv[1:]:
    print("==", d)
    for name, fn in (("multi", "resp_orch.json"), ("single", "resp_base.json")):
        R = json.load(open(f"{d}/{fn}")); print(f"{name}: n={len(R)} decisions {dict(collections.Counter(x.get('decision') for x in R))}")
    for role, fn in (("elig", "resp_elig.json"), ("nec", "resp_nec.json"), ("doc", "resp_doc.json"), ("single", "resp_base.json")):
        R = json.load(open(f"{d}/{fn}")); tot = good = 0
        for x in R:
            for f in x.get("findings", []): tot += 1; good += valid(f, x["case_id"])
        print(f"citations {role}: {good}/{tot} valid" + (f" ({good/tot:.0%})" if tot else ""))
