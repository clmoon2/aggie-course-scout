# v0.2-core release notes

Tag: `v0.2-core`
Date: 2026-11-22

This is the core search release. It is the first tagged version with the full crawl, index, query layer, static UI, and evaluation.

## What works

- 383 department pages crawled, 10,082 unique course records, 0 HTTP errors.
- Four-field BM25F index with title, department, description, and prerequisite postings.
- Python and JavaScript stemmers with a parity test.
- Query parser for phrases, `dept:`, `level:`, `credits:`, negation, synonyms, and spelling suggestions.
- Static UI with facets, snippets, detail drawer, why panel, and loading, empty, and error states.
- 25-query pooled evaluation with 514 judgments and four ablations.
- 24 passing Python, CLI, and Playwright tests.

## Results at this tag

BM25F scored P@10 0.824 and NDCG@10 0.967. Flat BM25 scored 0.532 and 0.665. BM25F loses known-item NDCG to flat BM25 by 0.005. Browser p50 is 10.9 ms and p95 is 22.8 ms.

## Data

`data/processed/courses.jsonl` SHA-256:
`a2cfbcece529332fce6cb4117953be9bbd250385843fec6a0650d0291c4f8ca2`

Index gzip SHA-256 is in `web/data/index_stats.json`.

## Known limits

- Catalog snapshot only, no schedule or instructor data.
- College is hand-mapped, 536 records unplaced.
- Phrase search is a full scan.
- Evaluation is single-grader and pooled.
- `os` over-expands because "operating" and "operations" share a stem.

## Verify

```bash
.venv/bin/python -m pytest tests/ -q
cd src && python3 evaluate.py
```
