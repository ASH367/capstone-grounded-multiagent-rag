"""Sentence-level leak cleaning.
Previous cleaning (data/cases_v2_clean, data/cases_v3_heldout_clean) dropped WHOLE facts that the AI leak audit labeled MIXED or ADJUDICATOR_FINDING.
This version keeps every verbatim sentence of a MIXED fact except the sentence(s) that contain the audit's own `leak_text`.
 - PATIENT_CLAIM / PARTY_ARGUMENT facts: kept unchanged (as before).
 - ADJUDICATOR_FINDING facts: dropped entirely (as before).
 - MIXED facts: only the flagged sentence(s) removed; remainder kept if it still has >= MINW words; if the leak text cannot be located, the whole fact is dropped (conservative).
No rewriting: every kept sentence is an exact substring of the original fact.
Usage: python3 scripts/surgical_clean.py
Outputs: data/cases_v2_surgical, data/cases_v3_heldout_surgical, results/review/surgical_clean_report.json
"""
import glob, json, os, re

MINW = 8
STOP = set("the a an of to in on and or for was were is are that this with by as at from be been has have had it its not no".split())
ABBR = ["Exh.", "Ex.", "Dec.", "No.", "Dr.", "U.S.", "C.F.R.", "St.", "v.", "Inc.", "Co.", "Mr.", "Ms.", "et al.", "e.g.", "i.e.", "Tr.", "Pub."]
TAIL = re.compile(r"^(Id\.|Exh?\.|See\b|Tr\.|Dec\.)")


def is_cite(p): return bool(TAIL.match(p.strip())) and len(p.strip()) < 70


def norm(s): return re.sub(r"\s+", " ", s).strip()


def split_sents(t):
    t = norm(t)
    for i, a in enumerate(ABBR): t = t.replace(a, a.replace(".", f"․{i}․"))
    parts = re.split(r"(?<=[.?!])\s+(?=[A-Z“\"(])", t)
    out = []
    for p in parts:
        for i, a in enumerate(ABBR): p = p.replace(a.replace(".", f"․{i}․"), a)
        if out and is_cite(p): out[-1] += " " + p        # citation tails belong to the previous sentence
        else: out.append(p)
    return out


def toks(s): return {w for w in re.findall(r"[a-z0-9]{3,}", s.lower()) if w not in STOP}


def flag_idx(S, leak):
    """indices of the sentences in S that contain the audit's leak text: for each leak piece, ONLY the single best-matching sentence (recall >= 0.6)."""
    pieces = []
    for part in re.split(r"\s*(?:\.\.\.|\u2026)\s*", leak or ""):
        pieces += [x for x in split_sents(part) if len(x.strip()) > 8]
    out = set()
    for piece in pieces:
        lt = toks(piece)
        if not lt: continue
        best = max(range(len(S)), key=lambda i: (len(lt & toks(S[i])) / len(lt)) * (len(lt & toks(S[i])) / max(1, len(toks(S[i]))) + 0.5))
        if len(lt & toks(S[best])) / len(lt) >= 0.6: out.add(best)
    return out


def run(orig_dir, out_dir, audit_file, keep_ids=None):
    audit = {(r["case_id"], r["fact_index"]): r for r in json.load(open(audit_file))}
    os.makedirs(out_dir, exist_ok=True); report = []
    stats = dict(cases=0, facts_before=0, facts_after=0, chars_after=0, whole_dropped=0, surgical=0, unlocated=0)
    for f in sorted(glob.glob(f"{orig_dir}/*.json")):
        c = json.load(open(f)); cid = c["case_id"]
        if keep_ids is not None and cid not in keep_ids: continue
        new = []
        for i, fact in enumerate(c["facts"], 1):
            a = audit[(cid, i)]; lab = a["label"]
            if lab in ("PATIENT_CLAIM", "PARTY_ARGUMENT"): new.append(norm(fact)); continue
            if lab == "ADJUDICATOR_FINDING":
                report.append(dict(case=cid, fact=i, action="dropped_whole(adjudicator_finding)", removed=norm(fact)[:300])); stats["whole_dropped"] += 1; continue
            S = split_sents(fact); bad = flag_idx(S, a["leak_text"]); keep = [x for i, x in enumerate(S) if i not in bad]; gone = [x for i, x in enumerate(S) if i in bad]
            if not gone:
                report.append(dict(case=cid, fact=i, action="dropped_whole(leak_text_not_located)", removed=norm(fact)[:300])); stats["unlocated"] += 1; continue
            rest = " ".join(keep); core = " ".join(x for x in keep if not is_cite(x))
            if len(core.split()) < MINW:
                report.append(dict(case=cid, fact=i, action="dropped_whole(remainder_too_short)", removed=norm(fact)[:300], kept_remainder=rest)); stats["whole_dropped"] += 1; continue
            new.append(rest); stats["surgical"] += 1
            report.append(dict(case=cid, fact=i, action="surgical", kept=rest[:400], removed=" | ".join(gone)[:400]))
        c2 = dict(c); c2["facts"] = new; c2["clean_method"] = "sentence-level via audit leak_text (scripts/surgical_clean.py)"
        json.dump(c2, open(f"{out_dir}/{os.path.basename(f)}", "w"), indent=1)
        stats["cases"] += 1; stats["facts_before"] += len(c["facts"]); stats["facts_after"] += len(new); stats["chars_after"] += sum(map(len, new))
    return stats, report


if __name__ == "__main__":
    held_ids = {json.load(open(f))["case_id"] for f in glob.glob("data/cases_v3_heldout_clean/*.json")}
    s1, r1 = run("data/cases_v2", "data/cases_v2_surgical", "results/review/leak_audit.json")
    s2, r2 = run("data/cases_v3_heldout", "data/cases_v3_heldout_surgical", "results/review/leak_audit_heldout.json", keep_ids=held_ids)
    json.dump({"dev22": dict(stats=s1, log=r1), "heldout18": dict(stats=s2, log=r2)}, open("results/review/surgical_clean_report.json", "w"), indent=1)
    for name, s in (("dev22", s1), ("heldout18", s2)):
        print(name, s)
    for d, tag in (("data/cases_v2_clean", "dev22 old clean"), ("data/cases_v2_surgical", "dev22 surgical"), ("data/cases_v3_heldout_clean", "held18 old clean"), ("data/cases_v3_heldout_surgical", "held18 surgical")):
        fs = [json.load(open(p)) for p in glob.glob(d + "/*.json")]
        print(f"{tag}: {len(fs)} cases, {sum(len(c['facts']) for c in fs)} facts, {sum(len(x) for c in fs for x in c['facts'])} chars")
