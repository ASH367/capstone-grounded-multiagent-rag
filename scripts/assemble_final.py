"""Assemble the FINAL test sets from all 40 decisions (dev 22 + held 18).  Writes data/cases_v4/<arm>_final_<dev|held>/ and results/FINAL_SET.json.
Status per decision: SPLIT (replaced by its units) | MAIN (single unit, merits-eligible COVERED/NOT_COVERED) | SEPARATE (unsplit PARTLY_COVERED: reported on its own, not in main score) | EXCLUDED (not a coverage question).
Main-score inclusion additionally requires evidence_ok (outcome-blind word floor) - evaluated per unit."""
import json, shutil, pathlib, collections
ROOT = pathlib.Path(__file__).resolve().parent.parent; OUT = ROOT / "data/cases_v4"
info = json.load(open(ROOT / "data/council_issue_tags.json"))["cases"]
ARMS = ["A_strict", "B_gaps", "C_prior", "D_wide"]
units = json.load(open(ROOT / "results/review/units_build.json"))
split_parents = {u["parent"] for u in units}
man = []
for arm in ARMS:
    for st in ("dev", "held"):
        d = OUT / f"{arm}_final_{st}"
        if d.exists(): shutil.rmtree(d)
        d.mkdir(parents=True)
for cid, v in sorted(info.items()):
    st = v["set"]
    if cid in split_parents: status = "SPLIT"
    elif not v["include_primary"]: status = "EXCLUDED"
    elif v["coverage_label"] == "PARTLY_COVERED": status = "SEPARATE"
    else: status = "MAIN"
    man.append(dict(id=cid, parent=cid, set=st, status=status, label=v["coverage_label"], kind="case"))
    if status in ("MAIN", "SEPARATE"):
        for arm in ARMS:
            c = json.load(open(OUT / f"{arm}_{st}" / f"{cid}.json")); c["parent"] = cid; c["status"] = status
            json.dump(c, open(OUT / f"{arm}_final_{st}" / f"{cid}.json", "w"), indent=1)
for u in units:
    st = info[u["parent"]]["set"]
    for arm in ARMS:
        c = json.load(open(OUT / f"{arm}_units" / f"{u['uid']}.json")); c["status"] = "MAIN"
        json.dump(c, open(OUT / f"{arm}_final_{st}" / f"{u['uid']}.json", "w"), indent=1)
    man.append(dict(id=u["uid"], parent=u["parent"], set=st, status="MAIN", label=u["label"], kind="unit", wordsA=u["wordsA"], wordsD=u["wordsD"], evidence_ok=u["evidence_ok"]))
# evidence_ok for single cases
for m in man:
    if m["kind"] == "case" and m["status"] in ("MAIN", "SEPARATE"):
        c = json.load(open(OUT / f"D_wide_final_{m['set']}" / f"{m['id']}.json")); m.update(wordsA=c["evidence_words_A"], wordsD=c["evidence_words_D"], evidence_ok=c["evidence_ok"])
json.dump(man, open(ROOT / "results/FINAL_SET.json", "w"), indent=1)
print("status counts per set:")
for st in ("dev", "held"):
    cnt = collections.Counter((m["status"], m["kind"]) for m in man if m["set"] == st); print(" ", st, dict(cnt))
print("\nMAIN score set (status MAIN and evidence_ok):")
for st in ("dev", "held", "both"):
    xs = [m for m in man if m["status"] == "MAIN" and m.get("evidence_ok") and (st == "both" or m["set"] == st)]
    lab = collections.Counter(m["label"] for m in xs); par = len({m["parent"] for m in xs})
    mx = max(lab.values()) / len(xs)
    print(f"  {st:5s} n={len(xs):2d} from {par:2d} decisions | {dict(lab)} | majority baseline {mx:.0%}")
print("\nSEPARATE (unsplit PARTLY):", [(m["id"], m["set"], m.get("evidence_ok")) for m in man if m["status"] == "SEPARATE"])
print("MAIN but evidence floor fails:", [(m["id"], m["set"]) for m in man if m["status"] == "MAIN" and not m.get("evidence_ok")])
print("EXCLUDED:", [m["id"] for m in man if m["status"] == "EXCLUDED"])
