#!/usr/bin/env python3
"""rag/fairtest.py - build fair-test case sets from raw Medicare Appeals Council decisions.

Idea: hand the system the decision's own PRE-VERDICT content (record facts, party submissions; optionally record-gap statements and
earlier-level denials) and nothing from the Council's verdict or reasoning. Every kept sentence is an exact substring of the decision.

  python3 -m rag.fairtest dump  --case prestige_homecare     # every sentence with its tag
  python3 -m rag.fairtest build --sets dev                   # arms -> data/cases_v4/<arm>_<set>/
  python3 -m rag.fairtest audit --sets dev                   # known-good recall, known-leak hits, verdict-word scan
  python3 -m rag.fairtest freeze                             # hash the rules BEFORE touching the held-out set
  python3 -m rag.fairtest build --sets held ; python3 -m rag.fairtest audit --sets held
Arms:  A_strict = FACT+PARTY | B_gaps = A + record-gap statements | C_prior = B + contractor/QIC (earlier-level) determinations.
Never included in any arm: Council voice/reasoning/disposition, law text, ALJ recital, procedure/liability, evaluation language, footnotes, captions.
"""
import argparse, collections, glob, hashlib, json, os, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/text"
TAGS = ROOT / "data/council_issue_tags.json"
OUT = ROOT / "data/cases_v4"
SRC = {"dev": ROOT / "data/cases_v2", "held": ROOT / "data/cases_v3_heldout"}
SURG = {"dev": ROOT / "data/cases_v2_surgical", "held": ROOT / "data/cases_v3_heldout_surgical"}
AUDIT = {"dev": ROOT / "results/review/leak_audit.json", "held": ROOT / "results/review/leak_audit_heldout.json"}
ARMS = {"A_strict": {"FACT", "PARTY"}, "B_gaps": {"FACT", "PARTY", "GAP"}, "C_prior": {"FACT", "PARTY", "GAP", "PRIOR_DENIAL", "PRIOR_DENIAL_CONT"}, "D_wide": {"FACT", "PARTY", "GAP", "PRIOR_DENIAL", "PRIOR_DENIAL_CONT", "COUNCIL_REC", "FACT_WEAK"}}
MAXW = 110     # max words per fact unit
EV_A, EV_D = 60, 150   # outcome-blind evidence-sufficiency rule: strict arm >= 60 words and wide arm >= 150 words, else the case cannot be tested fairly

# ------------------------------------------------------------------ 1. clean text -> paragraphs
PAGE_RE = re.compile(r"^\s{8,}[-\u2013\u2014]?\s*\d{1,3}\s*[-\u2013\u2014]?\s*$|^\s*Page\s+\d+(\s+of\s+\d+)?\s*$", re.I)
FN_RE = re.compile(r"^\d{1,2}\s*$")
TERM = re.compile(r"[.?!:;\"\u201d\u2019)]\s*$")


def pages(raw):
    pg, out = [], []
    for ln in raw.replace("\r", "").split("\n"):
        if PAGE_RE.match(ln): out.append(pg); pg = []
        else: pg.append(ln)
    out.append(pg)
    return out


def chunks(lines):
    cur, out = [], []
    for ln in lines + [""]:
        if ln.strip(): cur.append(ln)
        elif cur: out.append(cur); cur = []
    return out


def split_footnotes(lines):
    for i, ln in enumerate(lines):
        if FN_RE.match(ln):
            j = i + 1
            while j < len(lines) and not lines[j].strip(): j += 1
            if j < len(lines) and lines[j].startswith("  "): return lines[:i], lines[i:]
    return lines, []


def drop_caption(ch):
    for k, c in enumerate(ch):
        nw = sum(len(l.split()) for l in c)
        if nw >= 20 and not any(re.search(r"\S {8,}\S", l) for l in c): return ch[k:]
    return ch


