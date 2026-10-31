"""Criteria-tree design (after Pandey et al., BioNLP 2024, adapted).
Decompose by CRITERION, not by role. For each case: START -> fan out one LLM call per tree leaf (LangGraph Send) -> aggregate in CODE (AND/OR with a No-Information rule) -> decision.
Leaf prompt sees only the case facts and the manual passages from that leaf's sections. Case outcomes never appear in any prompt.
  CASES_DIR=data/cases_v3_heldout_clean INDEX_DIR=data/index_v3 \
  python3 -m rag.tree run --backend mock --out results/tree_mock --limit 2
  python3 -m rag.tree score --out results/tree_r1
Pre-registered mapping (fixed BEFORE any real run): root TRUE -> COVERED; root FALSE -> NOT_COVERED; root NO_INFORMATION (no criterion shown to fail) -> COVERED.
The tree cannot output PARTLY_COVERED by construction; that limit is reported, not hidden."""
import argparse, glob, json, operator, os, pathlib, re, sys, threading, time
from typing import Annotated, TypedDict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from rag import llm

TREES = json.load(open(os.environ.get("TREES", "data/criteria/trees.json")))
idx = json.load(open(os.environ.get("INDEX_DIR", "data/index_v3") + "/chunks.json")); chunks = idx["chunks"]
cases = {c["case_id"]: c for c in (json.load(open(f)) for f in sorted(glob.glob(os.environ.get("CASES_DIR", "data/cases_v3_heldout_clean") + "/*.json")))}
MAP = {"favorable": "COVERED", "unfavorable": "NOT_COVERED", "partial": "PARTLY_COVERED", "unknown": "UNKNOWN"}
vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True); X = vec.fit_transform([c["text"] for c in chunks])

SEM = threading.Semaphore(int(os.environ.get('TREE_CONCURRENCY', '3')))   # limit parallel API calls (avoids HTTP 429)
RULES = ("Rules: use ONLY the case facts and the passages below. Do not use outside knowledge. Answer TRUE only if the case facts show the criterion is met; FALSE only if the case facts show it is NOT met; "
         "NO_INFORMATION if the case facts do not settle it. For TRUE or FALSE, cite one passage id and copy a short quote (max 25 words) EXACTLY from that passage, and copy the case fact you relied on (max 25 words) EXACTLY from the case facts.")

def leaves(node, out=None):
    out = [] if out is None else out
    if node.get("leaf"): out.append(node)
    for c in node.get("children", []): leaves(c, out)
    return out

def facts_text(c): return "\n".join(f"[{n+1}] {x}" for n, x in enumerate(c["facts"]))

def leaf_passages(leaf, doc, c, k=4):
    cand = [i for i, ch in enumerate(chunks) if ch["doc"] == doc and ch["section"] in set(leaf["sections"])]
    if not cand: return []
    s = linear_kernel(vec.transform([" ".join(c["facts"]) + " " + leaf["text"]]), X[cand]).ravel()
    return [cand[j] for j in s.argsort()[::-1][:k]]

def leaf_prompt(leaf, doc, c):
    ids = leaf_passages(leaf, doc, c)
    ps = "\n\n".join(f"<passage id=\"{chunks[i]['chunk_id']}\" source=\"{chunks[i]['label']}\">\n{chunks[i]['text']}\n</passage>" for i in ids)
    return (f"You are checking ONE criterion of a Medicare coverage rule against a case.\nCriterion: {leaf['text']}\n{RULES}\n\n<case_facts>\n{facts_text(c)}\n</case_facts>\n\n<policy_passages>\n{ps}\n</policy_passages>\n\n"
            'Reply with JSON only: {"verdict": "TRUE" | "FALSE" | "NO_INFORMATION", "reason": "one sentence", "passage_id": <int or null>, "quote": "...", "case_fact": "..."}'), [chunks[i]["chunk_id"] for i in ids]

def combine(op, vals):
    if op == "AND":
        if "FALSE" in vals: return "FALSE"
        return "NO_INFORMATION" if "NO_INFORMATION" in vals else "TRUE"
    if "TRUE" in vals: return "TRUE"
    return "NO_INFORMATION" if "NO_INFORMATION" in vals else "FALSE"

def evaluate(node, res):
    if node.get("leaf"): return res.get(node["id"], {}).get("verdict", "NO_INFORMATION")
    return combine(node["op"], [evaluate(ch, res) for ch in node["children"]])

def decide(root_verdict): return "NOT_COVERED" if root_verdict == "FALSE" else "COVERED"

class S(TypedDict, total=False):
    case_id: str
    leaf_results: Annotated[list, operator.add]
    root: str; decision: str; wall: float; errors: int

