"""Section-aware chunking of CMS Medicare Benefit Policy Manual chapters (public PDFs -> text)."""
import re, json, pathlib
RAW = pathlib.Path("data/raw/text")
MANUALS = {"MBPM ch.1": "bp102c01.txt", "MBPM ch.7": "bp102c07.txt", "MBPM ch.10": "bp102c10.txt"}
MANUALS_V3 = {**MANUALS, "MBPM ch.6": "bp102c06.txt", "MBPM ch.8": "bp102c08.txt"}   # v3 index adds ch.6 and ch.8 (separate from v2)
HEAD = re.compile(r"(?m)^\x0c?(\d{1,3}(?:\.\d+){0,5}(?:\.[A-Z])?)[ \u00a0]*[-\u2013\u2014][ \u00a0]*(\S.*)$")  # \x0c = pdftotext page break   # headings start at column 0 in the body
MAXW = 220

def clean(t):
    t = re.sub(r"(?m)^\s*Rev\. ?\d+.*$", "", t)
    t = re.sub(r"(?m)^\s*Medicare Benefit Policy Manual.*$", "", t)
    t = re.sub(r"(?m)^\s*Chapter \d+ - .*$", "", t)
    return re.sub(r"[ \t]+", " ", t)

def chunk_manual(doc, fname):
    txt = (RAW / fname).read_text()
    version = (re.search(r"\(Rev\. ?\d+; Issued: [\d-]+", txt) or [""])[0]
    body = txt[[m.start() for m in HEAD.finditer(txt)][0]:]            # skip table of contents (indented headings don't match)
    marks = list(HEAD.finditer(body)); out = []
    for i, m in enumerate(marks):
        seg = clean(body[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(body)])
        words = seg.split()
        for j in range(0, max(len(words), 1), MAXW):
            part = " ".join(words[j:j + MAXW])
            if len(part.split()) < 8: continue
            out.append({"doc": doc, "section": m.group(1), "title": m.group(2).strip(),
                        "part": j // MAXW, "label": f"{doc} §{m.group(1)}",
                        "text": f"{m.group(1)} {m.group(2).strip()}. {part}"})
    return out, version

def build(manuals=None, outdir="data/index_v2"):
    manuals = manuals or MANUALS
    chunks, versions = [], {}
    for doc, f in manuals.items():
        c, v = chunk_manual(doc, f); chunks += c; versions[doc] = v
    for i, c in enumerate(chunks): c["chunk_id"] = i
    pathlib.Path(outdir).mkdir(parents=True, exist_ok=True)
    json.dump({"versions": versions, "chunks": chunks}, open(outdir + "/chunks.json", "w"), indent=1)
    return chunks, versions

if __name__ == "__main__":
    import sys
    v3 = len(sys.argv) > 1 and sys.argv[1] == "v3"
    chunks, versions = build(MANUALS_V3, "data/index_v3") if v3 else build()
    print("chunks:", len(chunks)); print(versions)
    for d in (MANUALS_V3 if v3 else MANUALS): print(d, sum(c["doc"] == d for c in chunks), "chunks,", len({c['section'] for c in chunks if c['doc']==d}), "sections")