def paragraphs(raw):
    paras, carry = [], None
    for pi, lines in enumerate(pages(raw)):
        body, fn = split_footnotes(lines)
        ch = chunks(body)
        if pi == 0: ch = drop_caption(ch)
        if fn and ch and ch[-1][0].strip()[:1].islower() and TERM.search(ch[-1][-1]): ch = ch[:-1]   # footnote continuation from previous page
        items = []
        for c in ch:
            items.append(dict(text=" ".join(l.strip() for l in c), indent=min(len(l) - len(l.lstrip()) for l in c), nlines=len(c), page=pi))
        if carry is None and paras and items and TAIL.match(items[0]["text"]):
            paras[-1]["text"] += " " + items[0]["text"]; items = items[1:]
        if carry is not None and items:
            if items[0]["text"][:1].islower() or items[0]["text"][:1].isdigit():
                items[0]["text"] = carry["text"] + " " + items[0]["text"]; items[0]["indent"] = carry["indent"]; items[0]["nlines"] += carry["nlines"]
            else: paras.append(carry)
            carry = None
        if items and not TERM.search(items[-1]["text"]): carry = items.pop()
        paras.extend(items)
    if carry: paras.append(carry)
    for p in paras: p["text"] = unmark(re.sub(r"\s+", " ", p["text"]).strip())
    return paras


def unmark(t):   # footnote digits glued to sentence punctuation:  "services.2 The ALJ"  or  "care. 4 In the days"
    t = re.sub(r"(?<=[a-z)\u201d\"'])([.?!])\s+\d{1,2}\s+(?=[A-Z])", r"\1 ", t)
    return re.sub(r"(?<=[a-z)\u201d\"'\d])([.?!])\d{1,2}(?=\s+[A-Z\u201c\"(])", r"\1", t)


# ------------------------------------------------------------------ 2. sentences
ABBR = ["Dr.", "Mr.", "Mrs.", "Ms.", "St.", "No.", "Nos.", "Inc.", "Co.", "Corp.", "Ltd.", "U.S.C.", "U.S.", "C.F.R.", "Exh.", "Exhs.", "Ex.", "Dec.", "Tr.", "Pub.", "Sec.",
        "Secs.", "Ch.", "e.g.", "i.e.", "E.g.", "v.", "vs.", "approx.", "a.m.", "p.m.", "M.D.", "R.N.", "L.P.N.", "P.T.", "O.T.", "Jan.", "Feb.", "Mar.", "Apr.", "Jun.", "Jul.", "Aug.", "Sept.", "Sep.",
        "Oct.", "Nov.", "Mt.", "Ft.", "Jr.", "Sr.", "Prof.", "Hon.", "Fed.", "Reg.", "Cir.", "Supp.", "para.", "Cf.", "al.", "etc."]
ABBR = sorted(ABBR, key=len, reverse=True)
SPLIT = re.compile(r"(?<=[.?!])[\"\u201d\u2019')\]]*\s+(?=[\"\u201c\u2018(\[]?[A-Z\u00a7])")
TAIL = re.compile(r"^(Id\.|Exhs?\.|Ex\.|See\b|Tr\.|Dec\.|Cf\.|Compare\b|Citing\b|E\.g\.|e\.g\.|([A-Z]\.){1,3}\d*\s*File\b)")


def split_sentences(t):
    for i, a in enumerate(ABBR): t = re.sub(r"(?<![A-Za-z])" + re.escape(a), a.replace(".", f"\u2024{i}\u2024"), t)
    t = re.sub(r"(?<![A-Za-z])([A-Z])\.(?=\s+[A-Z][a-z])", "\\1\u2024X\u2024", t)       # middle initials
    out, last = [], 0
    for m in SPLIT.finditer(t):
        out.append(t[last:m.start() + len(m.group(0).rstrip())]); last = m.end()
    out.append(t[last:])
    res = []
    for s in out:
        for i, a in enumerate(ABBR): s = s.replace(a.replace(".", f"\u2024{i}\u2024"), a)
        s = s.replace("\u2024X\u2024", ".")
        if res and TAIL.match(s) and len(s.split()) <= 45: res[-1] += " " + s
        else: res.append(s)
    return [s.strip() for s in res if s.strip()]


