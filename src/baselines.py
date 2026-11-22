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
        df: Counter = Counter()
        for did in range(self.n):
            text = " ".join((index["docs"][did][2], index["text"][did][0],
                             index["text"][did][1], index["docs"][did][4]))
            toks = normalize_tokens(text)
            tf = Counter(toks)
            self.tfs.append(tf)
            self.lengths.append(math.sqrt(sum(v * v for v in tf.values())) or 1.0)
            df.update(tf.keys())
        self.idf = {t: math.log((self.n + 1) / (c + 0.5)) for t, c in df.items()}

    def search(self, query: str, limit: int = 10):
        q = Counter(normalize_tokens(query))
        qnorm = math.sqrt(sum(v * v for v in q.values())) or 1.0
        scores = {}
        for term, qtf in q.items():
            if term not in self.idf:
                continue
            for did, tf in self.index["terms"].get(term, {}).get("x", []) + \
                    self.index["terms"].get(term, {}).get("t", []):
                scores[did] = scores.get(did, 0.0) + qtf * self.idf[term] * tf * self.idf[term]
        out = []
        for did, s in scores.items():
            out.append((s / (qnorm * self.lengths[did]), did))
        out.sort(key=lambda x: -x[0])
        return [(did, score) for score, did in out[:limit]]


class FlatBM25:
    name = "flat_bm25"

    def __init__(self, index):
        self.index = index
        self.n = index["n"]
        self.tfs = []
        self.lengths = []
        df: Counter = Counter()
        for did in range(self.n):
            text = " ".join((index["docs"][did][2], index["text"][did][0],
                             index["text"][did][1], index["docs"][did][4]))
            tf = Counter(normalize_tokens(text))
            self.tfs.append(tf)
            self.lengths.append(sum(tf.values()))
            df.update(tf.keys())
        self.avg = sum(self.lengths) / max(self.n, 1)
        self.idf = {t: math.log(1 + (self.n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def search(self, query: str, limit: int = 10):
        scores = {}
        for term in normalize_tokens(query):
            if term not in self.idf:
                continue
            for did, tf in self.index["terms"].get(term, {}).get("x", []) + \
                    self.index["terms"].get(term, {}).get("t", []):
                # The x and t postings can name the same doc. Fusion uses a
                # small title multiplier instead of double counting raw tf.
                prev = scores.get(did, 0.0)
                norm = tf / (1 - B + B * self.lengths[did] / self.avg)
                scores[did] = prev + self.idf[term] * norm * (K1 + 1) / (K1 + norm)
        out = sorted(scores.items(), key=lambda kv: -kv[1])
        return out[:limit]
