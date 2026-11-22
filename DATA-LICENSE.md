# Data source and reuse

Course records come from the 2026-2027 Texas A&M University undergraduate and graduate catalogs at https://catalog.tamu.edu/. The catalog text is published by Texas A&M University. This project stores a snapshot for coursework and links every record back to its source URL.

- Source pages: 383 department course-description pages
- Snapshot date: 2026-11-22
- Raw archive: `data/raw/<level>/<dept>.html.gz`
- Processed file: `data/processed/courses.jsonl`
- Processed SHA-256: `176cd0fde5ea33c5ce3a169f3521510285eddc07a845cc72d59c3192c5d5ec8f`
- Crawler user agent: `AggieCourseScout/1.0 (CSCE 470 class project; clmoon2@tamu.edu)`

The catalog's robots.txt allows the course-description paths used here. The raw pages are retained so a reader can check every parsed field. Course descriptions, titles, and credit values remain the property of Texas A&M. The parser, index, UI, evaluation judgments, and report are original work.

If reusing the snapshot, cite the catalog and this repo, and check the live catalog for changes.
