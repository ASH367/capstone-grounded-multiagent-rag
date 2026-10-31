"""Probe CourtListener (free) for federal opinions reviewing Medicare coverage denials. Run on YOUR Mac (the cloud workspace cannot reach it).
Reports hit counts per query and saves the first 20 hits' metadata/snippets. Optional token (free account): export COURTLISTENER_TOKEN=...
  python3 scripts/courtlistener_probe.py"""
import json, os, urllib.parse, urllib.request, urllib.error, pathlib
Q = {
 "snf":  '"skilled nursing facility" AND Medicare AND "Appeals Council" AND ("reasonable and necessary" OR "three-day" OR "skilled nursing")',
 "hh":   '"home health" AND Medicare AND "Appeals Council" AND (homebound OR "confined to the home" OR "plan of care")',
 "irf":  '"inpatient rehabilitation" AND Medicare AND "Appeals Council" AND "reasonable and necessary"',
 "any":  'Medicare AND "Secretary" AND "substantial evidence" AND ("skilled nursing" OR "home health" OR "inpatient rehabilitation") AND "Medicare Appeals Council"',
}
H = {"User-Agent": "capstone-research-probe"}
if os.environ.get("COURTLISTENER_TOKEN"): H["Authorization"] = "Token " + os.environ["COURTLISTENER_TOKEN"]
out = {}
for k, q in Q.items():
    url = "https://www.courtlistener.com/api/rest/v4/search/?" + urllib.parse.urlencode({"q": q, "type": "o", "order_by": "score desc", "stat_Precedential": "on", "stat_Non-Precedential": "on"})
    try: j = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=60))
    except urllib.error.HTTPError as e: print(k, "HTTP", e.code, e.read()[:200]); continue
    except Exception as e: print(k, "ERROR", e); continue
    rs = j.get("results", []); print(f"{k}: count={j.get('count')}  first hits:")
    for r in rs[:8]: print("  ", r.get("caseName"), "|", r.get("court"), "|", r.get("dateFiled"))
    out[k] = {"count": j.get("count"), "results": [{x: r.get(x) for x in ("caseName", "court", "dateFiled", "absolute_url", "cluster_id", "snippet")} for r in rs[:20]]}
pathlib.Path("data/raw").mkdir(parents=True, exist_ok=True); json.dump(out, open("data/raw/courtlistener_probe.json", "w"), indent=1); print("saved data/raw/courtlistener_probe.json")
