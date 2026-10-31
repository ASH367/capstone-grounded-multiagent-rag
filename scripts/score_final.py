#!/usr/bin/env python3
"""Score the FINAL runs (units + cases) with the human-in-the-loop layer.   python3 scripts/score_final.py --arm A_strict --set final_held --runs results/fair/A_strict_final_held/run1 [--probe results/fair/probe_A_strict_final_held]
Main score = FINAL_SET status MAIN and evidence_ok.  Unsplit PARTLY cases (status SEPARATE) are listed on their own, never pooled.
For each system (multi / single) and each rule (forced = no review; primary = mechanical HITL rule; selfflag = primary + 'final reason says UNKNOWN'):
  accuracy (forced), coverage (share decided without a human), accuracy when committing, review precision (flagged cases whose forced answer was wrong), error capture (forced errors that were flagged).
A flagged case is never counted as correct or wrong; it is a separate bucket.  Confidence intervals resample whole DECISIONS (clusters), because units of one decision are not independent."""
import argparse, collections, json, random

def boot(vals_by_cluster, fn, B=4000, seed=0):
    rnd = random.Random(seed); cl = list(vals_by_cluster); g = []
    for _ in range(B):
        s = [x for c in (cl[rnd.randrange(len(cl))] for _ in cl) for x in vals_by_cluster[c]]
        v = fn(s)
        if v is not None: g.append(v)
    g.sort(); return (g[int(0.025 * len(g))], g[int(0.975 * len(g))]) if g else (None, None)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--arm", required=True); ap.add_argument("--set", required=True); ap.add_argument("--runs", nargs="+", required=True); ap.add_argument("--probe"); a = ap.parse_args()
    FS = {m["id"]: m for m in json.load(open("results/FINAL_SET.json"))}
    out = {}
    for run in a.runs:
        H = json.load(open(f"{run}/hitl.json"))["cases"]; pr = {}
        if a.probe: pr = {x["case_id"]: x.get("decision") for x in json.load(open(f"{a.probe}/resp_base.json"))}
        main = [i for i in H if FS.get(i, {}).get("status") == "MAIN" and FS[i].get("evidence_ok")]
        sep = [i for i in H if FS.get(i, {}).get("status") == "SEPARATE"]
        lab = {i: FS[i]["label"] for i in main}; par = {i: FS[i]["parent"] for i in main}
        cnt = collections.Counter(lab.values()); print(f"==== {run}   MAIN n={len(main)} from {len(set(par.values()))} decisions   labels {dict(cnt)}   majority baseline {max(cnt.values())/len(main):.0%}")
        res = {"n": len(main)}
        def acc_by_cluster(sysn, ids): 
            d = collections.defaultdict(list)
            for i in ids: d[par[i]].append(int(H[i][sysn]["answer"] == lab[i]))
            return d
        for sysn in ("multi", "single"):
            ok = {i: H[i][sysn]["answer"] == lab[i] for i in main}
            wrong_partly = sum(H[i][sysn]["answer"] == "PARTLY_COVERED" for i in main)
            lo, hi = boot(acc_by_cluster(sysn, main), lambda s: sum(s) / len(s) if s else None)
            print(f"  {sysn.upper():6s} forced answer: {sum(ok.values())}/{len(main)} = {sum(ok.values())/len(main):.0%}  (95% cluster CI {lo:.0%}-{hi:.0%}); predicted PARTLY on {wrong_partly} single-label units")
            res[sysn] = {"forced_correct": sum(ok.values()), "forced_ci": [lo, hi], "partly_predictions": wrong_partly}
            for rule, key in (("primary rule", "flag"), ("self-flag variant", "flag_self")):
                fl = [i for i in main if H[i][sysn][key]]; dec = [i for i in main if not H[i][sysn][key]]
                dc = sum(ok[i] for i in dec); fw = sum(not ok[i] for i in fl); errs = [i for i in main if not ok[i]]
                cap = sum(not ok[i] for i in fl)
                print(f"     {rule:18s} coverage {len(dec)}/{len(main)} = {len(dec)/len(main):.0%} | accuracy when committing {dc}/{len(dec)}" + (f" = {dc/len(dec):.0%}" if dec else "") +
                      f" | sent to human {len(fl)} (forced answer wrong on {fw}" + (f" = review precision {fw/len(fl):.0%}" if fl else "") + f") | forced errors captured {cap}/{len(errs)} | confident-wrong {len(dec)-dc}")
                res[sysn][key] = dict(coverage=len(dec), committed_correct=dc, flagged=len(fl), flagged_wrong=fw, errors=len(errs), confident_wrong=len(dec) - dc)
        if pr:
            okp = {i: pr.get(i) == lab[i] for i in main}; print(f"  BLIND PROBE (facts only, no policy): {sum(okp.values())}/{len(main)} = {sum(okp.values())/len(main):.0%}"); res["probe_correct"] = sum(okp.values())
        gm = {i: int(H[i]["multi"]["answer"] == lab[i]) - int(H[i]["single"]["answer"] == lab[i]) for i in main}
        d = collections.defaultdict(list)
        for i in main: d[par[i]].append(gm[i])
        lo, hi = boot(d, lambda s: sum(s) / len(s) if s else None)
        print(f"  multi - single forced accuracy gap: {100*sum(gm.values())/len(main):+.0f} pts (95% cluster CI {100*lo:+.0f} to {100*hi:+.0f})")
        res["gap_multi_minus_single"] = sum(gm.values()) / len(main); res["gap_ci"] = [lo, hi]
        print("  by label:", {l: {s: f"{sum(H[i][s]['answer']==lab[i] for i in main if lab[i]==l)}/{sum(1 for i in main if lab[i]==l)}" for s in ('multi', 'single')} for l in sorted(cnt)})
        if sep: print("  SEPARATE list (unsplit PARTLY, not in main score):", [(i, FS[i]["label"], "multi=" + str(H[i]["multi"]["answer"]), "single=" + str(H[i]["single"]["answer"])) for i in sep])
        out[run] = res
    json.dump(out, open(f"results/fair/final_score_{a.arm}_{a.set}.json", "w"), indent=1)
