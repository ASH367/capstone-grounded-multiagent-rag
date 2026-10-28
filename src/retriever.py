"""
Milestone 1 — Retrieval layer.

Baseline retrieval method: TF-IDF + cosine similarity over subsection-level
chunks. This is the single-agent-era retrieval baseline referenced in the
project's Milestone 2 plan (where dense embeddings will be compared against
this baseline to measure what, if anything, embedding retrieval buys us on
precision of citation).
"""
import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

INDEX_DIR = Path(__file__).parent.parent / "data" / "index"


class PolicyRetriever:
    def __init__(self, chunks_path: Path = INDEX_DIR / "chunks.json"):
        self.chunks = json.loads(chunks_path.read_text())
        self.texts = [c["text"] for c in self.chunks]
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform(self.texts)

    def retrieve(self, query: str, doc_filter: str | None = None, top_k: int = 3) -> list[dict]:
        """Return top_k chunks most relevant to query, optionally restricted to one doc_id."""
        q_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self.matrix)[0]

        ranked = sorted(
            range(len(self.chunks)), key=lambda i: sims[i], reverse=True
        )
        results = []
        for i in ranked:
            chunk = self.chunks[i]
            if doc_filter and chunk["doc_id"] != doc_filter:
                continue
            if sims[i] <= 0:
                continue
            results.append({**chunk, "score": round(float(sims[i]), 4)})
            if len(results) >= top_k:
                break
        return results


if __name__ == "__main__":
    r = PolicyRetriever()
    test_query = "conservative therapy failure before spinal fusion surgery"
    hits = r.retrieve(test_query, doc_filter="medical_necessity_lumbar_fusion", top_k=3)
    print(f"Query: {test_query}\n")
    for h in hits:
        print(f"  [score={h['score']}] {h['doc_id']} / {h['subsection']}")
        print(f"    {h['text'][:120]}...")
