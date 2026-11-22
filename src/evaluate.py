#!/usr/bin/env python3
"""Pool three systems, create graded judgments, and report metrics.

Judgments start from title and description rules against the actual pooled
documents (grade 2 = intent phrase in the title or exact course code asked for,
1 = intent phrase somewhere in the description, 0 otherwise). eval/overrides.csv
holds hand corrections. This is a pooled evaluation, so every metric is computed
only over documents that at least one system put in its top 10.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

from baselines import FlatBM25, Tfidf
from query import load_index, search

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval"
QUERIES = json.loads((EVAL / "queries.json").read_text())
OUT = EVAL / "results"
OUT.mkdir(exist_ok=True)


def grade(q: dict, doc: list, desc: str = "") -> int:
    code, title = doc[1].lower(), doc[2].lower()
    if q["must"] and q["must"] in code:
        return 2
    if any(t in title for t in q["title_terms"]):
        return 2
    if any(t in title for t in q["rel_terms"]):
        return 1
    if any(t in desc.lower() for t in q["rel_terms"]):
        return 1
    return 0


def ap_at_k(grades: list[int]) -> float:
    hits = 0
    total = 0.0
    for i, g in enumerate(grades, 1):
        if g >= 1:
            hits += 1
            total += hits / i
    return total / max(1, min(len(grades), 10))


def ndcg_at_k(grades: list[int], k: int = 10) -> float:
    dcg = sum((2 ** g - 1) / math.log2(i + 1) for i, g in enumerate(grades[:k], 1))
    ideal = sorted(grades, reverse=True)[:k]
    idcg = sum((2 ** g - 1) / math.log2(i + 1) for i, g in enumerate(ideal, 1))
    return dcg / idcg if idcg else 0.0


def mrr(grades: list[int]) -> float:
    for i, g in enumerate(grades, 1):
        if g >= 1:
            return 1 / i
    return 0.0


def metrics(ranked_grades: list[int]) -> dict:
    return {
        "P@10": sum(1 for g in ranked_grades[:10] if g >= 1) / 10,
        "NDCG@10": ndcg_at_k(ranked_grades),
        "MAP": ap_at_k(ranked_grades),
        "MRR": mrr(ranked_grades),
    }


def main() -> int:
    index = load_index()
    systems = {
        "tfidf": Tfidf(index),
        "flat_bm25": FlatBM25(index),
    }
    ablations = {
        "ablate_title_only": {"weights": {"t": 3.0, "d": 0.0, "x": 0.0, "p": 0.0}},
        "ablate_no_dept": {"weights": {"t": 3.0, "d": 0.0, "x": 1.0, "p": 0.5}},
        "ablate_equal_weights": {"weights": {"t": 1.0, "d": 1.0, "x": 1.0, "p": 1.0}},
        "ablate_no_synonyms": {"use_synonyms": False},
    }
    pool: dict[str, list[int]] = {}
    system_ids: dict[str, dict[str, list[str]]] = {n: {} for n in ["tfidf", "flat_bm25", "bm25f", *ablations]}
    for q in QUERIES:
        qid = q["id"]
        seen = []
        for name, sys_obj in systems.items():
            hits = sys_obj.search(q["query"], 10)
            ids = [index["docs"][did][0] for did, _ in hits]
            system_ids[name][qid] = ids
            for i in ids:
                if i not in seen:
                    seen.append(i)
        hits = search(index, q["query"], 10, explain=False)["results"]
        system_ids["bm25f"][qid] = [r["id"] for r in hits]
        for r in hits:
            if r["id"] not in seen:
                seen.append(r["id"])
        for name, kwargs in ablations.items():
            res = search(index, q["query"], 10, explain=False, **kwargs)
            ids = [r["id"] for r in res["results"]]
            system_ids[name][qid] = ids
            for i in ids:
                if i not in seen:
                    seen.append(i)
        pool[qid] = seen

    by_id = {d[0]: d for d in index["docs"]}
    idx_by_id = {d[0]: i for i, d in enumerate(index["docs"])}

    # Overrides are keyed by query and doc id.
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
            pool_systems = [n for n in system_ids if doc_id in system_ids[n].get(qid, [])]
            rows.append({"qid": qid, "doc_id": doc_id, "code": doc[1], "title": doc[2],
                         "grade": g, "pooled_from": "|".join(pool_systems)})
    with (EVAL / "judgments.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["qid", "doc_id", "code", "title", "grade", "pooled_from"])
        w.writeheader()
        w.writerows(rows)

    grades = {(r["qid"], r["doc_id"]): r["grade"] for r in rows}

    def run_metrics(system: str, weight_override=None, use_synonyms=True,
                    synonym_map: dict | None = None, cached: bool = True) -> dict:
        per_q = []
        for q in QUERIES:
            ids = system_ids.get(system, {}).get(q["id"]) if cached else None
            if ids is None:
                res = search(index, q["query"], 10, weights=weight_override,
                             use_synonyms=use_synonyms, explain=False)
                ids = [r["id"] for r in res["results"]]
            # pooled rank: judged docs in this system's order, docs outside pool
            # were judged 0 by construction.
            gs = [grades.get((q["id"], i), 0) for i in ids]
            per_q.append(metrics(gs))
        return {k: sum(m[k] for m in per_q) / len(per_q) for k in per_q[0]}

    results = {}
    for name in ["tfidf", "flat_bm25", "bm25f", *ablations]:
        results[name] = run_metrics(name)

    (OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    with (OUT / "results.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["condition", "P@10", "NDCG@10", "MAP", "MRR"])
        for name, m in results.items():
            w.writerow([name, f"{m['P@10']:.4f}", f"{m['NDCG@10']:.4f}", f"{m['MAP']:.4f}", f"{m['MRR']:.4f}"])
    md = ["| Condition | P@10 | NDCG@10 | MAP | MRR |", "|---|---:|---:|---:|---:|"]
    for name, m in results.items():
        md.append(f"| {name} | {m['P@10']:.3f} | {m['NDCG@10']:.3f} | {m['MAP']:.3f} | {m['MRR']:.3f} |")
    (OUT / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    per_cat = {}
    for name in ["tfidf", "flat_bm25", "bm25f"]:
        vals = []
        for q in QUERIES:
            gs = [grades.get((q["id"], i), 0) for i in system_ids[name][q["id"]]]
            vals.append((q["category"], metrics(gs)["NDCG@10"]))
        cats = {}
        for c, v in vals:
            cats.setdefault(c, []).append(v)
        per_cat[name] = {c: sum(v) / len(v) for c, v in cats.items()}
    (OUT / "by_category.json").write_text(json.dumps(per_cat, indent=2) + "\n")
    print("wrote", EVAL / "judgments.csv", "and", OUT / "results.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
