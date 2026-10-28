"""Human-in-the-loop review layer.
  python3 -m rag.review build            -> results/review/queue.json + results/review/reviewer.html (open in a browser)
  python3 -m rag.review apply labels.json [labels2.json]  -> human-verified metrics (+ Cohen's kappa if two reviewers)
Checkpoints:  CP4 decisions needing a person (flagged), CP3 finding support, CP2 retrieval adequacy, CP1 data fidelity.
Reviewer should work in this order (CP4, CP3, CP2, then CP1) because CP1 shows the Council outcome."""
import json, glob, random, sys, html, pathlib, collections, re
RUN = pathlib.Path("results/llm_runs"); OUT = pathlib.Path("results/review"); OUT.mkdir(parents=True, exist_ok=True)
chunks = {c["chunk_id"]: c for c in json.load(open("data/index_v2/chunks.json"))["chunks"]}
cases = {c["case_id"]: c for c in (json.load(open(f)) for f in sorted(glob.glob("data/cases_v2/*.json")))}
def L(r): return {x["case_id"]: x for x in json.load(open(RUN / f"resp_{r}.json"))}
def facts(c): return "\n".join(f"[{i+1}] {x}" for i, x in enumerate(c["facts"]))
def trunc(s, n=110): w = s.split(); return " ".join(w[:n]) + (" ..." if len(w) > n else "")

def flagged(cid, R):
    v = [R["elig"][cid]["verdict"], R["nec"][cid]["verdict"], R["doc"][cid]["verdict"]]
    why = []
    if "UNKNOWN" in v: why.append("an agent said UNKNOWN")
    if len(set(v) - {"UNKNOWN"}) > 1: why.append("agents disagree")
    if R["orch"][cid]["decision"] != R["base"][cid]["decision"]: why.append("multi-agent and single-agent disagree")
    return why

def build():
    R = {r: L(r) for r in ("elig", "nec", "doc", "base", "orch")}; rng = random.Random(7); Q = []
    for cid in sorted(cases):                                    # CP4
        why = flagged(cid, R)
        if why:
            ag = "\n".join(f"- {nm}: {R[k][cid]['verdict']}; " + " | ".join(f['claim'] for f in R[k][cid]['findings'][:2]) for nm, k in (("Eligibility", "elig"), ("Medical necessity", "nec"), ("Documentation", "doc")))
            Q.append(dict(id=f"CP4|{cid}", cp="CP4", case=cid, title=f"Decide this case (flagged: {', '.join(why)})", body=f"CASE FACTS\n{facts(cases[cid])}\n\nAGENT SUMMARIES\n{ag}",
                          questions=[dict(id="decision", label="Your decision", options=["COVERED", "NOT_COVERED", "PARTLY_COVERED", "CANNOT_TELL"])]))
    pool = []                                                     # CP3: sampled findings, system hidden in the UI
    for sysname, keys in (("multi", ("elig", "nec", "doc")), ("single", ("base",))):
        its = [(sysname, k, cid, i) for k in keys for cid in cases for i, _ in enumerate(R[k][cid]["findings"])]
        rng.shuffle(its); pool += its[:30]
    rng.shuffle(pool)
    for sysname, k, cid, i in pool:
        f = R[k][cid]["findings"][i]; ch = chunks[f["passage_id"]]
        Q.append(dict(id=f"CP3|{cid}|{k}|{i}", cp="CP3", case=cid, system=sysname, title=f"Finding ({cid})",
                      body=f"CLAIM: {f['claim']}\n\nCASE FACT QUOTED: \"{f['case_fact']}\"\n\nPOLICY QUOTED ({ch['label']}): \"{f['quote']}\"",
                      questions=[dict(id="support", label="Is the claim supported by that case fact and that policy quote?", options=["SUPPORTED", "PARTLY", "NOT_SUPPORTED"])]))
    ret = json.load(open(RUN / "retrieved.json"))
    for cid in sorted(cases):                                     # CP2
        ps = "\n\n".join(f"({chunks[i]['label']}) {trunc(chunks[i]['text'])}" for i in ret[cid]["nec"])
        Q.append(dict(id=f"CP2|{cid}", cp="CP2", case=cid, title=f"Retrieval check ({cid})", body=f"CASE FACTS\n{facts(cases[cid])}\n\nRETRIEVED PASSAGES (top 5)\n{ps}",
                      questions=[dict(id="adequate", label="Do these passages contain the rule needed to decide this case?", options=["YES", "PARTLY", "NO"])]))
    for cid in sorted(cases):                                     # CP1 (shows the outcome: do last)
        c = cases[cid]
        Q.append(dict(id=f"CP1|{cid}", cp="CP1", case=cid, title=f"Data fidelity ({cid})",
                      body=f"Open data/raw/decisions/{cid}.pdf and compare.\n\nFACT EXCERPTS\n{facts(c)}\n\nOUTCOME LABEL: {c['reference_outcome']}\nCITED MBPM SECTIONS: " + (", ".join(f"{g['doc']} s{g['section']}" for g in c['cited_sections']) or "none"),
                      questions=[dict(id="facts", label="Excerpts are accurate and describe only the patient/claim?", options=["YES", "NO"]), dict(id="outcome", label="Outcome label matches the decision?", options=["YES", "NO"]), dict(id="sections", label="Cited sections match the decision?", options=["YES", "NO"])]))
    json.dump(Q, open(OUT / "queue.json", "w"), indent=1)
    page = TEMPLATE.replace("__DATA__", json.dumps([{k: v for k, v in q.items() if k != "system"} for q in Q]).replace("</", "<\\/"))
    open(OUT / "reviewer.html", "w").write(page)
    print(collections.Counter(q["cp"] for q in Q), "-> results/review/reviewer.html")

