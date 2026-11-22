#!/usr/bin/env python3
"""Build the browser index from data/processed/courses.jsonl.

Postings are nested by term and field so the browser never needs a server:
{"terms": {"algorithm": {"title": [[doc, tf]], ...}}, "docs": [...]}
Field names in postings: t=title, d=department, x=description, p=prerequisites.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean

from text import normalize_tokens

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "processed" / "courses.jsonl"
OUT_DIR = ROOT / "web" / "data"
OUT = OUT_DIR / "index.json.gz"
FIELDS = {"title": "t", "department": "d", "description": "x", "prerequisites": "p"}
WEIGHTS = {"t": 3.0, "d": 2.0, "x": 1.0, "p": 0.5}
CROSS_RE = re.compile(r"^/\s*[A-Z]{2,5}\s*\d{3,4}[A-Z]?\s*")


def clean_title(t: str) -> str:
    t = CROSS_RE.sub("", t)
    return re.sub(r"\s+", " ", t).strip(" /")


def main() -> None:
    docs = []
    postings: dict[str, dict[str, list[list[int]]]] = defaultdict(lambda: defaultdict(list))
    doclen = {f: [] for f in FIELDS.values()}
    for line in SRC.open(encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        did = len(docs)
        title = clean_title(r["title"])
        fields = {
            "title": f'{r["code"]} {title}',
            "department": f'{r["department"]} {r["dept_code"]} {r["college"]}',
            "description": r["description"],
            "prerequisites": r["prerequisites"] + " " + r.get("corequisites", ""),
        }
        for fname, short in FIELDS.items():
            toks = normalize_tokens(fields[fname])
            doclen[short].append(len(toks))
            counts: dict[str, int] = defaultdict(int)
            for tok in toks:
                counts[tok] += 1
            for tok, tf in counts.items():
                postings[tok][short].append([did, tf])
        docs.append([
            r["id"], r["code"], title, r["dept_code"], r["department"],
            r["college"], r["level"], r["credits"] or "", r["url"],
        ])
    n = len(docs)
    avglen = {f: (mean(v) if v else 1.0) for f, v in doclen.items()}
    # Full description and prerequisites live in a parallel array so the result
    # cards stay small but the detail panel has the source text.
    text = []
    src = [json.loads(l) for l in SRC.open(encoding="utf-8") if l.strip()]
    for i, r in enumerate(src):
        text.append([r["description"], r["prerequisites"], clean_title(r["title"])])
    index = {
        "built_at": "2026-11-22",
        "n": n,
        "k1": 1.2,
        "b": 0.75,
        "weights": WEIGHTS,
        "avglen": avglen,
        "doclen": doclen,
        "docs": docs,
        "text": text,
        "terms": {t: dict(f) for t, f in sorted(postings.items())},
    }
    blob = json.dumps(index, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wb", compresslevel=9) as f:
        f.write(blob)
    plain_hash = hashlib.sha256(blob).hexdigest()
    disk_hash = hashlib.sha256(OUT.read_bytes()).hexdigest()
    stats = {
        "docs": n,
        "terms": len(postings),
        "postings": sum(len(p) for t in postings.values() for p in t.values()),
        "plain_bytes": len(blob),
        "gzip_bytes": OUT.stat().st_size,
        "plain_sha256": plain_hash,
        "gzip_sha256": disk_hash,
        "avglen": avglen,
        "fields": FIELDS,
        "weights": WEIGHTS,
    }
    (OUT_DIR / "index_stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
