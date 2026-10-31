"""Human-in-the-loop layer.  PURELY MECHANICAL and POST-HOC on saved model responses: the specialists, orchestrator and single-agent prompts are unchanged,
so every flagged case still has its 'forced' answer (needed to measure whether the flag was warranted).  Triggers are fixed here BEFORE any final run.

  CASES_DIR=data/cases_v4/A_strict_final_held INDEX_DIR=data/index_v3 RUN_DIR=<run dir with resp_*.json + retrieved.json> python3 -m rag.hitl [--notes llm --backend openai --model ...]

PRIMARY rule - triggers (any one sends the case to a human):
  THIN        facts shown to the model have < THIN_WORDS words                                  (both systems)
  UNGROUNDED  fewer than MIN_VALID mechanically valid findings (quote verbatim in retrieved passage AND case_fact verbatim in facts)  (both systems)
  (SELF_UNKNOWN: final reason itself says UNKNOWN - the prompt's own vocabulary. Reported as a SECOND variant 'flag_self', not part of the primary rule.)
  ERROR       a model call failed / unparsable output                                           (both systems)
  ALL_UNKNOWN all three specialists return UNKNOWN                                              (multi only)
  DISAGREE    one specialist SUPPORTS_COVERAGE and another DOES_NOT_SUPPORT                      (multi only)
Writes <RUN_DIR>/hitl.json and <RUN_DIR>/review/<case>.md (full package + note) for every case flagged under either system."""
import json, os, re, sys, pathlib, hashlib, argparse

THIN_WORDS = 100
MIN_VALID = 2

def rules_hash(): return hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:16]

def _valid(P, findings, cid, role):
    ok, bad = P.check([f for f in findings if isinstance(f, dict)], cid, role); return ok, bad

def evaluate(P, RUN):
    R = {k: {x["case_id"]: x for x in json.load(open(RUN / f"resp_{k}.json"))} for k in ("elig", "nec", "doc", "base", "orch")}
    out = {}
    for cid, c in P.cases.items():
        if not all(cid in R[k] for k in R): continue
        E, N, D, B, O = (R[k][cid] for k in ("elig", "nec", "doc", "base", "orch"))
        words = sum(len(x.split()) for x in c["facts"]); ver = [E.get("verdict", "UNKNOWN"), N.get("verdict", "UNKNOWN"), D.get("verdict", "UNKNOWN")]
        vm = sum(_valid(P, s.get("findings", []), cid, role)[0] for s, role in ((E, "elig"), (N, "nec"), (D, "doc")))
        vs = _valid(P, B.get("findings", []), cid, "base")[0]
        mt, st = [], []
        if words < THIN_WORDS: mt.append("THIN"); st.append("THIN")
        if vm < MIN_VALID: mt.append("UNGROUNDED")
        if vs < MIN_VALID: st.append("UNGROUNDED")
        smu = bool(re.search(r"\bUNKNOWN\b", O.get("reason", "") or "")); ssu = bool(re.search(r"\bUNKNOWN\b", B.get("reason", "") or ""))   # self-flag variant, reported separately (NOT part of the primary rule)
        if any("error" in x for x in (E, N, D, O)) or str(O.get("reason", "")).startswith("ERROR") or O.get("decision") not in ("COVERED", "NOT_COVERED", "PARTLY_COVERED"): mt.append("ERROR")
        if "error" in B or str(B.get("reason", "")).startswith("ERROR") or B.get("decision") not in ("COVERED", "NOT_COVERED", "PARTLY_COVERED"): st.append("ERROR")
        if all(v == "UNKNOWN" for v in ver): mt.append("ALL_UNKNOWN")
        if "SUPPORTS_COVERAGE" in ver and "DOES_NOT_SUPPORT" in ver: mt.append("DISAGREE")
        out[cid] = dict(facts_words=words, specialist_verdicts=ver, valid_findings_multi=vm, valid_findings_single=vs,
                        multi=dict(answer=O.get("decision"), flag=bool(mt), triggers=mt, self_unknown=smu, flag_self=bool(mt) or smu), single=dict(answer=B.get("decision"), flag=bool(st), triggers=st, self_unknown=ssu, flag_self=bool(st) or ssu))
    return out

NOTE_PROMPT = ("You are preparing a hand-off note for a human reviewer. A Medicare coverage-review system could not safely decide this case. Use ONLY the material below; do not add outside facts. "
               "Reply with JSON only: {{\"why_flagged\": \"1-2 sentences\", \"missing\": [\"specific record items or policy points that were not settled\"], "
               "\"found\": [{{\"point\": \"...\", \"fact_quote\": \"copied EXACTLY from the case facts, max 25 words\"}}], \"request_document\": \"the specific document or information that would settle it\"}}\n\n"
               "<flag_reasons>{trig}</flag_reasons>\n<case_facts>\n{facts}\n</case_facts>\n<specialists>\n{spec}\n</specialists>\n<final_outputs>\n{fin}\n</final_outputs>")

