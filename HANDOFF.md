# Handoff: Aggie Course Scout

Status: complete, tested, deployed, and tagged. Built 2026-11-22.

## URLs

- Live site: https://clmoon2.github.io/aggie-course-scout/
- Report page: https://clmoon2.github.io/aggie-course-scout/report.html
- Repository: https://github.com/clmoon2/aggie-course-scout
- Core release: https://github.com/clmoon2/aggie-course-scout/releases/tag/v0.2-core
- Pages workflow run: https://github.com/clmoon2/aggie-course-scout/actions/runs/45002785126

## Artifacts

| Artifact | Path |
|---|---|
| Proposal checkpoint, 2 pages | checkpoints/CSCE470_Project_Proposal_Carlos_Luna-Pena.pdf |
| Data checkpoint, 1 page | checkpoints/CSCE470_Project_Data_Carlos_Luna-Pena.pdf |
| UI checkpoint, 2 pages | checkpoints/CSCE470_Project_UI_Carlos_Luna-Pena.pdf |
| Core release notes | docs/RELEASE-v0.2-core.md |
| Report PDF, 7 pages | docs/report.pdf |
| Slides with notes, 10 pages | slides/CSCE470_Project_Slides_Carlos_Luna-Pena.pdf |
| Screenshots | web/assets/screenshots/ |
| Tests | tests/ |
| Evaluation judgments | eval/judgments.csv |
| Metrics | eval/results/results.json |
| Latency | eval/results/latency.json |

## Hashes

```
e16567db30e1aef9770dd3399792ece696c4e321fbda333cce8a508051196206  data/processed/courses.jsonl
c4c2d79b99485b3a855e2a31e622751ecb8864b126b8e40932b2f36997a180fa  web/data/index.json.gz
b526f1277dafa2bf6443543c9db08abad8525ed59210a35c2180da3326a7c7d8  docs/report.pdf
34159461b4003418ec808ae7231f2e8f4bc07d5c4c65944893c9fc8cc5e2a145  checkpoints/CSCE470_Project_Proposal_Carlos_Luna-Pena.pdf
886cbd355f2d50d07ad386c341e6f38af4ff3d48d4ed2fb807e1fa3dd933eaa5  checkpoints/CSCE470_Project_Data_Carlos_Luna-Pena.pdf
08bbe14437c38707c675618f34cb811389ab64ffaf1082d9b8feb204c5039b31  checkpoints/CSCE470_Project_UI_Carlos_Luna-Pena.pdf
6170a9c60b649f6e9454507607293bd256f12d5344b8e25f25e60dde53f40bd4  slides/CSCE470_Project_Slides_Carlos_Luna-Pena.pdf
```

## Verification evidence

- Full test run: `38 passed in 23.60s` from `pytest tests/ -q`.
- Clean checkout: cloned the public repo to `/tmp/opencode/clean-check`, made a fresh venv, installed `requirements.txt`, and ran `pytest tests/ -q`. Result: `24 passed in 7.42s`.
- Live page, logged out Chrome context: HTTP 200, title `Aggie Course Scout | TAMU catalog search`, 20 result cards for `computer security`, first result `CSCE 465 · Computer and Network Security`.
- Live report page: HTTP 200.
- Pages workflow: run 45002785126, conclusion success, 39 seconds.
- Release: tag `v0.2-core` pushed and release published.
- Search CLI: `python3 src/query.py "CSCE 310" --limit 3 --json` returns CSCE 310 first.
- Data: 383 pages, 0 HTTP errors, 10,277 records. Manifest has one row per request.
- Latency: 75 samples, p50 14.4 ms, p95 22.2 ms, cold max 381 ms.

The last code commit is `435198d`. Later commits change documentation, report wording, and PDFs only.

## Before posting

1. Open the live site and the report logged out.
2. Confirm the release tag is visible.
3. Post the Canvas texts below in the matching checkpoint assignment. The checkpoint boxes are late, so each text says that.
4. Do not post the evaluation as "BM25F wins everywhere." Known-item NDCG is a 0.003 loss to flat BM25 and the report says so.

## Canvas: proposal checkpoint

Late proposal for my CSCE 470 project, Aggie Course Scout. It is a search engine over the public TAMU course catalog, built solo. The problem is that the catalog has descriptions but its search is site search. A query like "security" can return policy pages before CSCE 465, and a student who remembers a topic gets a department list. The tool ranks course records with BM25F, supports phrase and field filters, and shows which term and field produced a score. It is static on GitHub Pages, public data only, no backend. The proposal covers who benefits, existing tools, the build plan, resources, and a 25-query evaluation against TF-IDF and flat BM25. Proposal PDF is attached. Repo: https://github.com/clmoon2/aggie-course-scout.

