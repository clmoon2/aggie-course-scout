#!/usr/bin/env python3
"""Pool systems, create graded judgments, and report pooled metrics.

Every condition sees the same query preprocessing unless an ablation turns a
step off, and every baseline gets the same correction and synonym terms as
BM25F. NDCG@10 uses a global ideal built from all judged documents for that
query, not from each system's own top 10.
"""
from __future__ import annotations

import csv
import json
import math
import random
import re
import sys
from pathlib import Path

from baselines import FlatBM25, Tfidf
from query import expansion_terms, load_index, search

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval"
QUERIES = json.loads((EVAL / "queries.json").read_text())
OUT = EVAL / "results"
OUT.mkdir(exist_ok=True)


def has_term(text: str, term: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])", text.lower()) is not None


def grade(q: dict, doc: list, desc: str = "") -> int:
    code, title = doc[1].lower(), doc[2].lower()
    if q["must"] and q["must"] in code:
        return 2
    if any(has_term(title, t) for t in q["title_terms"]):
        return 2
    if any(has_term(title, t) for t in q["rel_terms"]):
        return 1
    if any(has_term(desc, t) for t in q["rel_terms"]):
        return 1
    return 0


def ap_at_10(grades: list[int], ideal_grades: list[int]) -> float:
    hits = 0
    total = 0.0
    relevant = sum(1 for g in ideal_grades if g >= 1)
    for i, g in enumerate(grades[:10], 1):
        if g >= 1:
            hits += 1
            total += hits / i
    return total / max(1, min(10, relevant))


def ndcg_at_10(grades: list[int], ideal_grades: list[int]) -> float:
    dcg = sum((2 ** g - 1) / math.log2(i + 1) for i, g in enumerate(grades[:10], 1))
    ideal = sorted(ideal_grades, reverse=True)[:10]
    idcg = sum((2 ** g - 1) / math.log2(i + 1) for i, g in enumerate(ideal, 1))
    return dcg / idcg if idcg else 0.0


def reciprocal_rank(grades: list[int]) -> float:
    for i, g in enumerate(grades[:10], 1):
        if g >= 1:
            return 1 / i
    return 0.0


def metrics(ranked_grades: list[int], ideal_grades: list[int]) -> dict:
    return {
        "P@10": sum(1 for g in ranked_grades[:10] if g >= 1) / 10,
        "NDCG@10": ndcg_at_10(ranked_grades, ideal_grades),
        "AP@10": ap_at_10(ranked_grades, ideal_grades),
        "MRR": reciprocal_rank(ranked_grades),
    }


