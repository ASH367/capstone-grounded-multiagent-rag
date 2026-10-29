"""Multi-agent vs single-agent RAG over CMS manuals. LLM calls are file-based so every prompt/response is saved.
  python3 rag/pipeline.py prepare   -> prompts for eligibility / necessity / documentation agents + single-agent baseline
  python3 rag/pipeline.py orch      -> orchestrator prompts from the three agents' saved responses
  python3 rag/pipeline.py assemble  -> mechanical citation checks, decisions, metrics
Case outcomes are never placed in any prompt."""
import json, glob, sys, re, os, pathlib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

RUN = pathlib.Path(os.environ.get("RUN_DIR", "results/llm_runs")); RUN.mkdir(parents=True, exist_ok=True)
DEC_OUT = "results/milestone1_decisions.json" if str(RUN) == "results/llm_runs" else str(RUN / "decisions.json")
idx = json.load(open(os.environ.get("INDEX_DIR", "data/index_v2") + "/chunks.json")); chunks = idx["chunks"]
cases = {c["case_id"]: c for c in (json.load(open(f)) for f in sorted(glob.glob(os.environ.get("CASES_DIR", "data/cases_v2") + "/*.json")))}
split = json.load(open("results/retrieval_v2.json"))["split"]
DOMDOC = {"home_health": "MBPM ch.7", "ambulance": "MBPM ch.10", "inpatient_rehab": "MBPM ch.1", "snf": "MBPM ch.8"}
vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
X = vec.fit_transform([c["text"] for c in chunks])
ROLES = {
 "elig": ("Eligibility Agent", "Decide whether this service is a type of care that the retrieved policy covers at all, and whether the basic eligibility conditions in the policy (patient status, type of service, certification or similar) appear satisfied.", "eligibility requirements covered services conditions"),
 "nec":  ("Medical Necessity Agent", "Decide whether the clinical criteria in the retrieved policy are met by the patient's condition and circumstances described in the case.", "medical necessity clinical criteria reasonable necessary skilled"),
 "doc":  ("Documentation Agent", "Decide whether the evidence and records that the retrieved policy requires are present in the case record.", "documentation requirements records certification evidence"),
}
def retrieve(q, doc, k):
    s = linear_kernel(vec.transform([q]), X).ravel(); out = []
    for i in s.argsort()[::-1]:
        if chunks[i]["doc"] == doc: out.append(i)
        if len(out) == k: break
    return out
def facts_text(c): return "\n".join(f"[{n+1}] {x}" for n, x in enumerate(c["facts"]))
def passages_text(ids): return "\n\n".join(f"<passage id=\"{chunks[i]['chunk_id']}\" source=\"{chunks[i]['label']}\">\n{chunks[i]['text']}\n</passage>" for i in ids)
RULES = ("Rules: use ONLY the case facts and the passages below. Do not use outside knowledge. Every finding must cite one passage id and copy a short quote (max 25 words) EXACTLY from that passage, and copy the case fact it relies on (max 25 words) EXACTLY from the case facts. "
         "If the passages or case facts do not settle a point, say UNKNOWN rather than guessing.")
def prompt_role(role, c, ids):
    name, task, _ = ROLES[role]
    return (f"You are the {name} in a Medicare coverage-review system.\nTask: {task}\n{RULES}\n\n<case_facts>\n{facts_text(c)}\n</case_facts>\n\n<policy_passages>\n{passages_text(ids)}\n</policy_passages>\n\n"
            'Reply with JSON only: {"verdict": "SUPPORTS_COVERAGE" | "DOES_NOT_SUPPORT" | "UNKNOWN", "findings": [{"claim": "...", "passage_id": <int>, "quote": "...", "case_fact": "..."}]}')
def prompt_base(c, ids):
    return (f"You are a single reviewer deciding whether Medicare covers the service in this case.\n{RULES}\n\n<case_facts>\n{facts_text(c)}\n</case_facts>\n\n<policy_passages>\n{passages_text(ids)}\n</policy_passages>\n\n"
            'Reply with JSON only: {"decision": "COVERED" | "NOT_COVERED" | "PARTLY_COVERED", "reason": "one or two sentences", "findings": [{"claim": "...", "passage_id": <int>, "quote": "...", "case_fact": "..."}]}')

def prepare():
    retrieved = {}; P = {r: [] for r in ROLES}; P["base"] = []
    for cid, c in cases.items():
        doc = DOMDOC[c["domain"]]; retrieved[cid] = {}
        for r, (_, _, qx) in ROLES.items():
            ids = retrieve(" ".join(c["facts"]) + " " + qx, doc, 5); retrieved[cid][r] = [chunks[i]["chunk_id"] for i in ids]
            P[r].append({"case_id": cid, "prompt": prompt_role(r, c, ids)})
        ids = retrieve(" ".join(c["facts"]), doc, 8); retrieved[cid]["base"] = [chunks[i]["chunk_id"] for i in ids]
        P["base"].append({"case_id": cid, "prompt": prompt_base(c, ids)})
    json.dump(retrieved, open(RUN / "retrieved.json", "w"), indent=1)
    for r, v in P.items(): json.dump(v, open(RUN / f"prompts_{r}.json", "w"), indent=1)
    print({r: len(v) for r, v in P.items()})

