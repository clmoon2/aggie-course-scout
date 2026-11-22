"""Query parsing, BM25F ranking, facets, snippets, and explanations."""
from __future__ import annotations

import gzip
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from text import STOPWORDS, normalize_tokens, stem, tokenize

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "web" / "data" / "index.json.gz"

SYNONYMS = {
    "ml": [["machine", "learning"]],
    "ai": [["artificial", "intelligence"]],
    "db": [["database"], ["databases"]],
    "dbs": [["database"]],
    "os": [["operating", "system"], ["operating", "systems"]],
    "sec": [["security"]],
    "security": [["cybersecurity"], ["cyber", "security"]],
    "stats": [["statistics"], ["statistical"]],
    "stat": [["statistics"]],
    "hci": [["human", "computer", "interaction"]],
    "net": [["network"], ["networking"]],
    "networks": [["networking"]],
    "nlp": [["natural", "language", "processing"]],
    "cv": [["computer", "vision"]],
    "se": [["software", "engineering"]],
    "oop": [["object", "oriented", "programming"]],
    "ds": [["data", "structures"]],
    "algos": [["algorithms"]],
    "math": [["mathematics"]],
    "bio": [["biology"]],
    "chem": [["chemistry"]],
    "econ": [["economics"]],
    "psych": [["psychology"]],
    "swe": [["software", "engineering"]],
}

FILTER_RE = re.compile(r"^(-?)(dept|level|credits):(.+)$", re.I)
CREDIT_RE = re.compile(r"^(>=|<=|>|<)?(\d+)$")


@dataclass
class Query:
    raw: str
    terms: list[str] = field(default_factory=list)
    phrases: list[list[str]] = field(default_factory=list)
    neg_terms: list[str] = field(default_factory=list)
    neg_phrases: list[list[str]] = field(default_factory=list)
    depts: list[str] = field(default_factory=list)
    neg_depts: list[str] = field(default_factory=list)
    levels: list[str] = field(default_factory=list)
    neg_levels: list[str] = field(default_factory=list)
    credits: tuple[str, int] | None = None
    synonyms: dict[str, list[list[str]]] = field(default_factory=dict)
    corrections: dict[str, str] = field(default_factory=dict)
    unknown: list[str] = field(default_factory=list)


def load_index(path: Path = INDEX_PATH) -> dict:
    with gzip.open(path, "rb") as f:
        idx = json.loads(f.read().decode("utf-8"))
    vocab = set()
    for desc, prereq, title in idx["text"]:
        vocab.update(tokenize(title + " " + desc + " " + prereq))
    vocab.update(idx["terms"].keys())
    idx["_vocab"] = sorted(t for t in vocab if t not in STOPWORDS and len(t) > 2)
    return idx


def _vocab(index: dict) -> list[str]:
    return index.get("_vocab", list(index["terms"]))


def edit_distance(a: str, b: str, cap: int = 3) -> int:
    """Damerau-Levenshtein with an early exit. Adjacent swaps cost one."""
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev2 = None
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        row_min = i
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            val = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                val = min(val, prev2[j - 2] + 1)
            cur.append(val)
            row_min = min(row_min, val)
        if row_min > cap:
            return cap + 1
        prev2, prev = prev, cur
    return prev[-1]


def suggest(term: str, vocab: list[str], limit: int = 3) -> list[str]:
    cap = 1 if len(term) <= 7 else 2
    scored = []
    for word in vocab:
        if abs(len(word) - len(term)) > cap:
            continue
        d = edit_distance(term, word, cap)
        if d <= cap and word != term:
            penalty = 0 if word[:1] == term[:1] else 0.4
            scored.append((d + penalty, -len(word), word))
    scored.sort()
    return [w for _, _, w in scored[:limit]]


