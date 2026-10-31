"""Four alternative agent designs, evaluated on the held-out cases (file-based runs, like rag/pipeline.py).
  A  planner -> one agent per component -> rule-based combination (no LLM orchestrator)
  B  advocate vs adversary -> judge
  C  generate (single-agent output) -> verifier labels -> revise
  D  compute-matched baseline: majority vote of the single-agent runs
Usage (env: CASES_DIR=data/cases_v3_heldout_clean INDEX_DIR=data/index_v3 RUN_DIR=results/designs):
  python3 -m rag.designs buildA1 | buildA2 | buildB1 | buildB2 | buildC | score
Prompts go to results/designs/<design>_r<k>/ ; responses are written next to them as resp_*.json."""
import json, sys, os, pathlib, collections, statistics as st
from rag import pipeline as P
OUT = pathlib.Path("results/designs"); OUT.mkdir(parents=True, exist_ok=True)
RUNS = (1, 2, 3)
BASE_RET = json.load(open("results/heldout_r1/retrieved.json"))
def passages_for(cid, n=8): return [P.by_id[i] if hasattr(P, "by_id") else i for i in BASE_RET[cid]["base"][:n]]
idx_of = {c["chunk_id"]: i for i, c in enumerate(P.chunks)}
def ptext(chunk_ids): return P.passages_text([idx_of[i] for i in chunk_ids])
def save(name, obj): d = OUT / name; d.mkdir(parents=True, exist_ok=True); return d
FIND = '"findings": [{"claim": "...", "passage_id": <int>, "quote": "...", "case_fact": "..."}]'
def wr(d, fn, obj): json.dump(obj, open(d / fn, "w"), indent=1)

def buildA1():   # planner prompts (same for every run)
    items = []
    for cid, c in P.cases.items():
        items.append({"case_id": cid, "prompt": "You are the Planner in a Medicare coverage-review system. Read the case facts and split the claim at issue into separable components that could each be covered or not covered on their own (for example distinct services, distinct time periods or visits, or distinct items). If the claim cannot be split, return exactly one component. At most 4 components. Use ONLY the case facts.\n\n"
            f"<case_facts>\n{P.facts_text(c)}\n</case_facts>\n\nReply with JSON only: {{\"components\": [{{\"name\": \"short name\", \"description\": \"what exactly this component is\"}}]}}"})
    for r in RUNS: d = save(f"A_r{r}", None); wr(d, "prompts_plan.json", items)
def buildA2():   # component prompts from each run's plan
    for r in RUNS:
        d = OUT / f"A_r{r}"; plans = {x["case_id"]: x for x in json.load(open(d / "resp_plan.json"))}; items = []
        for cid, c in P.cases.items():
            comps = plans[cid]["components"][:4] or [{"name": "whole claim", "description": "the whole claim"}]
            for k, comp in enumerate(comps):
                ids = P.retrieve(" ".join(c["facts"]) + " " + comp["description"], P.DOMDOC[c["domain"]], 6)
                items.append({"case_id": cid, "comp": k, "name": comp["name"], "prompt": f"You are a Component Reviewer in a Medicare coverage-review system. Decide ONLY this component of the claim: {comp['name']} - {comp['description']}\n{P.RULES}\n\n<case_facts>\n{P.facts_text(c)}\n</case_facts>\n\n<policy_passages>\n{P.passages_text(ids)}\n</policy_passages>\n\n"
                    f'Reply with JSON only: {{"decision": "COVERED" | "NOT_COVERED", "reason": "one sentence", {FIND}}}'})
        wr(d, "prompts_comp.json", items); print(r, len(items), "component prompts")
def buildB1():
    for side, task, pos in (("adv", "Make the strongest honest case that Medicare covers the service, in whole or in part.", "COVERED" + '" | "' + "PARTLY_COVERED"),
                            ("opp", "Make the strongest honest case that Medicare does NOT cover the service, in whole or in part.", "NOT_COVERED" + '" | "' + "PARTLY_COVERED")):
        items = []
        for cid, c in P.cases.items():
            items.append({"case_id": cid, "prompt": f"You are the {'Coverage Advocate' if side=='adv' else 'Coverage Skeptic'} in a Medicare coverage-review debate.\nTask: {task} Do not invent facts or quotes; if the best honest case is weak, say so.\n{P.RULES}\n\n<case_facts>\n{P.facts_text(c)}\n</case_facts>\n\n<policy_passages>\n{ptext(BASE_RET[cid]['base'])}\n</policy_passages>\n\n"
                f'Reply with JSON only: {{"position": "{pos}", "argument": "two to four sentences", {FIND}}}'})
        for r in RUNS: d = save(f"B_r{r}", None); wr(d, f"prompts_{side}.json", items)