# ------------------------------------------------------------------ 3. rule tagger
R = lambda p, f=re.I: re.compile(p, f)
COUNCIL = R(r"\b(we|our|us)\b|\bcouncil\b|\bboard\b|\bthis decision\b|\bthe decision (is|are)\b")
DISP = R(r"\b(affirm\w*|revers\w*|vacat\w*|remand\w*|uphold\w*|upheld|overturn\w*|dismiss\w*|adopt\w*|hereby)\b|\bdirected (to|that)\b|\b(is|are) ordered\b|\bordered to\b")   # v1.1: order language (found on held-out 11-1343, Council order tagged as earlier-level denial)
PROC = R(r"\b(timely|jurisdiction\w*|scope of review|de novo|docket|notice of|exhibit mac|mac-\d|amount in controversy|"
         r"appointment of representative|representation|liab(le|ility)|waiver|without fault|should have known|financially responsible|subrogee|overpayment|recoup\w*|refund)\b")
PROC_SOFT = R(r"\b(request(ed|s)? (for )?(a )?(hearing|review|reconsideration|redetermination|extension|leave)|exceptions?)\b")
REASON = R(r"^(Therefore|Thus|Accordingly|Consequently|Hence|As a result|In sum|In summary|In other words|Given (the|this|these)|Based on (the|this|these))\b")
PRIOR_PASSIVE = R(r"\b(initial determination|(was|were) (denied|disallowed|found (not )?covered)|denied (on|because|for)|denial (of|was)|on the ground that|ground for denial)\b")
LAW_CS = R(r"\bthe Act\b|\bSocial Security Act\b|\bMBPM\b|\bMPIM\b|\bNCD\b|\bLCD\b|\bCMS Pub\b|\bCMS Ruling\b", 0)
LAW_CI = R(r"C\.F\.R|\bCFR\b|U\.S\.C|\u00a7|\bsections?\s+\d|\bpub\.?\s*100|benefit policy manual|claims processing manual|program integrity manual|medicare manual|\bregulations?\b|\bstatut\w*|\bchapter\s+\d")
ALJ = R(r"\b(ALJ|ALJs|administrative law judges?|hearing decision|hearing officer|the undersigned)\b")
ALJ_FULL = R(r"\bDec\.\s+at\s+\d|\bALJ Decision\b|\bALJ Dec\b")
LAWSTMT = R(r"\b(must|shall|in order (for|to)|to qualify|to be covered|is defined|are defined|defined as|provides? that|provided that|requires? that|requirements? (of|for)|criteria (for|to)|only if|unless|is required|are required|is considered|are considered|is responsible for|are responsible for|has developed|guidance|guidelines?|should be (based|determined|considered|evaluated|assessed|made|applied|construed)|may be considered|regardless of|without regard|MPBM|MBPM)\b|\bMedicare (covers|pays|does not|will not|provides|requires)\b")
PATREF = R(r"\b(beneficiar\w+|patient|she|he|her|his|resident|claimant|appellant|PCR|EMT|paramedic|crew)\b")
PRIOR_CS = R(r"\b(QIC|QICs|MAC|MACs|CMS|QIO|PRO|PSC|ZPIC|RAC|FI|HHI)\b", 0)
PRIOR_CI = R(r"\b(qualified independent contractors?|intermediar(y|ies)|fiscal intermediar(y|ies)|contractors?|medicare administrative contractors?|carriers?|reconsiderations?|redeterminations?|reviewers?|centers for medicare|"
             r"peer review organization|recovery audit|medicare advantage)\b")
