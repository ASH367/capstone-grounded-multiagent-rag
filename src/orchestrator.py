"""
Milestone 1 - Orchestrator.

Runs the three agents and maps the result to the decision vocabulary defined in
CMS OPD PA FAQ Q23: provisional affirmation / provisional partial affirmation /
non-affirmation. Services are decided individually: case-level failures sink every
service; the LCD's 1-2 level limit (LCD Limitation 7, FAQ Q61) sinks level >= 3.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from agents import EligibilityAgent, MedicalNecessityAgent, DocumentationAgent
from retriever import PolicyRetriever

ROOT = Path(__file__).parent.parent
MAX_COVERED_LEVEL = 2


def _crit_dict(c):
    return {"criterion": c.name, "status": c.status, "evidence": c.detail,
            "citation": c.citations[0] if c.citations else None}


def run_case(case: dict, retriever: PolicyRetriever) -> dict:
    agents = [EligibilityAgent(retriever), MedicalNecessityAgent(retriever), DocumentationAgent(retriever)]
    findings = [a.run(case) for a in agents]
    verdicts = [f.verdict for f in findings if f.verdict != "N/A"]
    case_status = ("NOT_MET" if "NOT_MET" in verdicts else "UNKNOWN" if "UNKNOWN" in verdicts else "MET")

    lim7 = retriever.retrieve("one to 2 levels allowed per session three or 4 level procedures not medically necessary non-covered",
                              doc_filter="LCD_L38765_v27", top_k=1)[0]
    faq61 = retriever.retrieve("prior authorization 64492 64495 facet joint injections third additional level",
                               doc_filter="CMS_OPD_PA_FAQ_2024-11-14", top_k=1)[0]
    services = []
    for s in case["procedure"]["services"]:
        reasons, cites = [], []
        status = case_status
        if case_status == "NOT_MET":
            reasons.append("case-level criteria not met (see agent findings)")
        elif case_status == "UNKNOWN":
            reasons.append("record does not state one or more required facts")
        lvl = s["level"]
        if lvl is not None and lvl > MAX_COVERED_LEVEL:
            status = "NOT_MET"
            reasons.append(f"level {lvl} exceeds the 1-2 level limit")
            cites += [lim7["chunk_id"], faq61["chunk_id"]]
        elif lvl is None and status == "MET":
            status = "UNKNOWN"
            reasons.append("number of levels not stated")
        decision = {"MET": "AFFIRM", "NOT_MET": "NON-AFFIRM", "UNKNOWN": "INSUFFICIENT INFORMATION"}[status]
        services.append({"cpt": s["cpt"], "level": lvl, "decision": decision,
                         "reasons": reasons, "cited_chunks": cites})

    ds = [s["decision"] for s in services]
    n_aff, n_non = ds.count("AFFIRM"), ds.count("NON-AFFIRM")
    if n_aff == len(ds):
        decision = "PROVISIONAL AFFIRMATION"
    elif n_non == len(ds):
        decision = "NON-AFFIRMATION"
    elif n_aff and n_non and n_aff + n_non == len(ds):
        decision = "PROVISIONAL PARTIAL AFFIRMATION"
    elif n_non and not n_aff:
        decision = "NON-AFFIRMATION"   # at least one hard failure and nothing affirmable
    else:
        decision = "INSUFFICIENT INFORMATION"

    by_id = {c["chunk_id"]: c for c in retriever.chunks}
    cites = [c.citations[0] for f in findings for c in f.criteria if c.citations]
    grounded = sum(1 for c in cites if c["chunk_id"] in by_id and by_id[c["chunk_id"]]["text"].startswith(c["snippet"]))
    all_crits = [c for f in findings for c in f.criteria]
    return {
        "case_id": case["case_id"],
        "source": case.get("source", {}).get("citation") or case.get("source", {}).get("url"),
        "reference_outcome": case.get("reference_outcome"),
        "expected_decision": case.get("expected_decision"),
        "decision": decision,
        "services": services,
        "agents": [{"agent": f.agent, "verdict": f.verdict,
                    "criteria": [_crit_dict(c) for c in f.criteria]} for f in findings],
        "groundedness_check": {"citations": len(cites), "verified_in_index": grounded},
        "retrieval_check": {"criteria": len(all_crits),
                            "hit_at_1": sum(c.retrieval_hit_at_1 for c in all_crits),
                            "hit_at_3": sum(c.retrieval_hit_at_3 for c in all_crits)},
    }


def main(cases_dir=None, out_name="milestone1_output.json"):
    retriever = PolicyRetriever()
    cdir = Path(cases_dir) if cases_dir else ROOT / "data" / "cases"
    results = [run_case(json.loads(p.read_text()), retriever) for p in sorted(cdir.glob("*.json"))]
    n = len(results)
    crit = sum(r["retrieval_check"]["criteria"] for r in results)
    summary = {
        "cases": n,
        "citation_groundedness": f"{sum(r['groundedness_check']['verified_in_index'] for r in results)}/"
                                 f"{sum(r['groundedness_check']['citations'] for r in results)}",
        "retrieval_hit_at_1": f"{sum(r['retrieval_check']['hit_at_1'] for r in results)}/{crit}",
        "retrieval_hit_at_3": f"{sum(r['retrieval_check']['hit_at_3'] for r in results)}/{crit}",
        "decision_counts": {},
    }
    for r in results:
        summary["decision_counts"][r["decision"]] = summary["decision_counts"].get(r["decision"], 0) + 1
    # agreement with the real IRO outcome (external reference; different guideline set - see README)
    ref = [r for r in results if r["reference_outcome"]]
    if ref:
        table = {}
        for r in ref:
            key = (r["reference_outcome"], r["decision"])
            table[f"IRO {r['reference_outcome']} -> system {r['decision']}"] = table.get(
                f"IRO {r['reference_outcome']} -> system {r['decision']}", 0) + 1
        summary["vs_real_IRO_outcome"] = table
    out = {"summary": summary, "results": results}
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / out_name).write_text(json.dumps(out, indent=2))
    for r in results:
        print(f"{r['case_id']}: {r['decision']}  [IRO: {r['reference_outcome'] or '-'}]")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    import sys
    main(*sys.argv[1:])
