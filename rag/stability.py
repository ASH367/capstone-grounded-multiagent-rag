"""Compare two independent runs of the same prompts, and accuracy on flagged ("hard") vs unflagged cases."""
import json, collections
r1 = {r["case"]: r for r in json.load(open("results/milestone1_decisions.json"))["rows"]}
r2 = {r["case"]: r for r in json.load(open("results/llm_runs_run2/decisions.json"))["rows"]}
Q = json.load(open("results/review/queue.json")); hard = {q["case"] for q in Q if q["cp"] == "CP4"}   # flagged in run 1 (agents UNKNOWN/disagree or systems disagree)
ids = sorted(r1)
def acc(rows, key, subset): s = [c for c in ids if c in subset]; return (sum(rows[c][key] == rows[c]["reference"] for c in s), len(s))
out = {"n": len(ids)}
for sysn, key, ok in (("multi", "multi", "multi_ok"), ("single", "single", "single_ok")):
    same = sum(r1[c][key] == r2[c][key] for c in ids)
    out[sysn] = dict(run1_correct=sum(r1[c][ok] for c in ids), run2_correct=sum(r2[c][ok] for c in ids), same_decision_both_runs=same, same_rate=round(same / len(ids), 3),
                     changed=[(c, r1[c][key], r2[c][key]) for c in ids if r1[c][key] != r2[c][key]])
easy = set(ids) - hard
for sysn, ok in (("multi", "multi_ok"), ("single", "single_ok")):
    out[sysn]["hard_cases"] = dict(n=len(hard), run1=sum(r1[c][ok] for c in hard), run2=sum(r2[c][ok] for c in hard))
    out[sysn]["easy_cases"] = dict(n=len(easy), run1=sum(r1[c][ok] for c in easy), run2=sum(r2[c][ok] for c in easy))
av = sum(r1[c]["agent_verdicts"][i] == r2[c]["agent_verdicts"][i] for c in ids for i in range(3)); out["agent_verdict_agreement"] = round(av / (3 * len(ids)), 3)
out["citation_check_run2"] = json.load(open("results/llm_runs_run2/decisions.json"))["summary"]["all"]
json.dump(out, open("results/stability_m2.json", "w"), indent=1); print(json.dumps({k: v for k, v in out.items() if k != "citation_check_run2"}, indent=1)); print("run2 citation check:", out["citation_check_run2"]["citation_check_multi"], out["citation_check_run2"]["citation_check_single"])