PN = r"(appellant|claimant|petitioner|beneficiar\w+|provider|supplier|hospital|facility|agency|HHA|SNF|physician|doctor|representative|attorney|counsel|respondent|part(y|ies))"
PV = r"(argu\w+|contend\w*|assert\w*|maintain\w*|alleg\w*|claims? that|claimed that|claiming|submit\w*|explain\w*|object\w*|disagree\w*|dispute\w*|believe\w*|point\w* out|challeng\w*|stat\w+ that|wrote|testif\w*|assur\w*|insist\w*|urge\w*)"
PARTY = R(r"\b(according to|per) (the )?" + PN + r"|\b" + PN + r"(\W+\w+){0,8}\W+" + PV + r"\b")
GAP = R(r"\b(record|file|chart|notes|documentation|evidence|exhibits?)\b[^.]{0,80}\b(does not|do not|did not|doesn't|fails? to|failed to|lacks?|contains? no|is silent|are silent|not (contain|include|indicate|show|reflect|document|demonstrate|establish|support|reveal))\b"
        r"|\b(no|not any|nothing|without|absence of|lack of)\b[^.]{0,40}\b(evidence|documentation|record|support|indication|information|mention)\b|\bnot (documented|indicated|reflected|mentioned|noted|recorded|supported|established|shown)\b|\bneither\b[^.]{0,100}\bnor\b|\bno other (document|record|evidence)")
EVAL_STRONG = R(r"reasonable and necessary|medically necessary|\bnot necessary\b|\bunnecessary\b|\bnon-?covered\b|\bnot covered\b|\b(is|are|was|were) covered\b|\bcovered (by|under)\b|\bcoverage (is|was|requirement|criteria)\b|\bnot payable\b|\bpayable\b|"
                r"\b(not )?entitled\b|\b(not )?eligible for\b")
EVAL = R(r"\b(meet|meets|met|satisf(y|ies|ied)|fulfill(s|ed)?|qualif(y|ies|ied)) (the |all |each |these |those |any )?(coverage|requirements?|criteria|conditions?|standards?|definition|test)\b|"
         r"\b(fail(s|ed)? to|failure to|unable to|did not|does not|do not|has not|have not|had not|was not|were not|is not|are not|cannot) (meet|satisfy|establish|demonstrate|show|document|support|prove|qualify|comply)\b|"
         r"\b(insufficient|inadequate|unsupported|not supported)\b|\bdoes not mean\b|\bdoes not constitute\b|\bestablished by\b|\bample\b|\bsupport(s|ed)? (these|this|the|that)\b|\bdemonstrat\w+|\bweigh\w* in favor\b|\bin favor of\b|\bmedically appropriate\b|\bshould result in\b|^If\b|\bconstitut(e|es|ed)\b|\b(services?|care|visits?|treatment)\b[^.]{0,30}\b(was|were|is|are)\b[^.]{0,10}\b(un)?skilled\b")
MONTH = r"(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|june?|july?|aug(ust)?|sept?(ember)?|oct(ober)?|nov(ember)?|dec(ember)?)\.?"
STRICT = R(r"\b" + MONTH + r"\s+\d{1,2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b(19|20)\d\d\b|\b\d+(\.\d+)?\s*(mg|mcg|ml|cc|units?|miles?|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|visits?|sessions?|times|percent|%|lbs?|pounds?|feet|ft|inch\w*|mmhg|bpm|liters?|l)\b|"
           r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|once|twice|daily|weekly|monthly|bi-?weekly)\b|"
           r"\b(records?|report|PCR|PCS|run sheet|notes?|chart|certification|re-?certification|plan of care|POC|OASIS|assessment|evaluation|order|summary|letter|affidavit|physician|doctor|nurse|therapist|paramedic|EMT|crew|testimony|testified)\b[^.]{0,60}"
           r"\b(state[sd]?|indicate[sd]?|document(s|ed)?|show(s|ed)?|note[sd]?|report(s|ed)?|reflect(s|ed)?|record(s|ed)?|describe[sd]?|identif(y|ies|ied)|ordered|prescribed|certified|testified|wrote)\b")
