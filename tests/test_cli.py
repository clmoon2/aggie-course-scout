import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cli_json_search():
    out = subprocess.check_output(
        [sys.executable, "src/query.py", "CSCE 310", "--limit", "3", "--json"],
        cwd=ROOT, text=True, timeout=60,
    )
    data = json.loads(out)
    assert data["results"]
    assert data["results"][0]["code"] == "CSCE 310"
    assert data["total"] >= 1


def test_cli_filter_search():
    out = subprocess.check_output(
        [sys.executable, "src/query.py", "security dept:csce credits:>=3", "--limit", "5", "--json"],
        cwd=ROOT, text=True, timeout=60,
    )
    data = json.loads(out)
    assert data["results"]
    assert all(r["dept"] == "CSCE" for r in data["results"])
    assert all(float(r["credits"]) >= 3 for r in data["results"])


def test_cli_empty_query_with_filter():
    out = subprocess.check_output(
        [sys.executable, "src/query.py", "dept:csce level:graduate", "--limit", "3", "--json"],
        cwd=ROOT, text=True, timeout=60,
    )
    data = json.loads(out)
    assert data["total"] > 0
    assert all(r["dept"] == "CSCE" for r in data["results"])
    assert all(r["level"] == "graduate" for r in data["results"])