def kappa(a, b):
    ks = sorted(set(a) | set(b)); n = len(a)
    if not n: return None
    po = sum(x == y for x, y in zip(a, b)) / n; pe = sum((a.count(k) / n) * (b.count(k) / n) for k in ks)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0

def apply(paths):
    Q = {q["id"]: q for q in json.load(open(OUT / "queue.json"))}; labs = [json.load(open(p))["items"] for p in paths]; A = labs[0]; S = {"reviewer": json.load(open(paths[0])).get("reviewer", "unknown")}
    def ans(it, k): return A.get(it, {}).get("answers", {}).get(k)
    for sysname in ("multi", "single"):
        v = [ans(i, "support") for i, q in Q.items() if q["cp"] == "CP3" and q.get("system") == sysname and ans(i, "support")]
        c = collections.Counter(v); n = len(v)
        S[f"CP3_{sysname}"] = dict(n=n, supported=c["SUPPORTED"], partly=c["PARTLY"], not_supported=c["NOT_SUPPORTED"], groundedness=round(c["SUPPORTED"] / n, 3) if n else None, hallucination=round(c["NOT_SUPPORTED"] / n, 3) if n else None)
    v = [ans(i, "adequate") for i, q in Q.items() if q["cp"] == "CP2" and ans(i, "adequate")]; c = collections.Counter(v)
    S["CP2_retrieval_adequate"] = dict(n=len(v), yes=c["YES"], partly=c["PARTLY"], no=c["NO"])
    ok = [all(ans(i, k) == "YES" for k in ("facts", "sections")) for i, q in Q.items() if q["cp"] == "CP1" and ans(i, "facts")]
    S["CP1_data_fidelity"] = dict(n=len(ok), fully_correct=sum(ok), checked="excerpt fidelity and cited sections only; outcome label not re-checked")
    res = json.load(open("results/milestone1_decisions.json"))["rows"]; flagged_ids = {q["case"] for q in Q.values() if q["cp"] == "CP4"}; ref = {r["case"]: r["reference"] for r in res}
    hum = {Q[i]["case"]: ans(i, "decision") for i in Q if Q[i]["cp"] == "CP4" and ans(i, "decision")}
    gated = {r["case"]: (hum[r["case"]] if r["case"] in hum and hum[r["case"]] != "CANNOT_TELL" else r["multi"]) for r in res}
    S["CP4_gating"] = dict(flagged=len(flagged_ids), reviewed=len(hum), multi_accuracy=round(sum(r["multi"] == ref[r["case"]] for r in res) / len(res), 3), human_gated_accuracy=round(sum(gated[c] == ref[c] for c in ref) / len(ref), 3),
                           flagged_cases_system_correct=sum(next(r for r in res if r["case"] == c)["multi"] == ref[c] for c in flagged_ids), flagged_cases_human_correct=sum(hum.get(c) == ref[c] for c in flagged_ids))
    if len(labs) > 1:
        B = labs[1]
        for cp, key in (("CP3", "support"), ("CP2", "adequate"), ("CP4", "decision")):
            ids = [i for i, q in Q.items() if q["cp"] == cp and A.get(i, {}).get("answers", {}).get(key) and B.get(i, {}).get("answers", {}).get(key)]
            S[f"kappa_{cp}"] = dict(n=len(ids), kappa=kappa([A[i]["answers"][key] for i in ids], [B[i]["answers"][key] for i in ids]))
    json.dump(S, open(OUT / "review_summary.json", "w"), indent=1); print(json.dumps(S, indent=1))