def package(P, RUN, cid, h, resp, note=None):
    c = P.cases[cid]; ids = json.load(open(RUN / "retrieved.json"))[cid]
    L = [f"# Review package: {cid}", f"arm facts shown to the system; service at issue: {c.get('service_at_issue')}", "",
         "## Why this case was sent to a human", f"- multi-agent: {'FLAGGED ' + ', '.join(h['multi']['triggers']) if h['multi']['flag'] else 'decided (' + str(h['multi']['answer']) + ')'}",
         f"- single-agent: {'FLAGGED ' + ', '.join(h['single']['triggers']) if h['single']['flag'] else 'decided (' + str(h['single']['answer']) + ')'}"]
    if note:
        L += ["", "## Reviewer note", f"**Why:** {note.get('why_flagged', '')}", "**Missing / unsettled:**"] + [f"- {m}" for m in note.get("missing", [])] + ["**What the system did find (quotes verified against the facts):**"]
        L += [f"- {f.get('point', '')}: \"{f.get('fact_quote', '')}\"" for f in note.get("found", [])] + [f"**Document that would settle it:** {note.get('request_document', '')}"]
    L += ["", "## Full case as the system saw it (facts)"] + [f"[{i+1}] {x}" for i, x in enumerate(c["facts"])]
    L += ["", "## What each system said (the answer is NOT the gold label; the reviewer decides)"]
    for nm, k in (("Eligibility agent", "elig"), ("Medical-necessity agent", "nec"), ("Documentation agent", "doc")):
        r = resp[k][cid]; L += [f"### {nm}: {r.get('verdict')}"] + [f"- {f.get('claim')}  [passage {f.get('passage_id')}: \"{f.get('quote')}\"]" for f in r.get("findings", []) if isinstance(f, dict)]
    L += [f"### Orchestrator: {resp['orch'][cid].get('decision')}", resp["orch"][cid].get("reason", ""), f"### Single agent: {resp['base'][cid].get('decision')}", resp["base"][cid].get("reason", ""), "", "## Manual passages retrieved"]
    seen = set()
    for role in ids:
        for pid in ids[role]:
            if pid in seen: continue
            seen.add(pid); L += [f"### passage {pid} ({P.chunks[pid]['label']})", P.chunks[pid]["text"]]
    return "\n".join(L)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--notes", choices=["none", "llm"], default="none"); ap.add_argument("--backend"); ap.add_argument("--model"); a = ap.parse_args()
    from rag import pipeline as P
    RUN = P.RUN; res = evaluate(P, RUN)
    resp = {k: {x["case_id"]: x for x in json.load(open(RUN / f"resp_{k}.json"))} for k in ("elig", "nec", "doc", "base", "orch")}
    be = None
    if a.notes == "llm":
        from rag import llm; be = llm.get(a.backend, a.model)
    (RUN / "review").mkdir(exist_ok=True); nflag = 0
    for cid, h in res.items():
        if not (h["multi"]["flag"] or h["single"]["flag"]): continue
        nflag += 1; note = None
        if be:
            facts = "\n".join(f"[{i+1}] {x}" for i, x in enumerate(P.cases[cid]["facts"]))
            spec = "\n".join(f"{nm}: {resp[k][cid].get('verdict')} | " + " ; ".join(str(f.get('claim')) for f in resp[k][cid].get("findings", []) if isinstance(f, dict)) for nm, k in (("Eligibility", "elig"), ("Necessity", "nec"), ("Documentation", "doc")))
            fin = f"orchestrator: {resp['orch'][cid].get('reason')}\nsingle: {resp['base'][cid].get('reason')}"
            try:
                text, _ = be.call(NOTE_PROMPT.format(trig=json.dumps({"multi": h["multi"]["triggers"], "single": h["single"]["triggers"]}), facts=facts, spec=spec, fin=fin)); note = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
                ft = re.sub(r"\s+", " ", " ".join(P.cases[cid]["facts"])).lower()
                note["found"] = [f for f in note.get("found", []) if isinstance(f, dict) and re.sub(r"\s+", " ", f.get("fact_quote", "")).lower() in ft]   # drop any 'found' item whose quote is not verbatim in the facts
            except Exception as e: note = {"why_flagged": f"(note generation failed: {e})", "missing": [], "found": [], "request_document": ""}
        (RUN / "review" / f"{cid}.md").write_text(package(P, RUN, cid, h, resp, note))
    json.dump(dict(rules_sha=rules_hash(), THIN_WORDS=THIN_WORDS, MIN_VALID=MIN_VALID, cases=res), open(RUN / "hitl.json", "w"), indent=1)
    nm = sum(h["multi"]["flag"] for h in res.values()); ns = sum(h["single"]["flag"] for h in res.values())
    print(f"HITL {RUN}: n={len(res)} flagged multi={nm} single={ns} either={nflag}; rules {rules_hash()}")
