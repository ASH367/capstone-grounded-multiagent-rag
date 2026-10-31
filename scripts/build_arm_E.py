#!/usr/bin/env python3
"""POST-HOC exploratory arm E_aljfacts (added AFTER the frozen rules were applied to the held-out set; rag/fairtest.py is untouched).
Why: when the Council simply adopts the ALJ, the patient facts are narrated inside the ALJ-recital paragraphs, which arms A-D drop wholesale.
E = D + narrative sentences from those recitals that carry a date / number / record-source anchor and no evaluation, gap, law, procedure or Council cue.
It is reported separately and labelled exploratory; it never replaces the pre-registered arms.
  python3 scripts/build_arm_E.py
"""
import collections, glob, json, os, re, sys
sys.path.insert(0, ".")
from rag import fairtest as F

BLOCK = [F.EVAL, F.EVAL_STRONG, F.GAP, F.REASON, F.PROC, F.PROC_SOFT, F.LAW_CI, F.LAW_CS, F.COUNCIL, F.DISP, F.LAWSTMT, F.META]


def alj_fact(s):
    t = F.core(s["text"])
    return s["tag"] == "PRIOR_ALJ_CONT" and F.STRICT.search(t) and not F.cite_only(s["text"]) and len(t.split()) >= 6 and not any(r.search(t) or r.search(s["text"]) for r in BLOCK)


if __name__ == "__main__":
    info = F.tags_info(); report = collections.defaultdict(lambda: collections.Counter())
    for st in ("dev", "held"):
        d = F.OUT / f"E_aljfacts_{st}"; d.mkdir(parents=True, exist_ok=True)
        aud = collections.defaultdict(list)
        for r in json.load(open(F.AUDIT[st])):
            if r["label"] in ("ADJUDICATOR_FINDING", "MIXED") and r.get("leak_text"): aud[r["case_id"]].append(r)
        for cid in sorted(k for k, v in info.items() if v["set"] == st):
            sents = json.load(open(F.OUT / "tags" / f"{cid}.json"))["sentences"]
            n_new = 0
            for s in sents:
                if alj_fact(s): s["tag"] = "ALJ_FACT"; n_new += 1
            ts = F.ARMS["D_wide"] | {"ALJ_FACT"}; tsA = F.ARMS["A_strict"] | {"ALJ_FACT"}
            norm = " ".join(p["text"] for p in F.paragraphs(open(F.RAW / f"{cid}.txt", encoding="utf-8", errors="replace").read()))
            bad = [s["text"] for s in sents if s["tag"] in ts and s["text"] not in norm]
            tmpl = json.load(open(F.OUT / f"D_wide_{st}" / f"{cid}.json"))
            wA = sum(len(x["text"].split()) for x in sents if x["tag"] in tsA); wD = sum(len(x["text"].split()) for x in sents if x["tag"] in ts)
            tmpl.update(facts=F.units(sents, ts), arm="E_aljfacts", evidence_words_A=wA, evidence_words_D=wD, evidence_ok=int(wA >= F.EV_A and wD >= F.EV_D), alj_fact_sentences=n_new,
                        build=dict(tool="scripts/build_arm_E.py (post-hoc, exploratory)", rules_sha=F.rules_hash(), verbatim_failures=len(bad)))
            json.dump(tmpl, open(d / f"{cid}.json", "w"), indent=1)
            kept = [s["text"] for s in sents if s["tag"] in ts]
            good = []
            for f in json.load(open(F.SURG[st] / f"{cid}.json"))["facts"]: good += [g for g in F.split_sentences(f) if len(g.split()) >= 6]
            report[st]["cases"] += 1; report[st]["alj_fact_sentences"] += n_new; report[st]["words"] += sum(len(k.split()) for k in kept); report[st]["good"] += len(good)
            report[st]["good_hit"] += sum(1 for g in good if any(F.recall(g, k) >= 0.8 for k in kept)); report[st]["verbatim_failures"] += len(bad)
            report[st]["leak_facts"] += len(aud[cid]); report[st]["evidence_ok"] += tmpl["evidence_ok"]
            for r in aud[cid]:
                parts = [p for p in re.split(r"\s*(?:\.\.\.|…)\s*", r["leak_text"]) if len(p.strip()) > 8] or [r["leak_text"]]
                report[st]["leak_hit"] += int(any(F.recall(p, k) >= 0.6 for p in parts for k in kept))
    for st, c in report.items():
        print(st, dict(c), f"recall {100*c['good_hit']/max(1,c['good']):.0f}%")
    json.dump({k: dict(v) for k, v in report.items()}, open("results/review/fairtest_audit_E_aljfacts.json", "w"), indent=1)
