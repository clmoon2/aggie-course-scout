# Aggie Course Scout

A search engine for the public Texas A&M course catalog. BM25F over four fields, a browser query layer, and a static site on GitHub Pages.

Live: https://clmoon2.github.io/aggie-course-scout/

Report: https://clmoon2.github.io/aggie-course-scout/report.html

## What it does

- Searches 10,275 undergraduate and graduate course records from the 2026-2027 catalog.
- Supports quoted phrases, `dept:`, `level:`, `credits:` filters, and `-` negation.
- Expands common acronyms (ml, ai, db, os, security, stats) and suggests spelling fixes.
- Shows facets, highlighted snippets, and a term-by-term why-this-ranked panel.
- Runs with no backend. The index is a 2.2 MB gzipped asset.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python3 -m http.server 8000 --directory web
# open http://localhost:8000/
```

Search from the command line:

```bash
cd src
python3 query.py "computer security dept:csce" --limit 10
```

## Rebuild the data

```bash
python3 src/crawl_catalog.py     # 383 pages, writes data/processed/courses.jsonl
python3 src/build_index.py       # writes web/data/index.json.gz
```

The crawler checks `robots.txt`, uses 4 workers with a 0.2 second delay, retries three times, and keeps gzipped raw pages in `data/raw/`.

## Evaluation

```bash
cd src
python3 evaluate.py              # writes eval/judgments.csv and eval/results/
python3 latency.py               # writes eval/results/latency.json
```

The 25 queries are in `eval/queries.json`. The judgments are pooled from TF-IDF, flat BM25, BM25F, and four ablations, then graded 0/1/2 from the actual records. Current results:

| Condition | P@10 | NDCG@10 | MAP | MRR |
|---|---:|---:|---:|---:|
| TF-IDF | 0.516 | 0.665 | 0.463 | 0.646 |
| Flat BM25 | 0.520 | 0.663 | 0.482 | 0.656 |
| BM25F | 0.828 | 0.963 | 0.789 | 0.973 |
| BM25F, no synonyms | 0.772 | 0.920 | 0.728 | 0.933 |

Known-item NDCG is a tie with flat BM25 (0.922 vs 0.924). The report covers that and the other failures.

## Tests

```bash
.venv/bin/python -m pytest tests/ -q
```

Tokenizers, stemmer parity between Python and JavaScript, BM25 math, parser, filters, index integrity, CLI, and Playwright smoke tests.

## Layout

```
src/            crawler, tokenizer, index builder, query layer, baselines, evaluation
web/            static site, browser query engine, report page
eval/           queries, pooled judgments, metrics
data/raw/       gzipped source pages
data/processed/ parsed JSONL and crawl manifest
checkpoints/    proposal, data, and UI PDFs
slides/         10-slide deck with speaker notes
docs/           release notes
```

## Data notes

College is not printed on department pages, so it is mapped by hand from department prefixes. 211 records in professional or unplaced prefixes use "Other/Professional." Descriptions are the published catalog text, stripped of HTML. Prerequisites are regex-extracted and can truncate on unusual punctuation.

Output hash: `8eed36cec66a5f6e94893e502f6828c7b3cc67c4206d07b3d0e4f53adf54e38e`.

## License

Code is MIT. Catalog text belongs to Texas A&M University and is used with attribution for a class project. See `LICENSE` and `DATA-LICENSE.md`.
