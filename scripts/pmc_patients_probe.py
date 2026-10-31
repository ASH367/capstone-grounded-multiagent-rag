"""Probe PMC-Patients (public, CC BY-NC-SA 4.0; real published case-report narratives) for rich notes that mention post-acute care.
Run on YOUR Mac from the repo root. Downloads the 545 MB CSV once into data/raw/pmc_patients/ (do NOT commit it). No model calls.
  python3 scripts/pmc_patients_probe.py"""
import csv, sys, re, json, pathlib, statistics, collections, urllib.request
URL = "https://huggingface.co/datasets/zhengyun21/PMC-Patients/resolve/main/PMC-Patients.csv"
P = pathlib.Path("data/raw/pmc_patients/PMC-Patients.csv"); P.parent.mkdir(parents=True, exist_ok=True)
if not P.exists():
    print("downloading (545 MB)..."); urllib.request.urlretrieve(URL, P)
csv.field_size_limit(sys.maxsize)
RX = {"snf": r"skilled nursing facilit|nursing home|sub-?acute (?:care|rehab|facilit)|skilled nursing",
      "rehab": r"inpatient rehabilitation|acute rehabilitation|rehabilitation (?:facility|hospital|center|centre|unit)",
      "home_health": r"home health|visiting nurse|home nursing|homebound|home care"}
n = 0; words = []; hits = collections.defaultdict(list)
with open(P, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        t = r.get("patient") or ""; n += 1; w = len(t.split()); words.append(w)
        for k, rx in RX.items():
            m = re.search(rx, t, re.I)
            if m: hits[k].append((r.get("patient_uid") or r.get("patient_id"), w, t[max(0, m.start()-150):m.end()+150].replace("\n", " ")))
print(f"rows={n}  words/patient: median={statistics.median(words)}  p90={sorted(words)[int(.9*n)]}")
for k, v in hits.items():
    ws = [x[1] for x in v]; print(f"{k}: {len(v)} patients mention it; median length {statistics.median(ws)} words; >=300 words: {sum(w>=300 for w in ws)}")
    for x in v[:2]: print("   ...", x[2])
json.dump({k: [x[0] for x in v] for k, v in hits.items()}, open(P.parent / "hits.json", "w"))
print("saved ids to", P.parent / "hits.json")