META = R(r"\b(below|herein|hereinafter)\b|\bas (discussed|noted|stated|set forth|described) above\b|\b(described|discussed|set forth) in the [a-z ]{0,30}above\b|\bevaluated separately\b|^(to summarize|in summary|in conclusion)\b")
ANCH = R(r"\d|\b(january|february|march|april|may|june|july|august|september|october|november|december|patient|beneficiar\w*|diagnos\w+|admit\w*|discharg\w*|hospital\w*|transport\w*|ambulance|oxygen|therap\w+|nurs\w+|physician|doctor|"
         r"nurse|wound\w*|pain|blood|fractur\w*|surg\w+|medicat\w+|inject\w+|dialysis|stroke|pneumonia|infect\w+|edema|ambulat\w+|wheelchair|bed\w*|confined|homebound|transfer\w*|assist\w*|mobility|plan of care|certif\w+|"
         r"order\w*|visit\w*|session\w*|treat\w+|rehabilitat\w+|stay|days?|hours?|minutes?|weeks?|months?|symptom\w*|condition|disease|cancer|heart|cardiac|respiratory|chest|facility|home health|skilled|supply|supplies|equipment)\b")
REC_SRC = R(r"\b(report|records?|notes?|chart|PCR|PCS|certification|plan of care|orders?|summary|assessment|evaluation|form|letter|affidavit|testified|testimony|exhibit|documented)\b")
RECCITE = R(r"\bExhs?\.|\bId\.|\bFile\b|\bat \d")
CITE_ONLY = R(r"\b(Exhs?\.|Exhibits?|File|Id\.|Dec\.|Tr\.|See|at|pp?\.|MAC)\b|[\d,;.\-\u2013()]+|\b[A-Z]\.[A-Z]\.\d*\b")


CITE_STRIP = [re.compile(p) for p in (r"\b(?:See|see)(?: also| generally)?(?:, e\.g\.,)?\s+(?=[A-Z]\.|Exh|Id|Dec)", r"\b(?:[A-Z]\.){1,3}\d*\s*(?:File|Exh)[^.;]*?(?:Exhs?\.[^.;]*)?(?:;|\.(?=\s|$))",
                                    r"\bExhs?\.\s*[A-Za-z0-9\-]+(?:\s*(?:,|and|&)\s*[A-Za-z0-9\-]+)*(?:\s+at\s+[\d\-,\s]+)?", r"\bId\.(?:\s+at\s+[\d\-,\s]+)?", r"\bDec\.\s+at\s+[\d\-]+", r"\bTr\.\s+at\s+[\d\-]+")]


def core(s):
    for rx in CITE_STRIP: s = rx.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def cite_only(s): return len(CITE_ONLY.sub(" ", s).split()) < 5 or bool(re.match(r"^(([A-Z]\.){1,3}\d*\s*File|Exhs?\.|Dec\.)", s))


