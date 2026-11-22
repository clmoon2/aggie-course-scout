# Status: Aggie Course Scout

## Phase
Complete. Built, tested, deployed, tagged, and handed off on 2026-11-22.

## Current state
- 383 catalog pages crawled, 10,275 records, 0 HTTP errors.
- BM25F index and browser query layer working.
- 25 tests passing, clean-checkout run passing.
- 25 queries, 514 judgments, three baselines, four ablations.
- BM25F NDCG@10 0.963, flat BM25 0.663. Known-item is a 0.003 loss.
- Live on GitHub Pages, report live, tag v0.2-core pushed.
- Proposal, data, UI, report, and slides PDFs built.
- HANDOFF.md has URLs, hashes, evidence, and Canvas texts.

## Open items
- None for the build. Carlos still has to post the five Canvas texts.
- Optional: update the UI PDF if the site design changes.

## Log
- 2026-11-22: crawl and manifest.
- 2026-11-22: tokenizer, index, query layer, UI, evaluation.
- 2026-11-22: tests, clean checkout, Pages deploy, live verification.
- 2026-11-22: checkpoints, report, slides, release, handoff.