def main() -> int:
    index = load_index()
    baselines = {"tfidf": Tfidf(index), "flat_bm25": FlatBM25(index)}
    bm_conditions = {
        "bm25f": {},
        "ablate_no_correction": {"use_correction": False},
        "ablate_no_synonyms": {"use_synonyms": False},
        "ablate_no_synonyms_no_correction": {"use_synonyms": False, "use_correction": False},
        "ablate_title_only": {"weights": {"t": 3.0, "d": 0.0, "x": 0.0, "p": 0.0}},
        "ablate_no_dept": {"weights": {"t": 3.0, "d": 0.0, "x": 1.0, "p": 0.5}},
        "ablate_equal_weights": {"weights": {"t": 1.0, "d": 1.0, "x": 1.0, "p": 1.0}},
        "equal_expansion_no_phrase": {"correction_weight": 1.0, "synonym_weight": 1.0, "synonym_phrase_bonus": False},
    }
    names = ["tfidf", "flat_bm25", *bm_conditions]
    pool: dict[str, list[int]] = {}
    system_ids: dict[str, dict[str, list[str]]] = {n: {} for n in names}

    for q in QUERIES:
        qid = q["id"]
        seen: list[str] = []
        expanded = expansion_terms(index, q["query"], True, True)
        for name, obj in baselines.items():
            ids = [index["docs"][did][0] for did, _ in obj.search_terms(expanded, 10)]
            system_ids[name][qid] = ids
            seen.extend(i for i in ids if i not in seen)
        for name, kwargs in bm_conditions.items():
            res = search(index, q["query"], 10, explain=False, **kwargs)
            ids = [r["id"] for r in res["results"]]
            system_ids[name][qid] = ids
            seen.extend(i for i in ids if i not in seen)
        pool[qid] = seen

    by_id = {d[0]: d for d in index["docs"]}
    idx_by_id = {d[0]: i for i, d in enumerate(index["docs"])}

    overrides = {}
    op = EVAL / "overrides.csv"
    if op.exists():
        for row in csv.DictReader(op.open()):
            overrides[(row["qid"], row["doc_id"])] = int(row["grade"])

    rows = []
    qmap = {q["id"]: q for q in QUERIES}
    for qid, ids in pool.items():
        for doc_id in ids:
            doc = by_id[doc_id]
            g = overrides.get((qid, doc_id))
            if g is None:
                g = grade(qmap[qid], doc, index["text"][idx_by_id[doc_id]][0])
            sources = [n for n in names if doc_id in system_ids[n].get(qid, [])]
            rows.append({"qid": qid, "doc_id": doc_id, "code": doc[1], "title": doc[2],
                         "grade": g, "pooled_from": "|".join(sources)})
    with (EVAL / "judgments.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["qid", "doc_id", "code", "title", "grade", "pooled_from"])
        w.writeheader()
        w.writerows(rows)

    grades = {(r["qid"], r["doc_id"]): r["grade"] for r in rows}
    ideal = {qid: [r["grade"] for r in rows if r["qid"] == qid] for qid in pool}

    def run_metrics(system: str) -> dict:
        per_q = []
        for q in QUERIES:
            ids = system_ids[system][q["id"]]
            gs = [grades.get((q["id"], i), 0) for i in ids]
            per_q.append(metrics(gs, ideal[q["id"]]))
        return {k: sum(m[k] for m in per_q) / len(per_q) for k in per_q[0]}

    results = {name: run_metrics(name) for name in names}

    def dedupe(ids: list[str]) -> list[str]:
        seen, out = set(), []
        for doc_id in ids:
            code = by_id[doc_id][1]
            if code in seen:
                continue
            seen.add(code)
            out.append(doc_id)
        return out

    ideal_dedup = {}
    for qid, gs in ideal.items():
        best = {}
        for doc_id in pool[qid]:
            code = by_id[doc_id][1]
            best[code] = max(best.get(code, 0), grades[(qid, doc_id)])
        ideal_dedup[qid] = list(best.values())
    for name in ("flat_bm25", "bm25f"):
        per_q = []
        for q in QUERIES:
            ids = dedupe(system_ids[name][q["id"]])
            gs = [grades.get((q["id"], i), 0) for i in ids]
            per_q.append(metrics(gs, ideal_dedup[q["id"]]))
        results[name + "_deduped"] = {k: sum(m[k] for m in per_q) / len(per_q) for k in per_q[0]}

    def paired_significance(name: str):
      sig = {}
      for metric in ("P@10", "NDCG@10", "AP@10", "MRR"):
        diffs = []
        for q in QUERIES:
            a = metrics([grades.get((q["id"], i), 0) for i in system_ids[name][q["id"]]], ideal[q["id"]])[metric]
            b = metrics([grades.get((q["id"], i), 0) for i in system_ids["flat_bm25"][q["id"]]], ideal[q["id"]])[metric]
            diffs.append(a - b)
        wins = sum(d > 1e-12 for d in diffs)
        losses = sum(d < -1e-12 for d in diffs)
        ties = len(diffs) - wins - losses
        rng = random.Random(470)
        boot = []
        for _ in range(5000):
            sample = [diffs[rng.randrange(len(diffs))] for _ in diffs]
            boot.append(sum(sample) / len(sample))
        boot.sort()
        n = wins + losses
        if n:
            tail = sum(math.comb(n, k) for k in range(0, min(wins, losses) + 1)) / (2 ** n)
            p = min(1.0, 2 * tail)
        else:
            p = 1.0
        sig[metric] = {
            "mean_diff": sum(diffs) / len(diffs),
            "wins": wins, "losses": losses, "ties": ties,
            "ci95": [boot[int(0.025 * len(boot))], boot[int(0.975 * len(boot))]],
            "sign_test_p": p,
        }
      return sig
    (OUT / "significance.json").write_text(json.dumps({
        "shipped": paired_significance("bm25f"),
        "equalized": paired_significance("equal_expansion_no_phrase"),
    }, indent=2) + "\n")

    (OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    with (OUT / "results.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["condition", "P@10", "NDCG@10", "AP@10", "MRR"])
        for name, m in results.items():
            w.writerow([name, f"{m['P@10']:.4f}", f"{m['NDCG@10']:.4f}", f"{m['AP@10']:.4f}", f"{m['MRR']:.4f}"])
    md = ["| Condition | P@10 | NDCG@10 | AP@10 | MRR |", "|---|---:|---:|---:|---:|"]
    for name, m in results.items():
        md.append(f"| {name} | {m['P@10']:.3f} | {m['NDCG@10']:.3f} | {m['AP@10']:.3f} | {m['MRR']:.3f} |")
    (OUT / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))

    per_cat = {}
    for name in names:
        cats: dict[str, list[float]] = {}
        for q in QUERIES:
            gs = [grades.get((q["id"], i), 0) for i in system_ids[name][q["id"]]]
            cats.setdefault(q["category"], []).append(metrics(gs, ideal[q["id"]])["NDCG@10"])
        per_cat[name] = {c: sum(v) / len(v) for c, v in cats.items()}
    (OUT / "by_category.json").write_text(json.dumps(per_cat, indent=2) + "\n")
    plain_qids = [q["id"] for q in QUERIES if q["category"] not in ("typo", "synonym")]
    plain = {}
    for name in names:
        vals = []
        for qid in plain_qids:
            gs = [grades.get((qid, i), 0) for i in system_ids[name][qid]]
            vals.append(metrics(gs, ideal[qid])["NDCG@10"])
        plain[name] = sum(vals) / len(vals)
    (OUT / "plain_queries.json").write_text(json.dumps(plain, indent=2) + "\n")
    print("wrote", EVAL / "judgments.csv", "and", OUT / "results.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
