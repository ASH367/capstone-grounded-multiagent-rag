"""
Builds data/cases/real_iro_*.json from REAL public Texas Department of Insurance
Independent Review Organization (IRO) decisions.

Each decision (a public, name-redacted PDF) was read and its facts transcribed into the
case schema below. RULES: only what the decision states is recorded; anything not stated
(or redacted) is None -> the pipeline treats it as UNKNOWN. The IRO outcome is stored as
`reference_outcome` and is NEVER given to the pipeline as input.
Annotator mapping choices are listed in data/cases/MAPPING_NOTES.md.
NOTE: facts were extracted from the PDFs with an LLM-assisted reading (WebFetch), not by
hand-copy; verify against the source URL before citing a specific value.
"""
import json
from pathlib import Path

OUT = Path(__file__).parent.parent / "data" / "cases"
BASE = "https://www.tdi.texas.gov/medcases/iro/"

# id, path, outcome, type, regions, services[(label, level)], guidance, sedation, axial, radic,
# pain, conservative, non_facet, relief, reviewer_reason
C = [
 ("02", "2018/august/wp5414219203.pdf", "upheld", "rfa", 1, [("RFA L3",1),("RFA L4",2),("RFA L5",3)], "fluoroscopy", None, True, None,
  6, ["medications","medial branch block","right-sided rhizotomy","physical therapy"], "L4-L5 disc herniation (MRI)", [80],
  "Sustained relief >=50% for >=12 wks not met; ODG does not support repeat RFA within 6 months"),
 ("03", "2018/july/wp1750673217325.pdf", "upheld", "rfa", 2, [("RFA lumbar L5-S1",1),("facet block cervical C2-3",1),("facet block cervical C3-4",2)], None, None, True, True,
  None, ["physical therapy","chiropractic","epidural steroid injection","medial branch block","medications"], "diffuse disc herniation L5-S1", [],
  "No documentation of facet-oriented pain or positive medial branch block response"),
 ("04", "2018/january/wp5346199124.pdf", "upheld", "rfa", 1, [("RFTC L2",1),("RFTC L3",2),("RFTC L4",3)], "fluoroscopy", "anesthesia", None, False,
  None, ["medications","physical therapy","injections","immobilization","ice/heat"], "CRPS type 2 lower limb; lumbar disc displacement", [],
  "No documented plan for additional evidence-based conservative care (ODG)"),
 ("05", "2019/april/wp212148250532amen.pdf", "upheld", "diagnostic_mbb", 2, [("MBB level 1",1),("MBB level 2",2),("MBB level 3",3),("MBB level 4",4)], None, "monitored anesthesia care candidate", True, True,
  None, ["physical therapy","NSAIDs","medications","traction"], "disc herniation/bulging at multiple levels with radicular findings", None,
  "Lack of objective facet findings; radicular symptoms point to epidural not facet intervention"),
 ("06", "2019/april/wp5394253003.pdf", "overturned", "diagnostic_mbb", 1, [("MBB levels unspecified",None)], "fluoroscopy", "anesthesia", True, True,
  None, ["medications","physical therapy","heat","rest","hot/cold packs","prior injection (not helpful)"], "mild-to-moderate compression fracture with disc bulges", None,
  "Failed conservative treatment and facet syndrome evidence met ODG"),
 ("07", "2018/october/wp1750674227095.pdf", "upheld", "diagnostic_mbb", 2, [("MBB levels unspecified",None)], None, None, True, True,
  None, ["medications","ice","physical therapy (aggravated symptoms)"], "MRI: rotator cuff tears, ganglion cyst; disc narrowing, spurring, anterolisthesis", [],
  "Radicular pain; guidelines limit blocks to non-radicular facet pain"),
 ("08", "2018/july/wp5317216862.pdf", "upheld", "diagnostic_mbb", 2, [("facet block cervical C2-3",1),("facet block cervical C3-4",2),("facet block lumbar L5-S1",1)], "fluoroscopy", None, True, True,
  4, ["medications","physical therapy","cervical epidural steroid injection"], "cervical disc herniations C4-5, C5-6; malignant neoplasm left upper lobe lung", None,
  "Radiculopathy contraindicates facet blocks per ODG"),
 ("09", "2018/july/wp5301217075.pdf", "upheld", "rfa", 1, [("RFA C5-6",1),("RFA C6-7",2)], None, "sedation requested; prior blocks under total IV anesthesia", True, False,
  None, ["cervical epidural injections","medial branch blocks"], "large left C5-6 disc extrusion; cervical spondylosis; shoulder tears", [90],
  "Diagnostic block results negated by IV anesthesia; no objective improvement documented; no rehab plan"),
 ("10", "2018/july/wp2146399216702.pdf", "overturned", "diagnostic_mbb", 1, [("MBB C2-3",1),("MBB C3-4",2),("MBB C4",3)], None, "sedation (needle phobia)", True, False,
  None, ["physical therapy x12"], "C5-6 disc herniation; C6-7 and other disc bulges; facet and uncovertebral arthropathy", None,
  "Met clinical criteria for facet joint pain; sedation justified by documented needle phobia"),
 ("11", "2018/january/wp5414197498.pdf", "upheld", "diagnostic_mbb", 1, [("MBB C2-3 left",1)], None, None, True, True,
  None, ["medications","surgeries","physical therapy"], "cervical radiculopathy left C6; disc herniation C3-T1", None,
  "Predominant radicular pain; guidelines limit facet blocks to non-radicular pain"),
 ("12", "2018/march/wp5345203707.pdf", "overturned", "rfa", 1, [("RFA C4-5",1),("RFA C5-6",2)], None, None, True, False,
  None, ["diagnostics","medications","chiropractic","physical therapy","injections","medial branch block"], None, [90],
  "ODG criteria for cervical RFA met with >=70% diagnostic block response"),
 ("13", "2018/may/wp5353208520.pdf", "overturned", "diagnostic_mbb", 1, [("MBB C4-5",1),("MBB C6-7",2)], "fluoroscopy", "monitored anesthesia (CRNA)", True, True,
  None, ["physical therapy","home exercise","NSAIDs","cervical transforaminal injections"], "neural foraminal stenosis; spondylolisthesis; s/p posterior cervical fusion", [],
  "Diagnostic facet injection reasonable by deductive approach; MAC justified by needle phobia"),
 ("14", "2019/january/wp5518240955.pdf", "upheld", "therapeutic_facet", 1, [("therapeutic facet injection levels unspecified",None)], None, None, True, True,
  None, ["physical therapy","injections","medications","facet injections","radiofrequency ablation"], "lateral stenosis with encroachment", None,
  "Facet pathology and failure of conservative therapy not documented"),
 ("15", "2025/march/wp1729759414941.pdf", "overturned", "rfa", 1, [("RFA L3-4",1),("RFA L4-5",2),("RFA L5-S1",3)], None, None, True, None,
  7, ["exercise","medication","physical therapy","prior radiofrequency"], "intervertebral disc displacement; spondylosis", None,
  "Failed multimodal conservative management with facet-mediated pain on exam"),
]

