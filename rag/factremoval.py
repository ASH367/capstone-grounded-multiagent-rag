"""Fact-removal test for missing-information detection (known ground truth).
For every leaf the criteria tree answered TRUE, delete the ONE case fact it cited, rerun only that leaf.
  NO_INFORMATION            -> DETECTED   (model noticed the evidence is gone)
  TRUE citing another fact still in the case -> REDUNDANT (other facts also support it; not an error)
  TRUE citing a removed/invented fact, or FALSE -> UNSUPPORTED (model asserts without evidence)
  call failed               -> ERROR (excluded)
  CASES_DIR=data/cases_v3_heldout_clean INDEX_DIR=data/index_v3 python3 -m rag.factremoval --tree results/tree_sonnet_r2 --backend openai --model anthropic/claude-sonnet-5.5 --out results/factremoval_sonnet_r1
"""
import argparse, collections, copy, json, pathlib, time
from rag import llm
import rag.tree as T

def run(a):
    D = json.load(open(pathlib.Path(a.tree) / "tree_results.json")); be = llm.get(a.backend, a.model); rows = []
    for r in D["results"]:
        for l in r["leaves"]:
            if l["verdict"] != "TRUE": continue
            c = T.cases[l["case_id"]]; cf = T.n(l.get("case_fact")); hit = [i for i, f in enumerate(c["facts"]) if cf and cf in T.n(f)]
            if not hit: rows.append({"case_id": l["case_id"], "leaf_id": l["leaf_id"], "outcome": "SKIP_FACT_NOT_FOUND"}); continue
            c2 = copy.deepcopy(c); removed = [c["facts"][i] for i in hit]; c2["facts"] = [f for i, f in enumerate(c["facts"]) if i not in hit]
            leaf = next(x for x in T.leaves(T.TREES[c["domain"]]["root"]) if x["id"] == l["leaf_id"])
            p, ids = T.leaf_prompt(leaf, T.TREES[c["domain"]]["doc"], c2); d = None
            for k in range(5):
                try: text, _ = be.call(p); d = llm.extract_json(text); break
                except Exception as e: time.sleep(2 ** k)
            if d is None: out = "ERROR"
            elif d.get("verdict") == "NO_INFORMATION": out = "DETECTED"
            elif d.get("verdict") == "TRUE":
                nf = T.n(d.get("case_fact")); out = "REDUNDANT" if nf and any(nf in T.n(f) for f in c2["facts"]) else "UNSUPPORTED"
            else: out = "UNSUPPORTED"
            rows.append({"case_id": l["case_id"], "leaf_id": l["leaf_id"], "outcome": out, "removed": removed, "new_verdict": (d or {}).get("verdict"), "new_case_fact": (d or {}).get("case_fact"), "reason": (d or {}).get("reason")})
            print(l["case_id"], l["leaf_id"], out, flush=True)
    o = pathlib.Path(a.out); o.mkdir(parents=True, exist_ok=True); json.dump({"backend": be.name, "rows": rows}, open(o / "factremoval.json", "w"), indent=1)
    print(dict(collections.Counter(x["outcome"] for x in rows)))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--tree", required=True); ap.add_argument("--backend", default="mock"); ap.add_argument("--model"); ap.add_argument("--out", required=True)
    run(ap.parse_args())
