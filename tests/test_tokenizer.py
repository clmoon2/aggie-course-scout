import json
import subprocess
from pathlib import Path

from text import STOPWORDS, normalize_tokens, stem, tokenize

ROOT = Path(__file__).resolve().parents[1]


def test_tokenizer_lowercases_and_splits():
    assert tokenize("CSCE 121: Program-Design, 3 credits!") == ["csce", "121", "program", "design", "3", "credits"]


def test_stopwords_removed():
    assert normalize_tokens("the course of operating systems") == ["oper", "system"]
    assert "course" in STOPWORDS


def test_stemmer_known_pairs():
    assert stem("algorithms") == "algorithm"
    assert stem("databases") == "databas"
    assert stem("operating") == "oper"
    assert stem("learning") == "learn"
    assert stem("calculus") == "calculu"
    assert stem("security") == "secur"
    assert stem("graphics") == "graphic"


def test_stemmer_does_not_maul_short_words():
    assert stem("os") == "os"
    assert stem("ai") == "ai"
    assert stem("db") == "db"
    assert stem("data") == "data"


def test_python_and_js_stemmers_match():
    words = ["algorithms", "databases", "operating", "learning", "calculus", "security",
             "graphics", "programming", "networks", "statistics", "classes", "studies",
             "running", "happiness", "relational", "machine", "intelligence", "courses",
             "prerequisites", "visualization", "engineering", "analysis", "systems"]
    js = """
    const fs = require('fs'); const vm = require('vm');
    const ctx = {window:{}}; vm.createContext(ctx);
    vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx);
    const words = JSON.parse(process.argv[2]);
    console.log(JSON.stringify(words.map(w => ctx.window.ACSStem.stem(w))));
    """
    out = subprocess.check_output(
        ["node", "-e", js, str(ROOT / "web" / "js" / "stemmer.js"), json.dumps(words)],
        text=True,
    )
    assert json.loads(out) == [stem(w) for w in words]