def build():
    OUT.mkdir(parents=True, exist_ok=True)
    for (cid, path, outcome, typ, regions, svcs, guid, sed, axial, radic, pain, cons, nonf, relief, why) in C:
        case = {
          "case_id": f"real_iro_{cid}",
          "expected_decision": None,
          "reference_outcome": outcome,
          "source": {"type": "real public Texas DOI IRO decision (name-redacted)", "url": BASE + path,
                     "reviewer_reason": why,
                     "note": "Reviewer applied ODG/ACOEM guidelines, NOT Medicare LCD L38765. Outcome is an external reference, not an LCD ground truth."},
          "claim": {"type_of_bill": None, "emergency_dept": None, "pa_requested_before_service": None},
          "clinical": {"axial_pain": axial, "baseline_pain_nrs": pain, "disability_scale": None, "disability_score_pct": None,
                       "pain_duration_months": None, "conservative_management": cons or None,
                       "untreated_radiculopathy": radic, "non_facet_pathology": nonf, "centralized_pain_dx": None},
          "procedure": {"type": typ, "guidance": guid, "sedation": sed, "spinal_regions": regions,
                        "prior_diagnostic_mbb_relief_pct": relief,
                        "services": [{"cpt": l, "level": lv} for l, lv in svcs]},
          "documentation": {"baseline_pain_documented": True if pain is not None else None,
                            "pain_scale_used": "NRS (numeric x/10 as recorded)" if pain is not None else None,
                            "baseline_disability_documented": None, "disability_scale_used": None,
                            "conservative_records_attached": True if cons else None},
        }
        (OUT / f"real_iro_{cid}.json").write_text(json.dumps(case, indent=2))
    print(f"wrote {len(C)} cases")

if __name__ == "__main__":
    build()
