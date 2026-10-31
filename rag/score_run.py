"""Tolerant scorer for a LangGraph run folder (resp_orch.json, resp_base.json, resp_elig/nec/doc.json).
  CASES_DIR=data/cases_v3_heldout_clean INDEX_DIR=data/index_v3 python3 -m rag.score_run results/llama70_r1 [more folders]
Accuracy against the mapped appeal outcome; mechanical citation check that tolerates malformed findings (counted as invalid)."""
import glob, json, os, re, sys, collections
M = {"favorable": "COVERED", "unfavorable": "NOT_COVERED", "partial": "PARTLY_COVERED"}
chunks = {c["chunk_id"]: c for c in json.load(open(os.environ.get("INDEX_DIR", "data/index_v3") + "/chunks.json"))["chunks"]}
cases = {c["case_id"]: c for c in (json.load(open(f)) for f in glob.glob(os.environ.get("CASES_DIR", "data/cases_v3_heldout_clean") + "/*.json"))}
gold = {k: M[c["reference_outcome"]] for k, c in cases.items()}
n = lambda s: re.sub(r"\s+", " ", s or "").strip().lower()
def valid(f, cid):
    if not isinstance(f, dict): return False
    ch = chunks.get(f.get("passage_id")); facts = n("\n".join(f"[{i+1}] {x}" for i, x in enumerate(cases[cid]["facts"])))
    return bool(ch) and bool(n(f.get("quote"))) and n(f["quote"]) in n(ch["text"]) and n(f.get("case_fact")) in facts
for d in sys.argv[1:]:
    print("==", d)
    for name, fn in (("multi", "resp_orch.json"), ("single", "resp_base.json")):
        R = {x["case_id"]: x for x in json.load(open(f"{d}/{fn}"))}
        ok = sum(v.get("decision") == gold[k] for k, v in R.items())
        cm = collections.Counter((gold[k], v.get("decision")) for k, v in R.items())
        print(f"{name}: {ok}/{len(R)} ({ok/len(R):.0%}) preds {dict(collections.Counter(v.get('decision') for v in R.values()))}")
        for g in ("COVERED", "NOT_COVERED", "PARTLY_COVERED"): print("   ", g, {p: cm[(g, p)] for p in ("COVERED", "NOT_COVERED", "PARTLY_COVERED")})
    for role, fn in (("elig", "resp_elig.json"), ("nec", "resp_nec.json"), ("doc", "resp_doc.json"), ("single", "resp_base.json")):
        R = json.load(open(f"{d}/{fn}")); tot = good = 0
        for x in R:
            for f in x.get("findings", []): tot += 1; good += valid(f, x["case_id"])
        print(f"citations {role}: {good}/{tot} valid" + (f" ({good/tot:.0%})" if tot else ""))
