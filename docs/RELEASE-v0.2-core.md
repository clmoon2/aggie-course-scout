# v0.2-core release notes

Tag: `v0.2-core`
Date: 2026-11-22

This is the core search release. It is the first tagged version with the full crawl, index, query layer, static UI, and evaluation.

## What works

- 383 department pages crawled, 10,277 unique course records, 0 HTTP errors.
- Four-field BM25F index with title, department, description, and prerequisite postings.
- Python and JavaScript stemmers with a parity test.
- Query parser for phrases, `dept:`, `level:`, `credits:`, negation, synonyms, and spelling suggestions.
- Static UI with facets, snippets, detail drawer, why panel, and loading, empty, and error states.
- 25-query pooled evaluation with 513 judgments and four ablations.
- 25 passing Python, CLI, and Playwright tests.

## Results at this tag

BM25F scored P@10 0.828 and NDCG@10 0.964. Flat BM25 scored 0.520 and 0.663. BM25F loses known-item NDCG to flat BM25 by 0.003. Browser p50 is 14.4 ms and p95 is 21.8 ms.

## Data

`data/processed/courses.jsonl` SHA-256:
`176cd0fde5ea33c5ce3a169f3521510285eddc07a845cc72d59c3192c5d5ec8f`

Index gzip SHA-256 is in `web/data/index_stats.json`.

## Known limits

- Catalog snapshot only, no schedule or instructor data.
- College is hand-mapped, 61 records unplaced.
- Phrase search is a full scan.
- Evaluation is single-grader and pooled.
- `os` over-expands because "operating" and "operations" share a stem.

## Verify

```bash
.venv/bin/python -m pytest tests/ -q
cd src && python3 evaluate.py
```
