"""Retrieval test: query = case facts only; gold = MBPM sections the Council itself cited (not our wording)."""
import json, glob, random, pathlib, collections
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

idx = json.load(open("data/index_v2/chunks.json")); chunks = idx["chunks"]
cases = [json.load(open(f)) for f in sorted(glob.glob("data/cases_v2/*.json"))]
DOMDOC = {"home_health": "MBPM ch.7", "ambulance": "MBPM ch.10", "inpatient_rehab": "MBPM ch.1"}

# fixed dev/test split, stratified by domain (seed 7)
rng = random.Random(7); split = {}
for d in DOMDOC:
    ids = sorted(c["case_id"] for c in cases if c["domain"] == d); rng.shuffle(ids)
    for i, cid in enumerate(ids): split[cid] = "dev" if i % 2 == 0 else "test"

vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
X = vec.fit_transform([c["text"] for c in chunks])

def related(a, b):  # same section, or ancestor/descendant (e.g. 40.1 vs 40.1.2.1)
    return a == b or a.startswith(b + ".") or b.startswith(a + ".")

def topk_sections(q, k, doc=None):
    s = linear_kernel(vec.transform([q]), X).ravel()
    order = [i for i in s.argsort()[::-1] if doc is None or chunks[i]["doc"] == doc]
    out = []
    for i in order:
        key = (chunks[i]["doc"], chunks[i]["section"])
        if key not in out: out.append(key)
        if len(out) == k: break
    return out

corpus_secs = {(c["doc"], c["section"]) for c in chunks}
rows = []; skipped = collections.Counter()
for c in cases:
    gold_all = [(g["doc"], g["section"]) for g in c["cited_sections"]]
    gold = [g for g in gold_all if g in corpus_secs]
    skipped["gold_not_in_corpus"] += len(gold_all) - len(gold)
    if not gold: skipped["case_no_usable_gold"] += 1; continue
    q = " ".join(c["facts"])
    for mode, doc in (("all_manuals", None), ("domain_routed", DOMDOC[c["domain"]])):
        for k in (3, 5, 10):
            top = topk_sections(q, k, doc)
            ex = sum(g in top for g in gold) / len(gold)
            rel = sum(any(g[0] == t[0] and related(g[1], t[1]) for t in top) for g in gold) / len(gold)
            rows.append(dict(case=c["case_id"], domain=c["domain"], split=split[c["case_id"]], mode=mode, k=k, exact=ex, related=rel, any_exact=int(ex > 0), any_related=int(rel > 0)))

def avg(f, **kw):
    r = [x[f] for x in rows if all(x[a] == b for a, b in kw.items())]
    return round(sum(r) / len(r), 3) if r else None
summary = {"n_cases_scored": len({r["case"] for r in rows}), "n_cases_total": len(cases), "skipped": dict(skipped), "manual_versions": idx["versions"], "table": {}}
for mode in ("all_manuals", "domain_routed"):
    for k in (3, 5, 10):
        summary["table"][f"{mode}@{k}"] = {m: avg(m, mode=mode, k=k) for m in ("exact", "related", "any_exact", "any_related")}
json.dump({"summary": summary, "split": split, "rows": rows}, open("results/retrieval_v2.json", "w"), indent=1)
print(json.dumps(summary, indent=1))
print("per-domain related@5 (all_manuals):", {d: avg("related", mode="all_manuals", k=5, domain=d) for d in DOMDOC})
print("dev/test counts:", collections.Counter(split.values()))