def tag_sentence(s, section):
    """-> (tag, reason).  Priority: terminal/law section > council voice > procedure/liability > law cue > ALJ > earlier-level > party > record gap > evaluation > fact."""
    if section == "TERMINAL": return "TERMINAL", "after DECISION/CONCLUSION header"
    full = s; s = core(s)
    m = COUNCIL.search(s) or DISP.search(s)
    if m: return "COUNCIL", m.group(0)
    m = PROC.search(s)
    if m: return "PROC", m.group(0)
    if REASON.search(s): return "EVAL", "reasoning connective"
    m = LAW_CS.search(full) or LAW_CI.search(full)
    if m: return "LAW", m.group(0)
    m = LAWSTMT.search(s)
    if m: return "LAW", "law statement: " + m.group(0)
    m = ALJ.search(s) or ALJ_FULL.search(full)
    if m: return "PRIOR_ALJ", m.group(0)
    m = PRIOR_CS.search(s) or PRIOR_CI.search(s) or PRIOR_PASSIVE.search(s)
    if m: return "PRIOR_DENIAL", m.group(0)
    if cite_only(full) or len(s.split()) < 6: return "CITE", "cite/short"
    if PARTY.search(s): return "PARTY", PARTY.search(s).group(0)[:40]
    if PROC_SOFT.search(s): return "PROC", PROC_SOFT.search(s).group(0)
    m = EVAL_STRONG.search(s)
    if m: return "EVAL", m.group(0)
    m = GAP.search(s)
    if m: return "GAP", m.group(0)[:40]
    m = EVAL.search(s)
    if m: return "EVAL", m.group(0)
    if META.search(s): return "OTHER", "meta/reference sentence"
    m = LAWSTMT.search(s)
    if m: return "LAW", "law statement: " + m.group(0)
    if section == "LAW" and not PATREF.search(s): return "LAW", "law section, no patient reference"
    if not (ANCH.search(s) or PATREF.search(s)): return "OTHER", "no record anchor"
    return ("FACT", "") if STRICT.search(s) else ("FACT_WEAK", "no date/number/record-source anchor")


SEC_MAP = [(R(r"conclusion|^decision$|^order$|disposition|summary of (the )?decision"), "TERMINAL"), (R(r"law|authorit|standard|statut|regulat|legal|framework|jurisdiction"), "LAW"),
           (R(r"background|facts?\b|history|summary|overview"), "FACTS"), (R(r"discussion|analysis|findings|issues?\b|contentions|arguments"), "MIXED")]


def header_section(t, cur):
    if len(t.split()) > 8: return cur
    for rx, sec in SEC_MAP:
        if rx.search(t): return sec
    return cur


def is_header(p):
    t = p["text"]; ws = t.split(); w = len(ws)
    if w > 12 or p["nlines"] > 3: return False
    if t.isupper(): return True
    if re.search(r"[.?!;:,]\s*[\"\u201d]?$", t) or re.search(r"\b(or|and)$", t): return False
    caps = sum(1 for x in ws if x[:1].isupper() or x[:1].isdigit() or x[:1] in "(\u00a7/")
    return caps / w >= 0.7 or p["indent"] >= 12


def analyze(cid):
    """-> (paragraph list, flat sentence list with tags).  Sentence dict: pi, si, section, text, tag, reason."""
    raw = open(RAW / f"{cid}.txt", encoding="utf-8", errors="replace").read()
    paras = paragraphs(raw); sec = "INTRO"; sents = []
    for pi, p in enumerate(paras):
        if is_header(p):
            sec = header_section(p["text"], sec); p["kind"] = "HEADER"; p["section"] = sec; continue
        p["kind"] = "PARA"; p["section"] = sec
        ss = split_sentences(p["text"]); tags = [tag_sentence(s, sec) for s in ss]
        cf = next((i for i, t in enumerate(tags) if t[0] == "COUNCIL"), None)
        if sec in ("MIXED", "INTRO", "LAW") and cf is not None:     # from the first Council-voice sentence on, the paragraph is reasoning (record-gap sentences are kept for arm B)
            tags = [(t if (i < cf or t[0] in ("GAP", "COUNCIL", "PROC", "LAW")) else (("COUNCIL_REC", "record-report sentence inside Council paragraph") if (t[0] in ("FACT", "FACT_WEAK", "PARTY") and REC_SRC.search(ss[i]) and RECCITE.search(ss[i])) else ("COUNCIL_PARA", "after Council-voice sentence in paragraph"))) for i, t in enumerate(tags)]
        if sec != "TERMINAL" and ALJ_FULL.search(ss[-1]) and not any(t[0] == "COUNCIL" for t in tags): tags = [(t if t[0] in ("PROC", "LAW", "CITE", "COUNCIL") else ("PRIOR_ALJ", "paragraph cites the ALJ decision")) for t in tags]
        if sec != "TERMINAL":
            first = next((i for i, t in enumerate(tags) if t[0] in ("PRIOR_ALJ", "PRIOR_DENIAL")), None)
            if first is not None:
                kind = tags[first][0]
                tags = [(t if (i < first or t[0] in ("PRIOR_ALJ", "PRIOR_DENIAL", "COUNCIL", "COUNCIL_PARA", "PROC", "LAW", "CITE", "PARTY")) else (kind + "_CONT", "after earlier-level sentence in same paragraph")) for i, t in enumerate(tags)]
        for si, (s, (tg, why)) in enumerate(zip(ss, tags)):
            if p["text"][:1].islower() and si == 0: tg, why = "FRAGMENT", "starts lowercase (page-break artifact)"
            sents.append(dict(pi=pi, si=si, section=sec, text=s, tag=tg, reason=why))
    return paras, sents