def parse_query(raw: str, index: dict | None = None) -> Query:
    q = Query(raw=raw)
    vocab = _vocab(index) if index else []
    for piece in re.findall(r'-?"[^"]+"|\S+', raw):
        neg = piece.startswith("-")
        body = piece[1:] if neg else piece
        if body.startswith('"') and body.endswith('"') and len(body) >= 2:
            toks = normalize_tokens(body[1:-1])
            if toks:
                (q.neg_phrases if neg else q.phrases).append(toks)
            continue
        fm = FILTER_RE.match(body)
        if fm:
            val = fm.group(3).strip().lower()
            if fm.group(2).lower() == "dept":
                (q.neg_depts if neg else q.depts).append(val.upper())
            elif fm.group(2).lower() == "level":
                if val in ("undergraduate", "undergrad", "ug"):
                    (q.neg_levels if neg else q.levels).append("undergraduate")
                elif val in ("graduate", "grad"):
                    (q.neg_levels if neg else q.levels).append("graduate")
            else:
                cm = CREDIT_RE.match(val)
                if cm:
                    q.credits = (cm.group(1) or "=", int(cm.group(2)))
            continue
        toks = normalize_tokens(body)
        if not toks:
            continue
        if neg:
            q.neg_terms.extend(toks)
        else:
            q.terms.extend(toks)

    # Keep raw spellings so suggestions read as English instead of stems.
    pairs = []
    for raw_tok in tokenize(raw):
        if raw_tok in STOPWORDS or len(raw_tok) <= 1:
            continue
        pairs.append((stem(raw_tok), raw_tok))
    unknown = [t for t in q.terms if t not in index["terms"]] if index else []
    q.unknown = unknown
    for term in unknown:
        if len(term) < 4:
            continue
        raw_term = next((r for s, r in pairs if s == term), term)
        s = suggest(raw_term, vocab)
        if s:
            q.corrections[term] = s[0]
    for term in list(q.terms):
        for phrase in SYNONYMS.get(term, []):
            q.synonyms.setdefault(term, []).append(phrase)
    return q


def _doc_matches_filters(doc: list, q: Query) -> bool:
    code, dept, level, credits = doc[1], doc[3], doc[6], str(doc[7])
    if q.depts and dept not in q.depts:
        return False
    if q.neg_depts and dept in q.neg_depts:
        return False
    if q.levels and level not in q.levels:
        return False
    if q.neg_levels and level in q.neg_levels:
        return False
    if q.credits:
        op, val = q.credits
        try:
            c = float(credits.split("to")[0] or 0)
        except ValueError:
            return False
        if op == ">=" and c < val:
            return False
        if op == "<=" and c > val:
            return False
        if op == ">" and c <= val:
            return False
        if op == "<" and c >= val:
            return False
        if op == "=" and c != val:
            return False
    return True


def _phrase_docs(index: dict, phrase: list[str]) -> dict[int, int]:
    hits: dict[int, int] = {}
    for did, fields in enumerate(index["text"]):
        found = False
        for field_text in fields:
            toks = normalize_tokens(field_text)
            if any(toks[i:i + len(phrase)] == phrase for i in range(len(toks) - len(phrase) + 1)):
                found = True
                break
        if found:
            hits[did] = 1
    return hits