TEMPLATE = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Capstone review tool</title>
<style>body{font-family:system-ui,Arial;max-width:900px;margin:0 auto;padding:16px 16px 80px;background:#f7f5f0;color:#14213d}h1{font-size:22px}.bar{position:sticky;top:0;background:#14213d;color:#fff;padding:10px 14px;border-radius:0 0 12px 12px;display:flex;gap:12px;flex-wrap:wrap;align-items:center;z-index:5}
.tabs button{background:#fff;border:1px solid #ddd9ce;border-radius:8px;padding:6px 10px;cursor:pointer}.tabs button.on{background:#b8452e;color:#fff;border-color:#b8452e}.card{background:#fff;border:1px solid #ddd9ce;border-radius:12px;padding:16px;margin:14px 0}.card.done{border-left:6px solid #1f6f78}
pre{white-space:pre-wrap;font-family:inherit;line-height:1.45;background:#faf9f6;padding:10px;border-radius:8px}label{display:inline-block;margin:4px 14px 4px 0}textarea{width:100%;min-height:36px;margin-top:6px}.q{margin-top:10px;font-weight:600}.note{color:#4a5268;font-size:14px}button.exp{background:#1f6f78;color:#fff;border:0;border-radius:8px;padding:8px 14px;cursor:pointer}</style></head><body>
<div class="bar"><b>Review</b><span id="prog"></span><span class="tabs" id="tabs"></span><input id="who" placeholder="your name" style="padding:6px;border-radius:6px;border:0"><button class="exp" onclick="exp()">Export labels (JSON)</button></div>
<h1>Capstone review tool</h1><p class="note">Work in this order: CP4, CP3, CP2, then CP1 (CP1 shows the real outcome, so do it last). Progress saves in this browser. Export when done and save the file as results/review/human_labels.json.</p><div id="list"></div>
<script>const Q=__DATA__;const ORDER=["CP4","CP3","CP2","CP1"];const NAMES={CP4:"CP4 Decisions",CP3:"CP3 Findings",CP2:"CP2 Retrieval",CP1:"CP1 Data"};let cur="CP4";
const KEY="capstone-review-v1";let S={};try{S=JSON.parse(localStorage.getItem(KEY)||"{}")}catch(e){S={}}
function save(){try{localStorage.setItem(KEY,JSON.stringify(S))}catch(e){}}
function done(q){const a=(S[q.id]||{}).answers||{};return q.questions.every(x=>a[x.id])}
function setA(id,k,v){S[id]=S[id]||{answers:{},note:""};S[id].answers[k]=v;save();render(false)}
function setN(id,v){S[id]=S[id]||{answers:{},note:""};S[id].note=v;save()}
function render(scroll){const items=Q.filter(q=>q.cp===cur);document.getElementById("tabs").innerHTML=ORDER.map(c=>{const t=Q.filter(q=>q.cp===c),d=t.filter(done).length;return `<button class="${c===cur?"on":""}" onclick="cur='${c}';render(true)">${NAMES[c]} ${d}/${t.length}</button>`}).join(" ");
document.getElementById("prog").textContent=Q.filter(done).length+"/"+Q.length+" done";
document.getElementById("list").innerHTML=items.map(q=>`<div class="card ${done(q)?"done":""}"><b>${q.title}</b><pre>${q.body.replace(/&/g,"&amp;").replace(/</g,"&lt;")}</pre>`+q.questions.map(x=>`<div class="q">${x.label}</div>`+x.options.map(o=>`<label><input type="radio" name="${q.id}|${x.id}" ${((S[q.id]||{}).answers||{})[x.id]===o?"checked":""} onchange='setA(${JSON.stringify(q.id)},${JSON.stringify(x.id)},${JSON.stringify(o)})'> ${o}</label>`).join("")).join("")+`<textarea placeholder="optional note" onchange='setN(${JSON.stringify(q.id)},this.value)'>${((S[q.id]||{}).note||"").replace(/</g,"&lt;")}</textarea></div>`).join("");if(scroll)window.scrollTo(0,0)}
function exp(){const out={reviewer:document.getElementById("who").value||"unknown",exported:new Date().toISOString(),items:S};const b=new Blob([JSON.stringify(out,null,1)],{type:"application/json"});const a=document.createElement("a");a.href=URL.createObjectURL(b);a.download="human_labels.json";a.click()}
render(true)</script></body></html>"""
if __name__ == "__main__": build() if sys.argv[1] == "build" else apply(sys.argv[2:])