def units(sents, tagset):
    """kept sentences -> fact units (consecutive kept sentences of one paragraph, <= MAXW words)."""
    out, cur, cw, cpi = [], [], 0, None
    for s in sents:
        if s["tag"] not in tagset: continue
        w = len(s["text"].split())
        if cur and (s["pi"] != cpi or cw + w > MAXW): out.append(" ".join(cur)); cur, cw = [], 0
        cur.append(s["text"]); cw += w; cpi = s["pi"]
    if cur: out.append(" ".join(cur))
    return out


# ------------------------------------------------------------------ 4. build / audit
def tags_info():
    return json.load(open(TAGS))["cases"]


def rules_hash():
    return hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:16]


def build(sets):
    info = tags_info(); summary = []
    for st in sets:
        ids = sorted(k for k, v in info.items() if v["set"] == st)
        for arm in ARMS: (OUT / f"{arm}_{st}").mkdir(parents=True, exist_ok=True)
        (OUT / "tags").mkdir(parents=True, exist_ok=True)
        for cid in ids:
            src = json.load(open(SRC[st] / f"{cid}.json")); paras, sents = analyze(cid)
            norm = " ".join(p["text"] for p in paras)
            json.dump(dict(case_id=cid, sentences=sents), open(OUT / "tags" / f"{cid}.json", "w"), indent=0)
            wA = sum(len(x["text"].split()) for x in sents if x["tag"] in ARMS["A_strict"]); wD = sum(len(x["text"].split()) for x in sents if x["tag"] in ARMS["D_wide"])
            for arm, ts in ARMS.items():
                u = units(sents, ts)
                bad = [s["text"] for s in sents if s["tag"] in ts and s["text"] not in norm]
                c = {k: src.get(k) for k in ("case_id", "domain", "docket", "service_at_issue", "reference_outcome", "outcome_note", "cited_sections", "other_cites")}
                c.update(facts=u, arm=arm, set=st, coverage_label=info[cid]["coverage_label"], issue_type=info[cid]["issue_type"], include_primary=info[cid]["include_primary"],
                         evidence_words_A=wA, evidence_words_D=wD, evidence_ok=int(wA >= EV_A and wD >= EV_D),
                         build=dict(tool="rag/fairtest.py", rules_sha=rules_hash(), verbatim_failures=len(bad)))
                json.dump(c, open(OUT / f"{arm}_{st}" / f"{cid}.json", "w"), indent=1)
            summary.append(cid)
    print("built", len(summary), "cases; rules", rules_hash())


def toks(s):
    stop = set("the a an of to in on and or for was were is are that this with by as at from be been has have had it its not no".split())
    return {w for w in re.findall(r"[a-z0-9]{3,}", s.lower()) if w not in stop}


def recall(piece, sent):
    a = toks(piece)
    return len(a & toks(sent)) / len(a) if a else 0.0


VERDICT = R(r"\b(revers\w+|affirm\w+|remand\w+|liable|not covered|non-?covered|reasonable and necessary|medically necessary|council|we find|we conclude)\b")


