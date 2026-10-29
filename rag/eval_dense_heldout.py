"""Retrieval on the HELD-OUT cases (index_v3, cases with an MBPM key): TF-IDF vs dense vs hybrid. Nothing is tuned on these cases.
  python3 -m rag.eval_dense_heldout                    # TF-IDF only (works anywhere)
  ollama pull nomic-embed-text ; python3 -m rag.eval_dense_heldout --dense ollama    # adds dense + hybrid (run on the Mac)
  pip install sentence-transformers ; python3 -m rag.eval_dense_heldout --dense st   # alternative
Hit = Council-cited section is in the top-k sections (exact), or the same/parent/child section (related)."""
import json, glob, argparse, urllib.request
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
ap = argparse.ArgumentParser(); ap.add_argument("--dense", choices=["ollama", "st"]); ap.add_argument("--model"); a = ap.parse_args()
chunks = json.load(open("data/index_v3/chunks.json"))["chunks"]
cases = [json.load(open(f)) for f in sorted(glob.glob("data/cases_v3_heldout_clean/*.json"))]
DOMDOC = {"home_health": "MBPM ch.7", "ambulance": "MBPM ch.10", "inpatient_rehab": "MBPM ch.1", "snf": "MBPM ch.8"}
corpus = {(c["doc"], c["section"]) for c in chunks}
def related(x, y): return x == y or x.startswith(y + ".") or y.startswith(x + ".")
vec = TfidfVectorizer(sublinear_tf=True, stop_words="english"); X = vec.fit_transform([c["text"] for c in chunks])
def tfidf(q): return (X @ vec.transform([q]).T).toarray().ravel()
def norm(s): s = np.asarray(s, float); return (s - s.mean()) / (s.std() + 1e-9)
R = {"tfidf": tfidf}
if a.dense:
    if a.dense == "ollama":
        m = a.model or "nomic-embed-text"
        def emb(t): 
            req = urllib.request.Request("http://localhost:11434/api/embeddings", json.dumps({"model": m, "prompt": t[:6000]}).encode(), {"Content-Type": "application/json"})
            return np.array(json.load(urllib.request.urlopen(req, timeout=300))["embedding"])
        Z = np.array([emb(c["text"]) for c in chunks])
    else:
        from sentence_transformers import SentenceTransformer
        st = SentenceTransformer(a.model or "sentence-transformers/all-MiniLM-L6-v2"); Z = st.encode([c["text"] for c in chunks], normalize_embeddings=True)
        emb = lambda t: st.encode([t], normalize_embeddings=True)[0]
    Z = Z / np.linalg.norm(Z, axis=1, keepdims=True)
    dense = lambda q: Z @ (emb(q) / np.linalg.norm(emb(q)))
    R["dense"] = dense; R["hybrid"] = lambda q: norm(tfidf(q)) + norm(dense(q))
def topk(sc, k, doc):
    out = []
    for i in np.argsort(-sc):
        if chunks[i]["doc"] != doc: continue
        key = (chunks[i]["doc"], chunks[i]["section"])
        if key not in out: out.append(key)
        if len(out) == k: break
    return out
for name, f in R.items():
    rows = {5: [], 10: []}; n = 0
    for c in cases:
        gold = [(g["doc"], g["section"]) for g in c.get("cited_sections", []) if (g["doc"], g["section"]) in corpus]
        if not gold: continue
        n += 1; sc = f(" ".join(c["facts"]))
        for k in (5, 10):
            top = topk(sc, k, DOMDOC[c["domain"]])
            rows[k].append((np.mean([g in top for g in gold]), np.mean([any(g[0] == t[0] and related(g[1], t[1]) for t in top) for g in gold])))
    print(f"{name:7s} n={n}  " + "  ".join(f"top{k}: exact {np.mean([r[0] for r in rows[k]]):.0%} related {np.mean([r[1] for r in rows[k]]):.0%}" for k in (5, 10)))