## Canvas: data checkpoint

Late data checkpoint. I crawled the 2026-2027 TAMU undergraduate and graduate catalog course-description indexes: 383 department pages, 4 workers, 0.2 second delay, three retries, robots.txt respected. All 383 returned 200. I parsed 10,277 unique course records with code, title, credits, description, prerequisites, department, college, and level. HTML is stripped and records are deduplicated by level plus code. The output JSONL has SHA-256 e16567db30e1aef9770dd3399792ece696c4e321fbda333cce8a508051196206 and a manifest with every page hash and status. One-page data PDF attached. Limits: snapshot only, no schedule data, college is hand-mapped, and the count is 10,277, above my proposed range. Repo: https://github.com/clmoon2/aggie-course-scout.

## Canvas: core release

Late core release checkpoint, tagged v0.2-core. The crawl, four-field index, browser query layer, UI, and evaluation are working. BM25F uses title 3.0, department 2.0, description 1.0, prerequisite 0.5 with k1 1.2 and b 0.75. The query layer has phrases, dept/level/credits filters, negation, synonym expansion, spelling suggestions, facets, snippets, and a why panel. Evaluation is 25 queries and 513 pooled judgments. BM25F gets P@10 0.828 and NDCG@10 0.964, flat BM25 gets 0.520 and 0.663. Known-item is a near tie and BM25F actually loses by 0.003 NDCG there. Tests: 38 passing, including a clean-checkout run. Tag and release notes: https://github.com/clmoon2/aggie-course-scout/releases/tag/v0.2-core. Live: https://clmoon2.github.io/aggie-course-scout/.

## Canvas: UI checkpoint

Late UI checkpoint, two pages with desktop, mobile, and detail screenshots. The design uses TAMU maroon and cream, catalog-card results, a visible filter syntax, and a facet column that stacks on mobile. The detail drawer shows the full official description, prerequisites, and the term-by-term why-this-ranked table. There are loading, empty, and index-error states, an ARIA live status, a skip link, visible focus rings, and a reduced-motion rule. Playwright tests cover search, the detail panel, the typo suggestion, facets, the empty state, and 390 px layout without horizontal scroll. Two bugs came out of testing: the detail view used the ranked-list position instead of the document id, and the why table repeated a term score on every field row. Both are fixed. UI PDF attached. Live: https://clmoon2.github.io/aggie-course-scout/.

## Canvas: final submission

Final submission for Aggie Course Scout, a solo BM25F search engine over 10,277 public TAMU catalog records. Live site: https://clmoon2.github.io/aggie-course-scout/. Report: https://clmoon2.github.io/aggie-course-scout/report.html. Repo: https://github.com/clmoon2/aggie-course-scout. The project includes the crawl and manifest, a four-field index, a browser query layer, a static UI, 25 queries with 513 pooled judgments, three baselines, four ablations, a 7-page report, a 10-slide deck with notes, and 38 passing tests. BM25F gets NDCG@10 0.964 against 0.663 for flat BM25, but the win is concentrated in typo and synonym queries. Known-item NDCG is a 0.003 loss to flat BM25. Browser latency is p50 14.4 ms and p95 22.2 ms. Report PDF: docs/report.pdf. Slides: slides/CSCE470_Project_Slides_Carlos_Luna-Pena.pdf. Everything is public and logged out.

## Known limits

- Catalog snapshot from 2026-11-22. No schedule, seats, instructors, or modality.
- College is hand-mapped at department-prefix level. 36 records use "Other/Professional."
- Prerequisite regex can truncate on weird punctuation.
- Phrase search scans all documents.
- Single grader, 25 queries, pooled judgments.
- The `os` acronym over-expands because "operating" and "operations" share a stem.
- Department weight is not supported by the ablation.
- The live site has no production query log. Latency is local headless Chrome.
- Index first load is 2.2 MB gzipped.

## File map

```
src/crawl_catalog.py    crawler
src/text.py             tokenizer and Python stemmer
src/build_index.py      index builder
src/query.py            Python query layer and CLI
src/baselines.py        TF-IDF and flat BM25
src/evaluate.py         pooling, judgments, metrics, ablations
src/latency.py          browser latency
web/index.html          site
web/report.html         report
web/js/search.js        browser query layer
web/js/stemmer.js       matching JavaScript stemmer
web/js/app.js           UI controller
tests/                  unit, CLI, index, browser tests
eval/queries.json       25 queries
eval/judgments.csv      graded pool
eval/results/           metrics and latency
```
