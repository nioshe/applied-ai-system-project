"""Tiny dependency-free TF-IDF retriever over the VibeFinder knowledge base."""
import json
import math
import re
from collections import Counter
from typing import Dict, List, Tuple

STOPWORDS = {
    "a", "an", "the", "i", "me", "my", "to", "for", "of", "and", "or", "in", "on", "at", "is", "it", "some",
    "want", "need", "like", "give", "play", "music", "songs", "song", "something", "with", "that", "this",
    "when", "while", "so", "be", "am", "are", "can", "you", "please", "feel", "feeling", "something",
}


def tokenize(text: str) -> List[str]:
    """Lowercase, split into words, drop stopwords, and crudely strip a plural 's'."""
    words = re.findall(r"[a-z0-9&']+", text.lower())
    return [_stem(w) for w in words if w not in STOPWORDS]


def _stem(w: str) -> str:
    """Very small stemmer: studying -> study, rains -> rain."""
    if len(w) > 5 and w.endswith("ing"):
        return w[:-3]
    if len(w) > 3 and w.endswith("s"):
        return w[:-1]
    return w


def load_knowledge_base(path: str) -> List[Dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Retriever:
    """Ranks knowledge-base documents against a query by TF-IDF cosine similarity."""

    def __init__(self, docs: List[Dict]):
        if not docs:
            raise ValueError("Retriever needs at least one document")
        self.docs = docs
        self.doc_tokens = [tokenize(f"{d['title']} {d['text']} {d['keywords']}") for d in docs]
        n = len(docs)
        df = Counter(t for toks in self.doc_tokens for t in set(toks))
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}
        self.doc_vecs = [self._vec(toks) for toks in self.doc_tokens]

    def _vec(self, tokens: List[str]) -> Dict[str, float]:
        tf = Counter(t for t in tokens if t in self.idf)
        vec = {t: c * self.idf[t] for t, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def search(self, query: str, k: int = 3) -> List[Tuple[Dict, float]]:
        """Return up to k (doc, cosine score) pairs, best first, skipping zero-score docs."""
        q = self._vec(tokenize(query))
        if not q:
            return []
        scored = [(d, sum(w * dv.get(t, 0.0) for t, w in q.items())) for d, dv in zip(self.docs, self.doc_vecs)]
        scored = [(d, s) for d, s in scored if s > 0]
        return sorted(scored, key=lambda x: x[1], reverse=True)[:k]
