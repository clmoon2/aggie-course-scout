import json
import subprocess
from pathlib import Path

from query import load_index, search

ROOT = Path(__file__).resolve().parents[1]
QUERIES = [q["query"] for q in json.loads((ROOT / "eval" / "queries.json").read_text())]


def test_python_and_js_search_parity():
    """The deployed engine must return the same ids as the evaluated engine."""
    script = r"""
    const fs = require('fs'), zlib = require('zlib'), vm = require('vm');
    const ctx = {window: {}}; vm.createContext(ctx);
    vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx);
    vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), ctx);
    const idx = JSON.parse(zlib.gunzipSync(fs.readFileSync(process.argv[3])));
    const vocab = new Set(Object.keys(idx.terms));
    for (const fields of idx.text) for (const f of fields) {
      for (const t of ctx.window.ACSStem.tokenize(f)) if (t.length > 2) vocab.add(t);
    }
    idx._vocab = [...vocab].sort();
    const queries = JSON.parse(process.argv[4]);
    console.log(JSON.stringify(queries.map(q =>
      ctx.window.ACSSearch.search(idx, q, 10).results.map(r => r.id))));
    """
    out = subprocess.check_output(
        ["node", "-e", script, str(ROOT / "web/js/stemmer.js"),
         str(ROOT / "web/js/search.js"), str(ROOT / "web/data/index.json.gz"),
         json.dumps(QUERIES)],
        text=True, timeout=120,
    )
    js = json.loads(out)
    idx = load_index()
    py = [[r["id"] for r in search(idx, q, 10, explain=False)["results"]] for q in QUERIES]
    for query, a, b in zip(QUERIES, py, js):
        assert a[0] == b[0], query
        assert len(set(a) & set(b)) >= 9, query
