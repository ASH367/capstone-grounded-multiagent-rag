"""OPTIONAL, UNTESTED in the sandbox (Hugging Face is not reachable there). Run on your Mac:
   pip install sentence-transformers ; python3 -m rag.embed_retriever
Adds a dense-embedding retriever and prints the same dev/test table as rag/eval_retrieval_v2.py.
Choose the retriever on DEV only; report TEST once."""
import numpy as np
from sentence_transformers import SentenceTransformer
from rag import eval_retrieval_v2 as E          # reuses data, split and scoring (this also prints the sandbox-friendly table)

class Dense:
    name = "dense"
    def __init__(self, chunks, model="sentence-transformers/all-MiniLM-L6-v2"):
        self.m = SentenceTransformer(model); self.Z = self.m.encode([c["text"] for c in chunks], normalize_embeddings=True, show_progress_bar=True)
    def scores(self, q): return self.Z @ self.m.encode([q], normalize_embeddings=True)[0]

if __name__ == "__main__":
    d = Dense(E.chunks); h = E.Hybrid([E.bm, d], name="hybrid bm25+dense")
    for name, r in (("dense", d), ("hybrid bm25+dense", h)):
        print(name, "DEV ", E.score(r, "dev", True))
    print("Pick on DEV, then run:  E.score(<chosen>, 'test', True)")
