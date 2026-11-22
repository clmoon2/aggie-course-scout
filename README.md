# Aggie Course Scout

A search engine for the public Texas A&M course catalog. BM25F over four fields, a browser query layer, and a static site on GitHub Pages.

Live: https://clmoon2.github.io/aggie-course-scout/

Report: https://clmoon2.github.io/aggie-course-scout/report.html

## What it does

- Searches 10,277 undergraduate and graduate course records from the 2026-2027 catalog.
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

The crawler checks `robots.txt`, uses 4 workers with a 0.2 second delay, retries three times, and keeps gzipped raw pages in `data/raw/`. Index builds use a zero gzip mtime, so the same corpus produces the same artifact hash.

## Evaluation

```bash
cd src
python3 evaluate.py              # writes eval/judgments.csv and eval/results/
python3 latency.py               # writes eval/results/latency.json
```

The 25 queries are in `eval/queries.json`. The judgments are pooled from two baselines and seven BM25F conditions, then graded 0/1/2 from the actual records. Every system gets the same correction and synonym preprocessing unless an ablation removes it. NDCG uses a global ideal from the full judged pool. Current results:

| Condition | P@10 | NDCG@10 | AP@10 | MRR |
|---|---:|---:|---:|---:|
| TF-IDF, same terms | 0.700 | 0.671 | 0.669 | 0.794 |
| Flat BM25, same terms | 0.740 | 0.723 | 0.724 | 0.853 |
| BM25F | 0.776 | 0.793 | 0.767 | 0.841 |
| BM25F, no correction | 0.652 | 0.652 | 0.638 | 0.717 |
| BM25F, no synonyms | 0.720 | 0.734 | 0.708 | 0.798 |
| BM25F, no synonyms or correction | 0.596 | 0.593 | 0.580 | 0.673 |
| BM25F, title only | 0.716 | 0.806 | 0.716 | 0.873 |

The field-weight result is weak: title-only beats the full model on NDCG. The 0.070 gap is the field-weighting comparison with terms held constant; the 0.141 correction effect is a separate within-system comparison. The report covers that and the other failures.

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

College is not printed on department pages, so it is mapped by hand from department prefixes. 36 records in professional or unplaced prefixes use "Other/Professional." Descriptions are the published catalog text, stripped of HTML. Prerequisites are regex-extracted and can truncate on unusual punctuation. See `DATA-LICENSE.md` for source and reuse notes.

Output hash: `e16567db30e1aef9770dd3399792ece696c4e321fbda333cce8a508051196206`.

## License

Code is MIT. Catalog text belongs to Texas A&M University and is used with attribution for a class project. See `LICENSE` and `DATA-LICENSE.md`.
