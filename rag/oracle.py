"""Oracle-retrieval ablation: give the system the manual sections the Council actually cited (capped at 12 passages, ranked by TF-IDF to the facts)
instead of retrieved ones. Measures how much accuracy retrieval costs.
  CASES_DIR=data/cases_v3_oracle INDEX_DIR=data/index_v3 RUN_DIR=results/oracle_r1 python3 -m rag.oracle"""
import json
from rag import pipeline as P
from sklearn.metrics.pairwise import linear_kernel
CAP = 12
retrieved = {}; out = {r: [] for r in ("elig", "nec", "doc", "base")}
for cid, c in P.cases.items():
    gold = {(g["doc"], g["section"]) for g in c["cited_sections"]}
    idx = [i for i, k in enumerate(P.chunks) if (k["doc"], k["section"]) in gold]
    s = linear_kernel(P.vec.transform([" ".join(c["facts"])]), P.X[idx]).ravel()
    ids = [idx[j] for j in s.argsort()[::-1][:CAP]]
    retrieved[cid] = {r: [P.chunks[i]["chunk_id"] for i in ids] for r in ("elig", "nec", "doc", "base")}
    for r in ("elig", "nec", "doc"): out[r].append({"case_id": cid, "prompt": P.prompt_role(r, c, ids)})
    out["base"].append({"case_id": cid, "prompt": P.prompt_base(c, ids)})
json.dump(retrieved, open(P.RUN / "retrieved.json", "w"), indent=1)
for r, v in out.items(): json.dump(v, open(P.RUN / f"prompts_{r}.json", "w"), indent=1)
print({r: len(v) for r, v in out.items()}, "passages per case:", {k: len(v["base"]) for k, v in retrieved.items()})
