"""Two baselines: TF-IDF cosine and flat BM25 over concatenated fields."""
from __future__ import annotations

import math
from collections import Counter

from text import normalize_tokens

K1, B = 1.2, 0.75


class Tfidf:
    name = "tfidf"

    def __init__(self, index):
        self.index = index
        self.n = index["n"]
        self.tfs = []
        self.lengths = []
        self.postings: dict[str, list[tuple[int, int]]] = {}
        df: Counter = Counter()
        for did in range(self.n):
            text = " ".join((index["docs"][did][2], index["text"][did][0],
                             index["text"][did][1], index["docs"][did][4]))
            toks = normalize_tokens(text)
            tf = Counter(toks)
            self.tfs.append(tf)
            self.lengths.append(math.sqrt(sum(v * v for v in tf.values())) or 1.0)
            for term, n in tf.items():
                self.postings.setdefault(term, []).append((did, n))
            df.update(tf.keys())
        self.idf = {t: math.log((self.n + 1) / (c + 0.5)) for t, c in df.items()}

    def search(self, query: str, limit: int = 10):
        return self.search_terms(normalize_tokens(query), limit)

    def search_terms(self, terms: list[str], limit: int = 10):
        q = Counter(terms)
        qnorm = math.sqrt(sum(v * v for v in q.values())) or 1.0
        scores = {}
        for term, qtf in q.items():
            if term not in self.idf:
                continue
            for did, _ in self.postings.get(term, []):
                tf = self.tfs[did][term]
                scores[did] = scores.get(did, 0.0) + qtf * self.idf[term] * tf * self.idf[term]
        out = [(s / (qnorm * self.lengths[did]), did) for did, s in scores.items()]
        out.sort(key=lambda x: (-x[0], self.index["docs"][x[1]][1]))
        return [(did, score) for score, did in out[:limit]]


class FlatBM25:
    name = "flat_bm25"

    def __init__(self, index):
        self.index = index
        self.n = index["n"]
        self.tfs = []
        self.lengths = []
        self.postings: dict[str, list[tuple[int, int]]] = {}
        df: Counter = Counter()
        for did in range(self.n):
            text = " ".join((index["docs"][did][2], index["text"][did][0],
                             index["text"][did][1], index["docs"][did][4]))
            tf = Counter(normalize_tokens(text))
            self.tfs.append(tf)
            self.lengths.append(sum(tf.values()))
            for term, n in tf.items():
                self.postings.setdefault(term, []).append((did, n))
            df.update(tf.keys())
        self.avg = sum(self.lengths) / max(self.n, 1)
        self.idf = {t: math.log(1 + (self.n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def search(self, query: str, limit: int = 10):
        return self.search_terms(normalize_tokens(query), limit)

    def search_terms(self, terms: list[str], limit: int = 10):
        scores = {}
        for term in terms:
            if term not in self.idf:
                continue
            for did, _ in self.postings.get(term, []):
                tf = self.tfs[did][term]
                norm = tf / (1 - B + B * self.lengths[did] / self.avg)
                scores[did] = scores.get(did, 0.0) + self.idf[term] * norm * (K1 + 1) / (K1 + norm)
        out = sorted(scores.items(), key=lambda kv: (-kv[1], self.index["docs"][kv[0]][1]))
        return out[:limit]
