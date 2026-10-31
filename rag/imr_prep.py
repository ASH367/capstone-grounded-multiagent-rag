"""Pilot: turn California IMR (Independent Medical Review) findings into cases with FACTS ONLY (no reviewer conclusion).
Source: data/raw/ca_imr/ca_imr_snf_hh.csv (CA DMHC open data via Kaggle copy; LICENSE NOT YET CHECKED: do not commit/publish before checking).
Label mapping (fixed before any run): 'Overturned Decision of Health Plan' -> favorable (COVERED); 'Upheld Decision of Health Plan' -> unfavorable (NOT_COVERED).
Steps: (1) cut 'Final Result' and 'Credentials' sections mechanically; (2) LLM extracts patient/service/course facts only, no judgments;
(3) mechanical regex flags conclusion words; (4) second LLM audit asks whether any fact states/implies the decision. Review flagged cases by hand before use.
  python3 -m rag.imr_prep --dry                      # no model calls: shows cleaned text + sample
  python3 -m rag.imr_prep --backend openai --model anthropic/claude-sonnet-5.5 --audit-model openai/gpt-4.1 --n 10 --out data/cases_imr_pilot"""
import argparse, json, pathlib, re, collections
import pandas as pd
from rag import llm

CAT = "Rehabilitation Services - Skilled Nursing Facility - Inpatient"
CUT = re.compile(r"\s*Final Result\s*:.*$|\s*Credentials/Qualifications\s*:.*$", re.S | re.I)
HEAD = re.compile(r"^\s*Nature of Statutory Criteria/Case Summary\s*:\s*", re.I)
LEAK = re.compile(r"medically necessary|not medically|medical necessity|not necessary|appropriate|upheld|overturn|denial|should be|not indicated|medically indicated|justified|warranted|reasonable|meets? criteria|did not meet|does not meet|the reviewer|physician reviewer|therefore|accordingly|all told", re.I)

def clean(t): return HEAD.sub("", CUT.sub("", str(t))).strip()

EXTRACT = ("You prepare case records for a research study. Below is a medical reviewer's write-up about a request for skilled nursing facility (SNF) care.\n"
 "Extract ONLY the factual record about the patient and the request: age/sex, diagnoses, hospital stay or events, functional status, services the patient was receiving (nursing, therapy, wound care...), how the patient was progressing, and what was requested.\n"
 "STRICT RULES: Do NOT include the reviewer's opinion, reasoning, judgment, or conclusion, and do NOT include whether care was necessary, appropriate, skilled, custodial, or could be provided elsewhere. Do NOT include statements that the patient plateaued or improved if that is the reviewer's assessment; include only the underlying measurements or events. Do not add anything that is not in the text. Write each fact as one short plain sentence.\n"
 'Reply with JSON only: {"service_requested": "one short phrase", "facts": ["...", "..."]}\n\n<writeup>\n%s\n</writeup>')
AUDIT = ("Below are facts about a patient who requested skilled nursing facility care. A reviewer later decided whether the request was medically necessary.\n"
 "List any fact that states or strongly implies that decision or the reviewer's reasoning (e.g. says care was unnecessary, custodial, appropriate, or meets/does not meet criteria). Plain clinical facts are NOT leaks.\n"
 'Reply with JSON only: {"leaks": ["exact fact text", ...]}\n\n%s')

def main(a):
    d = pd.read_csv("data/raw/ca_imr/ca_imr_snf_hh.csv"); d = d[d["Treatment Category"] == CAT].copy()
    d["clean"] = d["Findings"].map(clean)
    ups = d[d["Determination"].str.startswith("Upheld")].sample(a.n, random_state=7); ovr = d[d["Determination"].str.startswith("Overturned")].sample(a.n, random_state=7)
    pick = pd.concat([ups, ovr]).sample(frac=1, random_state=3)
    if a.dry:
        for _, r in pick.head(2).iterrows(): print(r["Reference ID"], r["Determination"], "\n", r["clean"][:900], "\n")
        print("cleaned length median", d["clean"].str.len().median()); return
    be = llm.get(a.backend, a.model); ab = llm.get(a.backend, a.audit_model or a.model); out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True); rep = []
    for _, r in pick.iterrows():
        cid = f"imr_{r['Reference ID']}"
        try:
            j = llm.extract_json(be.call(EXTRACT % r["clean"])[0]); facts = [f for f in j.get("facts", []) if isinstance(f, str)]
            la = llm.extract_json(ab.call(AUDIT % "\n".join(f"- {f}" for f in facts))[0]).get("leaks", [])
        except Exception as e: print(cid, "ERROR", e); continue
        rx = [f for f in facts if LEAK.search(f)]
        fav = r["Determination"].startswith("Overturned")
        case = {"case_id": cid, "domain": "snf", "service_at_issue": j.get("service_requested", "SNF care"), "facts": facts, "reference_outcome": "favorable" if fav else "unfavorable",
                "outcome_note": r["clean"], "cited_sections": [], "other_cites": [], "scope": "included", "source": "CA DMHC IMR", "regex_flagged": rx, "audit_flagged": la}
        json.dump(case, open(out / f"{cid}.json", "w"), indent=1); rep.append({"case_id": cid, "n_facts": len(facts), "regex": len(rx), "audit": len(la), "outcome": case["reference_outcome"]})
        print(cid, case["reference_outcome"], len(facts), "facts | regex flags", len(rx), "| audit flags", len(la), flush=True)
    c = collections.Counter(bool(x["regex"] or x["audit"]) for x in rep); print("cases with any flag:", c[True], "of", len(rep)); json.dump(rep, open(out / "_prep_report.json", "w"), indent=1)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--backend", default="openai"); ap.add_argument("--model"); ap.add_argument("--audit-model", dest="audit_model"); ap.add_argument("--n", type=int, default=10); ap.add_argument("--out", default="data/cases_imr_pilot"); ap.add_argument("--dry", action="store_true"); main(ap.parse_args())
