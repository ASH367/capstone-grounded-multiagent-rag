"""
Milestone 1 - Ingestion.

Reads the two REAL public CMS documents in data/policies/ (text extracted from the
original PDFs with `pdftotext -layout`) and splits them into citable chunks:

  * cms_opd_prior_auth_faq.txt  -> one chunk per FAQ question  (chunk_id "FAQ-Q<n>")
  * lcd_l38765_facet_joint_interventions.txt -> one chunk per LCD criterion block /
    numbered limitation / numbered non-covered item (chunk_id "LCD-...")

Every chunk keeps doc_id + chunk_id + label so any finding can cite its source.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
POLICY_DIR = ROOT / "data" / "policies"
INDEX_DIR = ROOT / "data" / "index"

FAQ_FILE = "cms_opd_prior_auth_faq.txt"
LCD_FILE = "lcd_l38765_facet_joint_interventions.txt"
FAQ_ID = "CMS_OPD_PA_FAQ_2024-11-14"
LCD_ID = "LCD_L38765_v27"


def _clean(text: str) -> list[str]:
    """Drop PDF page furniture (URL footers, print headers, page numbers, date headers)."""
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            out.append("")
            continue
        if s.startswith("https://www.cms.gov/medicare-coverage-database"):
            continue
        if re.match(r"^\d+/\d+/\d+, \d+:\d+ [AP]M", s):
            continue
        if re.fullmatch(r"\d{1,2}", s):  # bare page number
            continue
        if s == "November 14, 2024":
            continue
        out.append(s)
    return out


def _norm(lines: list[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def chunk_faq(text: str) -> list[dict]:
    lines = _clean(text)
    chunks, cur_n, cur = [], None, []
    for line in lines:
        m = re.match(r"^(\d+)\. Q:\s*(.*)", line)
        if m:
            if cur_n is not None:
                chunks.append((cur_n, cur))
            cur_n, cur = int(m.group(1)), [m.group(2)]
        elif cur_n is not None:
            cur.append(line)
    if cur_n is not None:
        chunks.append((cur_n, cur))
    return [
        {"doc_id": FAQ_ID, "chunk_id": f"FAQ-Q{n}", "label": f"OPD PA FAQ, Q{n}",
         "text": _norm(body)}
        for n, body in chunks
    ]


def chunk_lcd(text: str) -> list[dict]:
    lines = _clean(text)
    full = "\n".join(lines)
    start = full.index("Coverage Indications, Limitations, and/or Medical Necessity")
    end = full.index("Definitions", start)
    body = full[start:end]

    def seg(a: str, b: str | None) -> str:
        i = body.index(a)
        j = body.index(b, i) if b else len(body)
        return body[i:j]

    chunks = []

    def add(cid, label, txt):
        chunks.append({"doc_id": LCD_ID, "chunk_id": cid, "label": label,
                       "text": _norm(txt.splitlines())})

    add("LCD-INDICATIONS", "LCD L38765, Indications (criteria 1-4)",
        seg("Facet joint interventions are considered medically reasonable", "A. Diagnostic Facet Joint Procedures"))
    add("LCD-A-DIAGNOSTIC", "LCD L38765, A. Diagnostic procedures",
        seg("A. Diagnostic Facet Joint Procedures", "B. Therapeutic Facet Joint Procedures"))
    add("LCD-B-THERAPEUTIC", "LCD L38765, B. Therapeutic procedures",
        seg("B. Therapeutic Facet Joint Procedures", "C. Facet Joint Denervation"))
    add("LCD-C-DENERVATION", "LCD L38765, C. Facet joint denervation (RFA)",
        seg("C. Facet Joint Denervation", "D. Facet Cyst Aspiration/Rupture"))
    add("LCD-D-CYST", "LCD L38765, D. Facet cyst aspiration/rupture",
        seg("D. Facet Cyst Aspiration/Rupture", "Limitations\n"))

    lim = seg("Limitations\n", "The following are considered not reasonable")
    nonc = seg("The following are considered not reasonable", "Note: The scales")
    for kind, block, prefix, name in (("LIM", lim, "LIM", "Limitation"),
                                     ("NC", nonc, "NC", "Non-covered item")):
        parts = re.split(r"(?m)^(\d{1,2})\. ", block)
        # parts = [preamble, n1, text1, n2, text2, ...]
        for k in range(1, len(parts) - 1, 2):
            add(f"LCD-{prefix}{parts[k]}", f"LCD L38765, {name} {parts[k]}", parts[k + 1])

    add("LCD-SCALES", "LCD L38765, Acceptable pain/disability scales",
        seg("Note: The scales", "Notice:"))
    add("LCD-PROVIDER", "LCD L38765, Provider qualifications",
        seg("Provider Qualifications:", None))
    return chunks


def ingest_all() -> list[dict]:
    chunks = chunk_faq((POLICY_DIR / FAQ_FILE).read_text())
    chunks += chunk_lcd((POLICY_DIR / LCD_FILE).read_text())
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    (INDEX_DIR / "chunks.json").write_text(json.dumps(chunks, indent=2))
    return chunks


if __name__ == "__main__":
    cs = ingest_all()
    by_doc = {}
    for c in cs:
        by_doc[c["doc_id"]] = by_doc.get(c["doc_id"], 0) + 1
    print(f"Wrote {len(cs)} chunks -> data/index/chunks.json  {by_doc}")
