import gzip
import hashlib
import json
from pathlib import Path

from query import load_index

ROOT = Path(__file__).resolve().parents[1]
STATS = ROOT / "web" / "data" / "index_stats.json"


def test_index_file_hash_matches_stats():
    stats = json.loads(STATS.read_text())
    raw = (ROOT / "web" / "data" / "index.json.gz").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == stats["gzip_sha256"]


def test_index_counts_and_ids():
    idx = load_index()
    assert idx["n"] == len(idx["docs"]) == len(idx["text"])
    ids = [d[0] for d in idx["docs"]]
    assert len(ids) == len(set(ids))
    assert all(":" in i for i in ids)


def test_every_posting_points_at_a_real_doc():
    idx = load_index()
    n = idx["n"]
    checked = 0
    for term, fields in idx["terms"].items():
        for short, entries in fields.items():
            for did, tf in entries:
                assert 0 <= did < n
                assert tf > 0
                assert idx["doclen"][short][did] >= tf
                checked += 1
    assert checked > 300000


def test_codes_are_indexed_for_lookup():
    idx = load_index()
    did = idx["docs"].index(next(d for d in idx["docs"] if d[1] == "CSCE 121"))
    assert any(did == x[0] for x in idx["terms"]["121"]["t"])
