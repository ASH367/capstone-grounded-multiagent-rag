#!/usr/bin/env python3
"""Score single-agent vs multi-agent runs on the Council cases under the ORIGINAL key and the COVERAGE-ONLY key.

  # new fair-test arms (cases carry coverage_label / include_primary; evidence floor is per arm, outcome-blind: word count of the facts)
  python3 scripts/score_fair.py --arm D_wide --set held --runs results/fair/D_wide_held/run1 [more run folders = replicates]
  # re-score older runs (any case folder) on the coverage-only key
  python3 scripts/score_fair.py --set held --runs results/heldout_r1 results/heldout_r2 results/heldout_r3
Key definitions
  original key : reference_outcome as first labelled (mixes coverage with liability/procedure)
  coverage key : data/council_issue_tags.json -> coverage_label on cases whose operative holding turns on a coverage criterion (include_primary = 1)
Reports accuracy, majority/always-COVERED baselines, balanced accuracy, exact McNemar (multi vs single) and a bootstrap CI for the accuracy gap.
"""
import argparse, collections, glob, json, math, os, random

TAGS = json.load(open("data/council_issue_tags.json"))["cases"]
M = {"favorable": "COVERED", "unfavorable": "NOT_COVERED", "partial": "PARTLY_COVERED"}
SRC = {"dev": "data/cases_v2", "held": "data/cases_v3_heldout"}
EVMIN = {"A_strict": 60, "B_gaps": 60, "C_prior": 100, "D_wide": 150, "E_aljfacts": 150}      # sensitivity only: word floor per arm (the pre-registered floor is the builder's evidence_ok flag)


def orig_label(cid):
    st = TAGS[cid]["set"]; p = f"{SRC[st]}/{cid}.json"
    return M.get(json.load(open(p)).get("reference_outcome")) if os.path.exists(p) else None


def mcnemar(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def bal_acc(truth, pred):
    labs = sorted(set(truth)); rec = []
    for l in labs:
        idx = [i for i, t in enumerate(truth) if t == l]; rec.append(sum(pred[i] == l for i in idx) / len(idx))
    return sum(rec) / len(rec)


def boot_gap(okm, oks, B=4000, seed=0):
    rnd = random.Random(seed); n = len(okm); g = []
    for _ in range(B):
        ix = [rnd.randrange(n) for _ in range(n)]; g.append((sum(okm[i] for i in ix) - sum(oks[i] for i in ix)) / n)
    g.sort(); return g[int(0.025 * B)], g[int(0.975 * B)]


def load_run(d):
    out = {}
    for name, fn in (("multi", "resp_orch.json"), ("single", "resp_base.json")):
        out[name] = {x["case_id"]: x.get("decision") for x in json.load(open(f"{d}/{fn}"))}
    return out


def report(title, ids, key, pred, verbose=False):
    ids = [i for i in ids if key.get(i)]
    if not ids: print(f"  {title}: no cases"); return None
    truth = [key[i] for i in ids]; maj = collections.Counter(truth).most_common(1)[0]
    pm = [pred["multi"].get(i) for i in ids]; ps = [pred["single"].get(i) for i in ids]
    okm = [int(a == t) for a, t in zip(pm, truth)]; oks = [int(a == t) for a, t in zip(ps, truth)]
    b = sum(1 for x, y in zip(okm, oks) if x and not y); c = sum(1 for x, y in zip(okm, oks) if y and not x)
    lo, hi = boot_gap(okm, oks)
    print(f"  {title}: n={len(ids)}  labels {dict(collections.Counter(truth))}")
    print(f"     multi  {sum(okm)}/{len(ids)} = {sum(okm)/len(ids):.0%}   balanced {bal_acc(truth, pm):.2f}   preds {dict(collections.Counter(pm))}")
    print(f"     single {sum(oks)}/{len(ids)} = {sum(oks)/len(ids):.0%}   balanced {bal_acc(truth, ps):.2f}   preds {dict(collections.Counter(ps))}")
    print(f"     majority-class baseline {maj[1]/len(ids):.0%} ({maj[0]});  always-COVERED {truth.count('COVERED')/len(ids):.0%};  multi-only-right {b}, single-only-right {c}, McNemar exact p={mcnemar(b, c):.2f};  gap (multi-single) {100*(sum(okm)-sum(oks))/len(ids):+.0f} pts, 95% CI [{100*lo:+.0f}, {100*hi:+.0f}]")
    if verbose:
        for i, t, a, s in zip(ids, truth, pm, ps): print(f"       {i:30s} truth={t:14s} multi={str(a):14s} {'ok ' if a == t else 'ERR'}  single={str(s):14s} {'ok ' if s == t else 'ERR'}")
    return dict(n=len(ids), multi=sum(okm), single=sum(oks), majority=maj[1] / len(ids), mcnemar_p=mcnemar(b, c), gap_ci=[lo, hi])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--runs", nargs="+", required=True); ap.add_argument("--set", choices=["dev", "held", "all"], default="all"); ap.add_argument("--arm"); ap.add_argument("--verbose", action="store_true"); ap.add_argument("--pool", action="store_true", help="merge several run folders (e.g. held + dev) into one scored set")
    a = ap.parse_args(); res = {}
    words = {}; evok = {}
    if a.arm:
        for st in ("dev", "held"):
            for f in glob.glob(f"data/cases_v4/{a.arm}_{st}/*.json"):
                c = json.load(open(f)); words[c["case_id"]] = sum(len(x.split()) for x in c["facts"]); evok[c["case_id"]] = c["evidence_ok"]
    if a.pool:
        merged = {"multi": {}, "single": {}}
        for d in a.runs:
            for k, v in load_run(d).items(): merged[k].update(v)
        runs = [("POOLED " + " + ".join(a.runs), merged)]
    else: runs = [(d, load_run(d)) for d in a.runs]
    for d, pred in runs:
        print(f"==== {d}")
        ids = [i for i in pred["multi"] if i in TAGS and (a.set == "all" or TAGS[i]["set"] == a.set)]
        orig = {i: orig_label(i) for i in ids}; cov = {i: TAGS[i]["coverage_label"] for i in ids}
        fair = [i for i in ids if TAGS[i]["include_primary"]]
        r = {"original_key_all": report("ORIGINAL key, all cases", ids, orig, pred, a.verbose),
             "coverage_key_merits": report("COVERAGE key, merits cases only", fair, cov, pred, a.verbose)}
        if words:
            ev = [i for i in fair if evok.get(i)]
            r["PRIMARY_coverage_key_merits_evidence_ok"] = report("PRIMARY: COVERAGE key, merits cases with enough non-reasoning evidence (builder flag: strict arm >= 60 words and wide arm >= 150)", ev, cov, pred, a.verbose)
            print("  dropped for thin evidence:", [(i, words.get(i, 0)) for i in fair if i not in ev])
            ev2 = [i for i in fair if words.get(i, 0) >= EVMIN[a.arm]]
            r["sens_coverage_key_merits_wordfloor"] = report(f"sensitivity: COVERAGE key, merits cases with >= {EVMIN[a.arm]} words in this arm", ev2, cov, pred, a.verbose)
        res[d] = r
    os.makedirs("results/fair", exist_ok=True)
    json.dump(res, open(f"results/fair/score_{a.arm or 'old'}_{a.set}.json", "w"), indent=1)
