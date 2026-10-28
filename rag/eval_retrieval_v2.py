"""Pick the retriever on DEV cases only, then report TEST once. Gold = MBPM sections the Council cited."""
import json, glob, itertools, collections
import numpy as np
from rag.retrievers import Tfidf, BM25, LSA, Hybrid
idx = json.load(open("data/index_v2/chunks.json")); chunks = idx["chunks"]
cases = [json.load(open(f)) for f in sorted(glob.glob("data/cases_v2/*.json"))]
split = json.load(open("results/retrieval_v2.json"))["split"]
DOMDOC = {"home_health": "MBPM ch.7", "ambulance": "MBPM ch.10", "inpatient_rehab": "MBPM ch.1"}
corpus = {(c["doc"], c["section"]) for c in chunks}
def related(a, b): return a == b or a.startswith(b + ".") or b.startswith(a + ".")

def topk(r, q, k, doc):
    s = r.scores(q); out = []
    for i in np.argsort(-s):
        if doc and chunks[i]["doc"] != doc: continue
        key = (chunks[i]["doc"], chunks[i]["section"])
        if key not in out: out.append(key)
        if len(out) == k: break
    return out

def score(r, which, doc_routed):
    rows = []
    for c in cases:
        if split[c["case_id"]] != which: continue
        gold = [(g["doc"], g["section"]) for g in c["cited_sections"] if (g["doc"], g["section"]) in corpus]
        if not gold: continue
        q = " ".join(c["facts"]); doc = DOMDOC[c["domain"]] if doc_routed else None
        for k in (5, 10):
            top = topk(r, q, k, doc)
            rows.append((k, sum(g in top for g in gold) / len(gold), sum(any(g[0] == t[0] and related(g[1], t[1]) for t in top) for g in gold) / len(gold)))
    res = {}
    for k in (5, 10):
        v = [x for x in rows if x[0] == k]
        res[k] = dict(exact=round(np.mean([x[1] for x in v]), 3), related=round(np.mean([x[2] for x in v]), 3), n=len(v))
    return res

tf, bm, ls = Tfidf(chunks), BM25(chunks), LSA(chunks)
cands = {"tfidf (M1 baseline)": tf, "bm25": bm, "lsa": ls, "hybrid bm25+lsa": Hybrid([bm, ls]), "hybrid bm25+tfidf": Hybrid([bm, tf]), "hybrid bm25+tfidf+lsa": Hybrid([bm, tf, ls])}
dev = {n: score(r, "dev", True) for n, r in cands.items()}
print("DEV (domain-routed)  n_scored =", dev["tfidf (M1 baseline)"][5]["n"])
for n, d in dev.items(): print(f"  {n:26} top5 exact {d[5]['exact']:.2f} rel {d[5]['related']:.2f} | top10 exact {d[10]['exact']:.2f} rel {d[10]['related']:.2f}")
# choose on dev: mean of the four numbers
best = max(dev, key=lambda n: np.mean([dev[n][5]["exact"], dev[n][5]["related"], dev[n][10]["exact"], dev[n][10]["related"]]))
print("chosen on DEV:", best)
test = {n: score(cands[n], "test", True) for n in ("tfidf (M1 baseline)", best)}
print("TEST (reported once, domain-routed)")
for n, d in test.items(): print(f"  {n:26} top5 exact {d[5]['exact']:.2f} rel {d[5]['related']:.2f} | top10 exact {d[10]['exact']:.2f} rel {d[10]['related']:.2f}  n={d[5]['n']}")
json.dump({"dev": {n: {str(k): v for k, v in d.items()} for n, d in dev.items()}, "chosen_on_dev": best, "test": {n: {str(k): v for k, v in d.items()} for n, d in test.items()}}, open("results/retrieval_m2.json", "w"), indent=1)
