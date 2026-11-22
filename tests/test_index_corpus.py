import csv
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

from query import load_index

ROOT = Path(__file__).resolve().parents[1]
COURSES = ROOT / "data" / "processed" / "courses.jsonl"


def test_index_rows_match_corpus():
    idx = load_index()
    rows = [json.loads(line) for line in COURSES.open()]
    assert len(rows) == idx["n"]
    for i, row in enumerate(rows):
        doc = idx["docs"][i]
        assert doc[0] == row["id"]
        assert doc[1] == row["code"]
        assert doc[3] == row["dept_code"]
        assert doc[5] == row["college"]
        assert doc[7] == (row["credits"] or "")
        assert idx["text"][i][0] == row["description"]
        assert idx["text"][i][1] == row["prerequisites"]


def test_courses_hash_matches_published_value():
    expected = "e16567db30e1aef9770dd3399792ece696c4e321fbda333cce8a508051196206"
    assert hashlib.sha256(COURSES.read_bytes()).hexdigest() == expected


def test_index_build_is_byte_deterministic():
    def build():
        subprocess.run(["python3", "src/build_index.py"], cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL)
        return hashlib.sha256((ROOT / "web/data/index.json.gz").read_bytes()).hexdigest()
    assert build() == build()
