"""Build per-unit (beneficiary x service / stay) test cases from decisions where the Council ruled on each part.
Uses the FROZEN tagger/arm rules in rag/fairtest.py unchanged. Unit membership is assigned by document STRUCTURE only
(section ranges + the service named in a paragraph's first sentence), never by outcome words.
Outputs: data/cases_v4/{A_strict,D_wide}_units/<unit_id>.json  +  results/review/units_build.json (labels, council sentence, audit)."""
import json, re, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from rag import fairtest as F

OUT = ROOT / "data/cases_v4"; ARMS = dict(F.ARMS)   # all four arms, same frozen definitions
SVC = {"PT": r"\bPT\b|physical therapy", "OT": r"\bOT\b|occupational therapy", "ST": r"\bST\b|speech", "SN": r"skilled nursing|\bSN\b"}

def mk(uid, parent, label, sentence, svc_at_issue, ranges, service=None, note=""):
    return dict(uid=uid, parent=parent, label=label, council_sentence=sentence, service_at_issue=svc_at_issue, ranges=ranges, service=service, note=note)

U = []
b = "11-1343"
for ben, rng, dates, rows in [
    ("DE", (30, 47), "Oct 1-31, 2009", [("OT", "COVERED", "the Council concurs with the ALJ that the OT services were medically reasonable and necessary"),
                                       ("PT", "NOT_COVERED", "the record does not support a finding that the PT services were medically reasonable and necessary"),
                                       ("ST", "NOT_COVERED", "the record does not support a finding that D.E. experienced significant progress to justify continued skilled speech therapy")]),
    ("EM", (48, 63), "Oct 1-31, 2009", [("ST", "COVERED", "the Council concurs with the ALJ that the ST services were medically reasonable and necessary"),
                                       ("PT", "NOT_COVERED", "the record does not support a finding that the PT services were medically reasonable and necessary"),
                                       ("OT", "NOT_COVERED", "the Council finds that the PT, and OT services at issue were not medically reasonable and necessary")]),
    ("JM", (64, 78), "Aug 1-31, 2009", [("SN", "COVERED", "the SN services for dates of service at issue were skilled, and thus medically reasonable and necessary"),
                                       ("PT", "NOT_COVERED", "the Council finds the PT, OT, and ST services at issue were not medically reasonable and necessary"),
                                       ("OT", "NOT_COVERED", "the Council finds the PT, OT, and ST services at issue were not medically reasonable and necessary"),
                                       ("ST", "NOT_COVERED", "the Council finds the PT, OT, and ST services at issue were not medically reasonable and necessary")])]:
    nm = {"PT": "physical therapy", "OT": "occupational therapy", "ST": "speech-language therapy", "SN": "skilled nursing"}
    for svc, lab, sent in rows:
        U.append(mk(f"{b}__{ben}_{svc}", b, lab, sent, f"SNF {nm[svc]} furnished to one beneficiary ({ben[0]}.{ben[1]}.), {dates}", [rng], svc))
for ben, rng, dates in [("BK", (13, 18), "Oct 2004 - Aug 2005"), ("BN", (18, 25), "Oct 2004 - Feb 2005"), ("FP", (25, 32), "Sep 2004 - Nov 2004 and after")]:
    U.append(mk(f"prestige_homecare__{ben}", "prestige_homecare", "NOT_COVERED", "the home health services provided to beneficiaries B.K., B.N., and F.P. were not medically reasonable and necessary and are not covered by Medicare",
                f"Home health services furnished to one beneficiary ({ben[0]}.{ben[1]}.), {dates}", [rng]))
U.append(mk("m_10_1771__EK", "m_10_1771", "NOT_COVERED", "the physical therapy services provided to Beneficiary E.K. were not covered by Medicare", "Outpatient physical therapy furnished to one nursing-facility resident (E.K.), Sep 4-30, 2008", [(20, 30)],
            note="source text names E.M./speech therapy in the E.K. section (internal inconsistency)"))
U.append(mk("m_10_1771__JS", "m_10_1771", "NOT_COVERED", "the skilled nursing facility services provided to Beneficiaries E.M. and J.S. were not covered by Medicare", "SNF services (Part A) furnished to one resident (J.S.), Sep 1-18, 2008", [(30, 46)],
            note="no separate E.M. section in text; E.M. unit not built"))
U.append(mk("roman_eagle__stay1", "roman_eagle_memorial_home", "NOT_COVERED", "Medicare coverage for the period from September 29 through November 27, 2003 is denied because the beneficiary did not receive skilled care and her physician did not certify her need for a skilled level of care",
            "SNF services in a noncertified bed, first stay Sept 29 - Nov 27, 2003", [(6, 30), (38, 46), (96, 102)]))
U.append(mk("roman_eagle__stay2", "roman_eagle_memorial_home", "COVERED", "During the second stay, from December 11, 2003, through January 6, 2004, the beneficiary received skilled care and her physician certified her need for skilled-level care",
            "SNF services in a noncertified bed, second stay Dec 11, 2003 - Jan 6, 2004", [(6, 7), (30, 46), (102, 125)],
            note="label is coverage-criteria only: provider (not Medicare) liable because notice/consent invalid. decided with user 2026-10-30"))

# ---- added 2026-10-30 (full 40-decision scan): decisions with a separate Council verdict per beneficiary / service
for ben, rng, dates in [("IW", (16, 32), "Apr 20 - May 7, 2004"), ("JH", (16, 40), "Jul 10-23, 2004"), ("AD", (16, 46), "Mar 8-18, 2005")]:
    rg = [(16, 18), (18, 32)] if ben == "IW" else ([(16, 18), (32, 40)] if ben == "JH" else [(16, 18), (40, 46)])
    U.append(mk(f"altabates__{ben}", "altabates", "COVERED", "Services provided to this beneficiary were reasonable and necessary under applicable legal authority (numbered Council finding; ALJ reversed, claim covered)",
                f"Inpatient rehabilitation facility (IRF) services furnished to one beneficiary ({ben[0]}.{ben[1]}.), {dates}", rg))
