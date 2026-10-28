"""Retrievers over the section-chunked CMS manuals. All expose scores(query)->np.array over chunks."""
import re, json, numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import linear_kernel
from rank_bm25 import BM25Okapi

STOP = set(TfidfVectorizer(stop_words="english").get_stop_words())
def toks(s): return [t for t in re.findall(r"[a-z0-9]+", s.lower()) if t not in STOP and len(t) > 2]

class Tfidf:
    name = "tfidf"
    def __init__(self, chunks):
        self.v = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        self.X = self.v.fit_transform([c["text"] for c in chunks])
    def scores(self, q): return linear_kernel(self.v.transform([q]), self.X).ravel()

class BM25:
    name = "bm25"
    def __init__(self, chunks, k1=1.5, b=0.75):
        self.m = BM25Okapi([toks(c["text"]) for c in chunks], k1=k1, b=b)
    def scores(self, q): return np.asarray(self.m.get_scores(toks(q)))

class LSA:
    name = "lsa"
    def __init__(self, chunks, dim=150):
        self.v = TfidfVectorizer(stop_words="english", sublinear_tf=True)
        X = self.v.fit_transform([c["text"] for c in chunks])
        self.svd = TruncatedSVD(n_components=min(dim, X.shape[1] - 1), random_state=7)
        Z = self.svd.fit_transform(X); self.Z = Z / (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9)
    def scores(self, q):
        z = self.svd.transform(self.v.transform([q])); z = z / (np.linalg.norm(z) + 1e-9)
        return (self.Z @ z.ravel())

class Hybrid:
    """Reciprocal rank fusion of several retrievers."""
    def __init__(self, parts, k=60, name=None): self.parts, self.k = parts, k; self.name = name or "hybrid(" + "+".join(p.name for p in parts) + ")"
    def scores(self, q):
        out = np.zeros(len(self.parts[0].scores("x")))
        for p in self.parts:
            order = np.argsort(-p.scores(q)); r = np.empty(len(order)); r[order] = np.arange(1, len(order) + 1)
            out += 1.0 / (self.k + r)
        return out