def build(backend):
    def dispatch(s):
        c = cases[s["case_id"]]; t = TREES[c["domain"]]
        return [Send("leaf", {"case_id": s["case_id"], "leaf": lf, "doc": t["doc"]}) for lf in leaves(t["root"])]
    def leaf(s):
        c = cases[s["case_id"]]; p, ids = leaf_prompt(s["leaf"], s["doc"], c)
        d, sec = None, 0.0
        for attempt in range(6):                                  # retry with backoff; failures are NEVER scored as answers
            try:
                with SEM: text, sec = backend.call(p)
                d = llm.extract_json(text); break
            except Exception as e:
                err = str(e); time.sleep(2 ** attempt)
        if d is None: d = {"verdict": "ERROR", "reason": f"ERROR {err}"}
        elif d.get("verdict") not in ("TRUE", "FALSE", "NO_INFORMATION"): d = {"verdict": "ERROR", "reason": f"ERROR bad verdict {d.get('verdict')!r}"}
        d.update({"case_id": s["case_id"], "leaf_id": s["leaf"]["id"], "seconds": sec, "offered_passage_ids": ids})
        return {"leaf_results": [d]}
    def aggregate(s):
        c = cases[s["case_id"]]; res = {r["leaf_id"]: r for r in s["leaf_results"]}
        nerr = sum(1 for r in res.values() if r["verdict"] == "ERROR")
        root = evaluate(TREES[c["domain"]]["root"], {k: ({**v, "verdict": "NO_INFORMATION"} if v["verdict"] == "ERROR" else v) for k, v in res.items()})
        return {"root": root, "decision": "ERROR" if nerr else decide(root), "errors": nerr}
    g = StateGraph(S); g.add_node("leaf", leaf); g.add_node("aggregate", aggregate)
    g.add_conditional_edges(START, dispatch, ["leaf"]); g.add_edge("leaf", "aggregate"); g.add_edge("aggregate", END)
    return g.compile()

def run(a):
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    be = llm.get(a.backend, a.model); graph = build(be); R = []
    for cid in list(cases)[: a.limit]:
        t0 = time.perf_counter(); s = graph.invoke({"case_id": cid, "leaf_results": []}); wall = time.perf_counter() - t0
        R.append({"case_id": cid, "domain": cases[cid]["domain"], "root": s["root"], "decision": s["decision"], "errors": s.get("errors", 0), "wall_s": wall, "leaves": sorted(s["leaf_results"], key=lambda r: r["leaf_id"])})
        print(cid, s["root"], s["decision"], f"{wall:.1f}s", flush=True)
    json.dump({"backend": be.name, "results": R}, open(out / "tree_results.json", "w"), indent=1)

def n(s): return re.sub(r"\s+", " ", s or "").strip().lower()
def score(a):
    D = json.load(open(pathlib.Path(a.out) / "tree_results.json")); R0 = D["results"]
    bad = [r for r in R0 if r.get("errors", 0)]
    print(f"cases with failed calls: {len(bad)} of {len(R0)} (failed leaf calls: {sum(r['errors'] for r in bad)}). These are EXCLUDED from accuracy.")
    R = [r for r in R0 if not r.get("errors", 0)]
    if not R: print("no valid cases; rerun"); return
    gold = {k: MAP[c["reference_outcome"]] for k, c in cases.items()}
    import collections
    if all(v == "UNKNOWN" for v in gold.values()):
        print(f"{D['backend']}: unlabeled cases, decision accuracy not computed; decisions {dict(collections.Counter(r['decision'] for r in R))}")
    else:
        ok = sum(r["decision"] == gold[r["case_id"]] for r in R)
        print(f"{D['backend']}: 3-class {ok}/{len(R)} ({ok/len(R):.0%})")
        nonp = [r for r in R if gold[r["case_id"]] != "PARTLY_COVERED"]
        print(f"covered-vs-not on the {len(nonp)} non-partial cases: {sum(r['decision']==gold[r['case_id']] for r in nonp)}/{len(nonp)}")
        cm = collections.Counter((gold[r["case_id"]], r["decision"]) for r in R)
        for g in ("COVERED", "NOT_COVERED", "PARTLY_COVERED"): print(" ", g, {p: cm[(g, p)] for p in ("COVERED", "NOT_COVERED")})
    lv = [l for r in R for l in r["leaves"]]; c = collections.Counter(l["verdict"] for l in lv); print("leaf verdicts", dict(c), f"| NO_INFORMATION share {c['NO_INFORMATION']/max(1,len(lv)):.0%}")
    bad = tot = 0
    for r in R:
        for l in r["leaves"]:
            if l["verdict"] == "NO_INFORMATION": continue
            tot += 1; pid = l.get("passage_id")
            txt = next((ch["text"] for ch in chunks if ch["chunk_id"] == pid), None)
            facts = n(facts_text(cases[r["case_id"]]))
            good = pid in l["offered_passage_ids"] and txt and n(l.get("quote")) in n(txt) and n(l.get("case_fact")) in facts
            bad += not good
    print(f"citations: {tot - bad}/{tot} mechanically valid among TRUE/FALSE leaves")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["run", "score"]); ap.add_argument("--backend", default="mock"); ap.add_argument("--model"); ap.add_argument("--out", required=True); ap.add_argument("--limit", type=int)
    a = ap.parse_args(); {"run": run, "score": score}[a.cmd](a)