U.append(mk("nj_dept_humanservices22__WB_SN", "nj_dept_humanservices22", "COVERED", "We therefore conclude that the four skilled nursing visits are covered services", "Four home health skilled nursing visits (intramuscular injections) for one beneficiary (W.B.), 2005", [(3, 4), (5, 21)]))
U.append(mk("nj_dept_humanservices22__WB_PT", "nj_dept_humanservices22", "COVERED", "We therefore conclude that the eleven physical therapy visits were covered services", "Eleven home health physical therapy visits for one beneficiary (W.B.), Oct 25 - Nov 29, 2005", [(3, 4), (5, 11), (21, 43)]))
U.append(mk("nj_dept_humanservices22__DW", "nj_dept_humanservices22", "COVERED", "The decision of the Medicare Appeals Council in both cases is fully favorable to the appellant", "Home health physical therapy and home health aide services for one beneficiary (D.W.), from Oct 10, 2005", [(43, 54)]))

def owners(paras, lo, hi):
    """service owners per paragraph from the service named in its first sentence, else inherited from a service header; empty = shared."""
    own, hdr = {}, set()
    for i in range(lo, hi):
        p = paras[i]; t = p["text"]
        if p["kind"] == "HEADER":
            hdr = {s for s, rx in SVC.items() if re.search(rx, t)} if re.search(r"Services$", t.strip()) else set(); continue
        if re.match(r"\d\. Beneficiary", t): hdr = set(); continue
        first = F.split_sentences(t)[0] if t else ""
        got = {s for s, rx in SVC.items() if re.search(rx, first)}
        own[i] = got or hdr
    return own

def toks(s): return F.toks(s)

def main():
    info = json.load(open(F.TAGS))["cases"]; cache = {}; report = []
    for arm in ARMS: (OUT / f"{arm}_units").mkdir(parents=True, exist_ok=True)
    for u in U:
        cid = u["parent"]
        if cid not in cache: cache[cid] = F.analyze(cid)
        paras, sents = cache[cid]; src = {}
        for st in ("dev", "held"):
            fp = F.SRC[st] / f"{cid}.json"
            if fp.exists(): src = json.load(open(fp)); break
        sel = []
        for a, z in u["ranges"]:
            own = owners(paras, a, z) if u["service"] else {}
            for s in sents:
                if not (a <= s["pi"] < z): continue
                if u["service"] and own.get(s["pi"]) and u["service"] not in own[s["pi"]]: continue
                if s not in sel: sel.append(s)
        sel.sort(key=lambda s: (s["pi"], s["si"]))
        norm = " ".join(p["text"] for p in paras)
        wA = sum(len(s["text"].split()) for s in sel if s["tag"] in ARMS["A_strict"]); wD = sum(len(s["text"].split()) for s in sel if s["tag"] in ARMS["D_wide"])
        # leak audit: kept sentences that closely echo the Council's own verdict sentence for this unit
        cs = toks(u["council_sentence"]); leaks = []
        for s in sel:
            if s["tag"] in ARMS["D_wide"]:
                tk = toks(s["text"]);
                if cs and len(tk & cs) / len(cs) >= 0.6 and len(tk) >= 5: leaks.append(s["text"][:160])
        for arm, ts in ARMS.items():
            fu = F.units(sel, ts); bad = [s["text"] for s in sel if s["tag"] in ts and s["text"] not in norm]
            c = {k: src.get(k) for k in ("domain", "docket", "cited_sections", "other_cites")}
            c.update(case_id=u["uid"], parent=u["parent"], unit_note=u["note"], service_at_issue=u["service_at_issue"], reference_outcome=u["label"], outcome_note="(unit)",
                     facts=fu, arm=arm, set=info.get(cid, {}).get("set", "units"), coverage_label=u["label"], issue_type=info.get(cid, {}).get("issue_type", ""), include_primary=1,
                     evidence_words_A=wA, evidence_words_D=wD, evidence_ok=int(wA >= F.EV_A and wD >= F.EV_D),
                     build=dict(tool="scripts/build_units.py", rules_sha=F.rules_hash(), verbatim_failures=len(bad)))
            json.dump(c, open(OUT / f"{arm}_units" / f"{u['uid']}.json", "w"), indent=1)
        report.append(dict(uid=u["uid"], parent=u["parent"], label=u["label"], council_sentence=u["council_sentence"], wordsA=wA, wordsD=wD, evidence_ok=int(wA >= F.EV_A and wD >= F.EV_D), leak_candidates=leaks, note=u["note"]))
    json.dump(report, open(ROOT / "results/review/units_build.json", "w"), indent=1)
    print(f"{'unit':28s} {'label':12s} {'A':>5s} {'D':>5s} ok leaks")
    for r in report: print(f"{r['uid']:28s} {r['label']:12s} {r['wordsA']:5d} {r['wordsD']:5d} {r['evidence_ok']:2d} {len(r['leak_candidates'])}")
    ok = [r for r in report if r["evidence_ok"]]
    print("units", len(report), "| evidence_ok", len(ok), "| ok COV", sum(r["label"] == "COVERED" for r in ok), "NOT", sum(r["label"] == "NOT_COVERED" for r in ok))

if __name__ == "__main__": main()