def audit(sets, verbose=True):
    info = tags_info(); rep = {}
    for st in sets:
        aud = collections.defaultdict(list)
        for r in json.load(open(AUDIT[st])):
            if r["label"] in ("ADJUDICATOR_FINDING", "MIXED") and r.get("leak_text"): aud[r["case_id"]].append(r)
        ids = sorted(k for k, v in info.items() if v["set"] == st)
        for arm, ts in ARMS.items():
            tot = collections.Counter(); rows = []
            for cid in ids:
                sents = json.load(open(OUT / "tags" / f"{cid}.json"))["sentences"]; kept = [s["text"] for s in sents if s["tag"] in ts]
                raw_w = sum(len(p["text"].split()) for p in paragraphs(open(RAW / f"{cid}.txt", encoding="utf-8", errors="replace").read()))
                good = []
                for f in json.load(open(SURG[st] / f"{cid}.json"))["facts"]: good += [g for g in split_sentences(f) if len(g.split()) >= 6]
                hit_good = sum(1 for g in good if any(recall(g, k) >= 0.8 for k in kept))
                leaks = 0
                for r in aud[cid]:
                    parts = [p for p in re.split(r"\s*(?:\.\.\.|\u2026)\s*", r["leak_text"]) if len(p.strip()) > 8] or [r["leak_text"]]
                    if any(recall(p, k) >= 0.6 for p in parts for k in kept): leaks += 1
                vw = sum(1 for k in kept if VERDICT.search(k))
                rows.append(dict(case=cid, sents=len(kept), words=sum(len(k.split()) for k in kept), raw_words=raw_w, good=len(good), good_hit=hit_good, leak_facts=len(aud[cid]), leak_hit=leaks, verdict_word_sents=vw))
                for k, v in rows[-1].items():
                    if k != "case": tot[k] += v
            rep[f"{st}/{arm}"] = dict(total=dict(tot), rows=rows)
            if verbose:
                t = tot; print(f"{st:4s} {arm:9s} cases={len(ids)} sents={t['sents']} words={t['words']} ({100*t['words']/t['raw_words']:.0f}% of decision) known-good recall={t['good_hit']}/{t['good']} ({100*t['good_hit']/max(1,t['good']):.0f}%) "
                              f"known-leak facts hit={t['leak_hit']}/{t['leak_facts']} verdict-word sentences={t['verdict_word_sents']}")
    json.dump(rep, open(ROOT / f"results/review/fairtest_audit_{'_'.join(sets)}.json", "w"), indent=1)
    return rep


def dump(cid, only=None, width=170):
    paras, sents = analyze(cid); cnt = collections.Counter(s["tag"] for s in sents)
    print(cid, dict(cnt))
    last = None
    for s in sents:
        if only and s["tag"] not in only: continue
        if s["pi"] != last: print(f"--- [{paras[s['pi']]['section']}]"); last = s["pi"]
        print(f"{s['tag']:12s}| {s['text'][:width]}" + (f"   <{s['reason']}>" if s["reason"] else ""))
    for i, p in enumerate(paras):
        if p["kind"] == "HEADER": print(f"HEADER[{p['section']}] {p['text'][:80]}")


def freeze():
    h = rules_hash(); json.dump(dict(rules_sha=h, file="rag/fairtest.py", note="Rules/cues tuned on the 22 dev decisions only. Frozen before the 18 held-out decisions were built."), open(ROOT / "results/fairtest_freeze.json", "w"), indent=1)
    print("frozen", h)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["dump", "build", "audit", "freeze"]); ap.add_argument("--case"); ap.add_argument("--sets", default="dev"); ap.add_argument("--only")
    a = ap.parse_args(); sets = a.sets.split(",")
    if a.cmd == "dump": dump(a.case, set(a.only.split(",")) if a.only else None)
    elif a.cmd == "build": build(sets)
    elif a.cmd == "audit": audit(sets)
    else: freeze()
