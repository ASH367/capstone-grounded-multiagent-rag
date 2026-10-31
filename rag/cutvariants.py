"""Candidate 'story-keeping' cuts (DEV ONLY, exploratory).  The frozen tagger (rag/fairtest.py, v1.1) is NOT changed.
It drops every sentence after the first Council-voice sentence in a paragraph (COUNCIL_PARA) and every sentence with an
evaluation phrase (EVAL), even when that sentence reports a record fact.  These variants try to RECOVER the record-fact part
of those sentences and still drop the Council's conclusion.
  S  sentence-level: keep a dropped sentence whole only if it has a record anchor and NO conclusion wording anywhere.
  M  S + clause-level: split a dropped sentence at conclusion connectives, keep clauses that are record facts with no conclusion wording.
  W  M + neutralise: strip 'the record shows/demonstrates that' lead-ins ('clearly', 'ample') and keep the bare record fact.
Verdict wording (covered / not covered / reasonable and necessary / we find ...) is never recovered by any variant."""
import re
from rag import fairtest as ft

R = lambda p: re.compile(p, re.I)
CONCL = R(r"\b(therefore|thus|accordingly|consequently|hence|as a result|we |our |council|conclud\w*|find(s|ing)?\b|establish\w*|demonstrat\w*|support(s|ed|ing)?\b|warrant\w*|justif\w*|outweigh\w*|insufficient|sufficient|adequate\w*|persuasive|credib\w*|reasonabl\w*|necessar\w*|unnecessar\w*|covered|coverage|payable|qualif\w*|meets?\b|satisf\w*|consistent with|clearly|ample|fails? to|failed to|unreasonabl\w*|appropriate\w*|valid\w*|prove[sd]?|deny|denied|denial|reverse\w*|affirm\w*|liable|liability|limitation on|weigh\w*|mean|means|meant|would|could have|should|critical|essential|important|issues?|unskilled|need for|appears? to|sole|remaining|opportunity|fair|likely|likelihood|threat\w*)\b")
PRIORLVL = R(r"\b(ALJ|ALJs|QIC|QICs|MAC|contractors?|intermediar\w+|carrier|redetermination|reconsideration|argument\w*|argues?|contends?|asserts?)\b")
SPLIT = R(r"\s*(?:;|,?\s+(?:and|but)\s+(?=(?:therefore|thus|so)\b)|,?\s+(?:because|therefore|thus|so that|which|whereas|although)\b|\s[-–—]\s)\s*")
LEAD = R(r"^(?:the |this |these |those |several |both |all )?(?:medical |clinical |nursing |hospital |emergency room |treatment |physician'?s? )*(?:records?|notes?|documents?|documentation|evidence|file|reports?|charts?|entries|orders?|plan of care|run sheet|PCR)(?:,? (?:including|such as)[^,]{0,80},)?\s+(?:also |clearly |plainly )?(?:show|indicate|reflect|document|demonstrate|reveal|establish|confirm|state|note|record|contain)(?:s|ed)?\s+(?:that\s+)?")
ANCHOR = lambda s: bool((ft.PATREF.search(s) or ft.REC_SRC.search(s)) and not PRIORLVL.search(s) and (ft.STRICT.search(s) or (ft.PATREF.search(s) and re.search(r"\b(was|were|had|has|received|admitted|transported|presented|complained|ordered|prescribed|signed|reported|noted|ambulat\w+|walk\w+|requir\w+|used|needed|stable|alert|oriented|unable|able|complained|found|monitored|underwent|reflects?|shows?)\b", s, re.I))))
BAD_START = R(r"^(see|id\.|exhs?\.|cf\.|rr at|tr\.|hearing cd)\b")
MINW = 6
RECOVER_FROM = {"COUNCIL_PARA", "EVAL"}      # only sentences the frozen tagger dropped as reasoning


def fact_clauses(text, variant):
    s = ft.core(text).strip()
    if BAD_START.search(s) or len(s.split()) < MINW: return []
    if variant == "S":
        return [text.strip()] if (ANCHOR(s) and not CONCL.search(s)) else []
    parts = [p.strip(" ,;.") for p in SPLIT.split(s) if p and p.strip(" ,;.")]
    out = []
    for p in parts:
        if variant == "W":
            q = LEAD.sub("", p).strip(" ,;.")
            if q and q != p and len(q.split()) >= MINW: p = q[0].upper() + q[1:]
        if len(p.split()) >= MINW and ANCHOR(p) and not CONCL.search(p) and not BAD_START.search(p): out.append(re.sub(r"\s+\d{1,3}\.$", ".", p if p.endswith(".") else p + "."))
    return out


def recovered(sentences, variant):
    """-> list of dict(pi, si, kept, orig, tag) for the sentences of one decision (tag file 'sentences')."""
    out = []
    for s in sentences:
        if s["tag"] not in RECOVER_FROM: continue
        for k in fact_clauses(s["text"], variant): out.append(dict(pi=s["pi"], si=s["si"], kept=k, orig=s["text"], tag=s["tag"]))
    return out


# ---- weak-fact reservoir: FACT_WEAK sentences (real record facts without a date/number anchor) that carry no conclusion/law/prior-level wording
LAWISH = R(r"\b(generally|will be considered|is considered|are considered|may be|can be|in order (to|for)|a patient (who|is|will|may)|patients (who|with|are)|an individual (is|who)|is defined|are defined|shall|must|requires? (that|a|the)|criteria|guidelines?|does not have to|may use|will be evaluated|considered under|final rule|manual notes|medical event|actual medical documentation|needed nurses)\b|^[\s\u2022\u00b7]*(the )?(severity|medical predictability|availability)|^\s*\d\)|^\s*\(")


def weak_ok(text):
    t = ft.core(text)
    return not (CONCL.search(t) or BAD_START.search(t) or PRIORLVL.search(t) or LAWISH.search(t) or ft.COUNCIL.search(t)) and len(t.split()) >= MINW


def retag(sents, variant):
    """Return a NEW sentence list in which story-keeping pieces are re-tagged FACT (variant: 'plus' = strict + clean weak facts; 'plusW' = plus + clause-level recoveries)."""
    out = []
    for s in sents:
        s = dict(s)
        if s["tag"] == "FACT_WEAK" and weak_ok(s["text"]): s["tag"], s["reason"] = "FACT", "recovered weak fact (no conclusion/law/prior-level wording)"
        elif variant == "plusW" and s["tag"] in RECOVER_FROM:
            ks = fact_clauses(s["text"], "W")
            if ks: s["text"], s["tag"], s["reason"] = " ".join(ks), "FACT", "recovered record-fact clause(s) from a reasoning sentence"
        out.append(s)
    return out