def block(nm, resp): return f"<{nm}>\nPosition: {resp.get('position')}\nArgument: {resp.get('argument')}\n" + "\n".join(f"- {f['claim']} (passage {f['passage_id']}: \"{f['quote']}\")" for f in resp.get("findings", [])) + f"\n</{nm}>\n"
def buildB2():
    for r in RUNS:
        d = OUT / f"B_r{r}"; A = {x["case_id"]: x for x in json.load(open(d / "resp_adv.json"))}; O = {x["case_id"]: x for x in json.load(open(d / "resp_opp.json"))}; items = []
        for cid, c in P.cases.items():
            items.append({"case_id": cid, "prompt": "You are the Judge in a Medicare coverage-review debate. An advocate and a skeptic have each argued the case. Decide using ONLY the case facts and the cited findings; do not use outside knowledge. COVERED = coverage is supported; NOT_COVERED = it is not; PARTLY_COVERED = part of the service or period is covered and part is not. Also say whether the two sides substantially disagree.\n\n"
                f"<case_facts>\n{P.facts_text(c)}\n</case_facts>\n\n{block('advocate', A[cid])}\n{block('skeptic', O[cid])}\n"
                'Reply with JSON only: {"decision": "COVERED" | "NOT_COVERED" | "PARTLY_COVERED", "reason": "one or two sentences", "sides_disagree": true | false, "passage_ids": [<int>, ...]}'})
        wr(d, "prompts_judge.json", items)
def buildC():
    chunks = {c["chunk_id"]: c for c in P.chunks}
    for r in RUNS:
        base = {x["case_id"]: x for x in json.load(open(f"results/heldout_r{r}/resp_base.json"))}
        ver = collections.defaultdict(dict)
        for x in json.load(open(f"results/verifier/heldout_r{r}_output.json")):
            _, s, role, case, i = x["id"].split("|")
            if s == "single": ver[case][int(i)] = (x["label"], x.get("reason", ""))
        items = []
        for cid, c in P.cases.items():
            b = base[cid]; fl = ""
            for i, f in enumerate(b.get("findings", [])):
                lab, why = ver[cid].get(i, ("SUPPORTED", ""))
                fl += f"[{i}] claim: {f['claim']} | passage {f['passage_id']}: \"{f['quote']}\" | verifier: {lab} ({why})\n"
            items.append({"case_id": cid, "prompt": "You are the Reviser in a Medicare coverage-review system. A reviewer produced a decision and findings; a Verifier checked each finding against its quoted case fact and policy text. Remove or fix every finding the Verifier marked PARTLY or NOT_SUPPORTED (you may cite other passages below), then give the final decision. You may change the decision if the supported findings point elsewhere, but use ONLY the case facts and passages below.\n"
                f"{P.RULES}\n\n<case_facts>\n{P.facts_text(c)}\n</case_facts>\n\n<policy_passages>\n{ptext(BASE_RET[cid]['base'])}\n</policy_passages>\n\n<original_decision>{b.get('decision')}: {b.get('reason')}</original_decision>\n<findings_with_verifier_labels>\n{fl}</findings_with_verifier_labels>\n\n"
                f'Reply with JSON only: {{"decision": "COVERED" | "NOT_COVERED" | "PARTLY_COVERED", "reason": "one or two sentences", {FIND}}}'})
        d = save(f"C_r{r}", None); wr(d, "prompts_revise.json", items)
def aggregate_A(comps):
    ds = [x["decision"] for x in comps]
    return "COVERED" if all(d == "COVERED" for d in ds) else "NOT_COVERED" if all(d == "NOT_COVERED" for d in ds) else "PARTLY_COVERED"
def score():
    MAP = P.MAP; ref = {cid: MAP[c["reference_outcome"]] for cid, c in P.cases.items()}; res = collections.defaultdict(lambda: collections.defaultdict(list)); calls = {}
    def dec(r, k): return json.load(open(f"results/heldout_r{r}/decisions.json"))
    for r in RUNS:
        rows = {x["case"]: x for x in dec(r, 0)["rows"]}
        for cid in ref: res["multi (current, 4 calls)"][r].append(rows[cid]["multi"] == ref[cid]); res["single (1 call)"][r].append(rows[cid]["single"] == ref[cid])
        d = OUT / f"A_r{r}"
        if (d / "resp_comp.json").exists():
            C = collections.defaultdict(list)
            for x in json.load(open(d / "resp_comp.json")): C[x["case_id"]].append(x)
            for cid in ref: res["A planner+components+rule"][r].append(aggregate_A(C[cid]) == ref[cid])
            calls["A planner+components+rule"] = round(sum(len(v) for v in C.values()) / len(C) + 1, 1)
        d = OUT / f"B_r{r}"
        if (d / "resp_judge.json").exists():
            J = {x["case_id"]: x for x in json.load(open(d / "resp_judge.json"))}
            for cid in ref: res["B advocate/skeptic+judge (3 calls)"][r].append(J[cid]["decision"] == ref[cid])
        d = OUT / f"C_r{r}"
        if (d / "resp_revise.json").exists():
            R = {x["case_id"]: x for x in json.load(open(d / "resp_revise.json"))}
            for cid in ref: res["C generate+verify+revise (3 calls)"][r].append(R[cid]["decision"] == ref[cid])
    maj = []
    for cid in ref:
        v = collections.Counter(next(x for x in dec(r, 0)["rows"] if x["case"] == cid)["single"] for r in RUNS).most_common(1)[0][0]; maj.append(v == ref[cid])
    lines = []
    for name, runs in res.items():
        a = [sum(v) for v in runs.values()]; lines.append(f"{name:42s} per-run correct {a} of {len(ref)}  mean {st.mean(a):.1f} ({st.mean(a)/len(ref):.0%})  SD {st.pstdev(a):.1f}")
    lines.append(f"{'D majority of 3 single runs (3 calls)':42s} correct {sum(maj)} of {len(ref)} ({sum(maj)/len(ref):.0%})")
    print("\n".join(lines)); print("avg calls/case A:", calls.get("A planner+components+rule"))
if __name__ == "__main__": globals()[sys.argv[1]]()