def search(index: dict, raw: str, limit: int = 10, weights: dict | None = None,
           use_synonyms: bool = True, explain: bool = True) -> dict:
    q = parse_query(raw, index)
    weights = weights or index["weights"]
    n = index["n"]
    scores: dict[int, float] = {}
    why: dict[int, dict] = {}
    matched_terms: dict[int, set] = {}

    def add_term(term: str, qweight: float, label: str) -> None:
        if term not in index["terms"]:
            normed = normalize_tokens(term)
            if not normed:
                return
            term = normed[0]
        post = index["terms"].get(term)
        if not post:
            return
        df = len({did for short in weights for did, _ in post.get(short, [])}) or 1
        idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
        contribs: dict[int, dict] = {}
        for short, w in weights.items():
            entries = post.get(short, [])
            avg = index["avglen"][short] or 1.0
            for did, tf in entries:
                dl = index["doclen"][short][did]
                norm = tf / (1 - index["b"] + index["b"] * dl / avg)
                wtf_so_far = contribs.setdefault(did, {"norm": 0.0, "fields": {}})["norm"]
                # BM25F saturates the total weighted tf, not each field.
                new_norm = wtf_so_far + w * norm
                contribs[did]["norm"] = new_norm
                contribs[did]["fields"][short] = {"tf": tf, "weight": w}
        for did, c in contribs.items():
            norm = c["norm"]
            if norm <= 0:
                continue
            inc = qweight * idf * norm * (index["k1"] + 1) / (index["k1"] + norm)
            scores[did] = scores.get(did, 0.0) + inc
            matched_terms.setdefault(did, set()).add(term)
            if explain:
                e = why.setdefault(did, {}).setdefault(label, {})
                e["idf"] = round(idf, 3)
                e["fields"] = c["fields"]
                e["contribution"] = round(e.get("contribution", 0) + inc, 2)

    if not q.terms and not q.phrases:
        # Filter-only query. Give every doc a neutral score so facets still work.
        scores = {did: 1.0 for did in range(n)}

    synonym_phrases = [ph for vals in q.synonyms.values() for ph in vals if len(ph) > 1]
    for term in q.terms:
        add_term(term, 0.5 if len(term) <= 3 else 1.0, term)
        if term in q.corrections:
            add_term(q.corrections[term], 0.55, f"~{q.corrections[term]}")
        if use_synonyms:
            for phrase in q.synonyms.get(term, []):
                if len(phrase) == 1:
                    add_term(phrase[0], 0.55, f"{term}~{phrase[0]}")
                else:
                    toks = normalize_tokens(" ".join(phrase))
                    for t in toks:
                        add_term(t, 0.5, f"{term}~{' '.join(phrase)}")

    phrase_info = []
    for phrase in q.phrases + [normalize_tokens(" ".join(p)) for p in synonym_phrases]:
        ph = [t for t in phrase if t]
        if len(ph) < 2:
            continue
        hits = _phrase_docs(index, ph)
        if not hits:
            continue
        df = len(hits)
        idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
        for did in hits:
            inc = 2.5 + idf
            # Exact phrase in a title is the strongest signal on this catalog.
            title_toks = normalize_tokens(index["text"][did][2])
            in_title = any(title_toks[i:i + len(ph)] == ph for i in range(len(title_toks) - len(ph) + 1))
            if in_title:
                inc += 2.0
            scores[did] = scores.get(did, 0.0) + inc
            matched_terms.setdefault(did, set()).update(ph)
            if explain:
                e = why.setdefault(did, {}).setdefault('"' + " ".join(ph) + '"', {})
                e["idf"] = round(idf, 3)
                e["fields"] = {"phrase": {"tf": 1, "weight": 2.5}, "title_bonus": in_title}
                e["contribution"] = round(inc, 2)
        phrase_info.append({"phrase": " ".join(ph), "docs": df})

    banned = set()
    for term in q.neg_terms:
        for did, _ in index["terms"].get(term, {}).get("x", []):
            banned.add(did)
    for phrase in q.neg_phrases:
        banned.update(_phrase_docs(index, phrase))

    ranked = []
    for did, score in scores.items():
        if did in banned:
            continue
        doc = index["docs"][did]
        if not _doc_matches_filters(doc, q):
            continue
        ranked.append((score, did))
    ranked.sort(key=lambda x: (-x[0], index["docs"][x[1]][1]))
    total = len(ranked)
    page = ranked[:limit]

    facets = {"dept": {}, "level": {}, "college": {}, "credits": {}}
    for _, did in ranked:
        d = index["docs"][did]
        facets["dept"][d[3]] = facets["dept"].get(d[3], 0) + 1
        facets["level"][d[6]] = facets["level"].get(d[6], 0) + 1
        facets["college"][d[5]] = facets["college"].get(d[5], 0) + 1
        cr = d[7] or "?"
        facets["credits"][cr] = facets["credits"].get(cr, 0) + 1

    results = []
    for score, did in page:
        d = index["docs"][did]
        desc, prereq, title = index["text"][did]
        results.append({
            "id": d[0], "code": d[1], "title": title, "dept": d[3],
            "department": d[4], "college": d[5], "level": d[6],
            "credits": d[7], "url": d[8], "score": round(score, 3),
            "snippet": snippet(desc, matched_terms.get(did, set())),
            "why": why.get(did, {}) if explain else {},
        })
    return {
        "query": raw, "total": total,
        "suggestion": next(iter(q.corrections.values()), None),
        "correction_map": q.corrections,
        "synonyms": {k: [" ".join(v) for v in vals] for k, vals in q.synonyms.items()},
        "results": results,
        "facets": {k: dict(sorted(v.items(), key=lambda kv: -kv[1])[:12]) for k, v in facets.items()},
        "parsed": {"terms": q.terms, "phrases": [" ".join(p) for p in q.phrases],
                   "depts": q.depts, "levels": q.levels,
                   "credits": q.credits, "unknown": q.unknown},
    }


def snippet(desc: str, terms: set[str], width: int = 26) -> str:
    words = desc.split()
    if not words:
        return ""
    best = 0
    best_hits = -1
    for i in range(0, len(words), 5):
        window = words[i:i + width]
        hits = sum(1 for w in window if set(normalize_tokens(w)) & terms)
        if hits > best_hits:
            best_hits, best = hits, i
    start = max(0, best - 3)
    end = min(len(words), start + width)
    out = " ".join(words[start:end])
    if start > 0:
        out = "..." + out
    if end < len(words):
        out += "..."
    for term in sorted(terms, key=len, reverse=True):
        out = re.sub(rf"\b({re.escape(term)}\w*)", r"<mark>\1</mark>", out, flags=re.I)
    return out


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-synonyms", action="store_true")
    args = ap.parse_args()
    idx = load_index()
    res = search(idx, args.query, args.limit, use_synonyms=not args.no_synonyms)
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(f"{res['total']} results; suggestion={res['suggestion']}")
        for r in res["results"]:
            print(f"{r['score']:8.2f}  {r['code']:10s} {r['title']} [{r['credits']} cr, {r['dept']}]")


if __name__ == "__main__":
    main()