def load(role): return {x["case_id"]: x for x in json.load(open(RUN / f"resp_{role}.json"))}
def orch():
    E, N, D = load("elig"), load("nec"), load("doc"); out = []
    for cid, c in cases.items():
        if not (cid in E and cid in N and cid in D): continue      # allows partial (--limit) runs
        blocks = ""
        for nm, R in (("Eligibility Agent", E), ("Medical Necessity Agent", N), ("Documentation Agent", D)):
            r = R[cid]; blocks += f"<agent name=\"{nm}\" verdict=\"{r['verdict']}\">\n" + "\n".join(f"- {f['claim']} (source passage {f['passage_id']}: \"{f['quote']}\")" for f in r["findings"]) + "\n</agent>\n"
        p = ("You are the Orchestrator in a Medicare coverage-review system. Three specialist agents have reviewed the case. Combine their findings into one decision. "
             "Use ONLY the agents' findings and the case facts; do not use outside knowledge. Cite the passage ids your decision relies on. COVERED = coverage is supported; NOT_COVERED = it is not; PARTLY_COVERED = part of the service or period is covered and part is not.\n\n"
             f"<case_facts>\n{facts_text(c)}\n</case_facts>\n\n{blocks}\n"
             'Reply with JSON only: {"decision": "COVERED" | "NOT_COVERED" | "PARTLY_COVERED", "reason": "one or two sentences", "passage_ids": [<int>, ...]}')
        if os.environ.get("ORCH_V2"):
            p = ("You are the Orchestrator in a Medicare coverage-review system. Three specialist agents have reviewed the case. Combine their findings into one decision. "
                 "Use ONLY the agents' findings and case facts; do not use outside knowledge. Cite the passage ids your decision relies on. "
                 "Step 1: split the claim into separable components (for example: the transport versus extra mileage; different time periods or visits; different services). If the claim has only one component, use one. "
                 "Step 2: for each component decide COVERED or NOT_COVERED using the agents' findings. A single specialist's DOES_NOT_SUPPORT or UNKNOWN does not settle a component by itself; weigh the findings. "
                 "Step 3: final decision = COVERED if all components are covered, NOT_COVERED if none are, PARTLY_COVERED if some are and some are not.\n\n"
                 f"<case_facts>\n{facts_text(c)}\n</case_facts>\n\n{blocks}\n"
                 'Reply with JSON only: {"components": [{"name": "...", "decision": "COVERED" | "NOT_COVERED"}], "decision": "COVERED" | "NOT_COVERED" | "PARTLY_COVERED", "reason": "one or two sentences", "passage_ids": [<int>, ...]}')
        out.append({"case_id": cid, "prompt": p})
    json.dump(out, open(RUN / "prompts_orch.json", "w"), indent=1); print(len(out), "orchestrator prompts")

MAP = {"favorable": "COVERED", "unfavorable": "NOT_COVERED", "partial": "PARTLY_COVERED"}
def n(s): return re.sub(r"\s+", " ", s or "").strip().lower()
def check(findings, cid, role):
    ok = bad = 0; allowed = set(json.load(open(RUN / "retrieved.json"))[cid][role]); ft = n(" ".join(cases[cid]["facts"]))
    for f in findings:
        pid = f.get("passage_id"); good = pid in allowed and n(f.get("quote")) in n(chunks[pid]["text"]) and n(f.get("case_fact")) in ft if pid in allowed else False
        ok += good; bad += (not good)
    return ok, bad
def assemble():
    E, N, D, B, O = (load(r) for r in ("elig", "nec", "doc", "base", "orch")); rows = []
    for cid, c in cases.items():
        if not all(cid in R for R in (E, N, D, B, O)): continue
        ref = MAP.get(c["reference_outcome"]); ma = O[cid]["decision"]; sa = B[cid]["decision"]
        ok = bad = 0
        for role, R in (("elig", E), ("nec", N), ("doc", D)):
            a, b = check(R[cid]["findings"], cid, role); ok += a; bad += b
        sok, sbad = check(B[cid]["findings"], cid, "base")
        rows.append(dict(case=cid, split=split.get(cid, "heldout"), domain=c["domain"], reference=ref, multi=ma, single=sa, multi_ok=ma == ref, single_ok=sa == ref,
                         multi_findings_valid=ok, multi_findings_invalid=bad, single_findings_valid=sok, single_findings_invalid=sbad,
                         agent_verdicts=[E[cid]["verdict"], N[cid]["verdict"], D[cid]["verdict"]]))
    def agg(rs, k): return round(sum(r[k] for r in rs) / len(rs), 3) if rs else None
    def val(rs, p): v = sum(r[p + "_findings_valid"] for r in rs); i = sum(r[p + "_findings_invalid"] for r in rs); return {"findings": v + i, "mechanically_valid": round(v / (v + i), 3) if v + i else None}
    summ = {}
    for name, rs in (("all", rows), ("dev", [r for r in rows if r["split"] == "dev"]), ("test", [r for r in rows if r["split"] == "test"]), ("heldout", [r for r in rows if r["split"] == "heldout"])):
        summ[name] = {"n": len(rs), "decision_agreement_multi": agg(rs, "multi_ok"), "decision_agreement_single": agg(rs, "single_ok"), "citation_check_multi": val(rs, "multi"), "citation_check_single": val(rs, "single")}
    from collections import Counter
    summ["reference_distribution"] = dict(Counter(r["reference"] for r in rows)); summ["multi_predictions"] = dict(Counter(r["multi"] for r in rows)); summ["single_predictions"] = dict(Counter(r["single"] for r in rows))
    summ["majority_class_baseline"] = round(max(Counter(r["reference"] for r in rows).values()) / len(rows), 3)
    json.dump({"summary": summ, "rows": rows}, open(DEC_OUT, "w"), indent=1); print(json.dumps(summ, indent=1))
    for r in rows: print(f"{r['case']:32} {r['split']:4} ref={r['reference']:13} multi={r['multi']:13} single={r['single']:13}")

if __name__ == "__main__": {"prepare": prepare, "orch": orch, "assemble": assemble}[sys.argv[1]]()
