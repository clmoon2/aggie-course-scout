#!/usr/bin/env python3
"""Crawl the public TAMU course catalog into data/processed/courses.jsonl.

Politeness: 4 worker threads, 0.2 s sleep before every request in each worker,
three retries with backoff, one connection pool per worker, robots.txt fetched
and checked at startup. Raw pages are kept gzipped for an audit trail.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
BASE = "https://catalog.tamu.edu"
UA = "AggieCourseScout/1.0 (CSCE 470 class project; clmoon2@tamu.edu)"
WORKERS = 4
DELAY = 0.2
RETRIES = 3
TIMEOUT = 30
INDEXES = [
    ("undergraduate", f"{BASE}/undergraduate/course-descriptions/"),
    ("graduate", f"{BASE}/graduate/course-descriptions/"),
]
CODE_RE = re.compile(r"^([A-Z]{2,5})\s*(\d{3,4}[A-Z]?)\b")
CREDIT_RE = re.compile(r"Credits?\s+(\d+(?:\s*(?:to|-)\s*\d+)?)", re.I)
DEPT_RE = re.compile(r"^([A-Z]{2,5})\s*-\s*(.+?)\s*\(([A-Z]{2,5})\)")

lock = threading.Lock()
seen: set[tuple[str, str]] = set()
records: list[dict] = []
manifest_rows: list[dict] = []
robots_cache: dict[str, RobotFileParser] = {}
robots_lock = threading.Lock()


def check_robots(url: str, session: requests.Session) -> bool:
    host = urlparse(url).netloc
    with robots_lock:
        rp = robots_cache.get(host)
    if rp is None:
        rp = RobotFileParser()
        rp.set_url(f"https://{host}/robots.txt")
        try:
            r = session.get(rp.url, timeout=TIMEOUT)
            rp.parse(r.text.splitlines())
        except requests.RequestException:
            rp = RobotFileParser()
            rp.parse([])
        with robots_lock:
            robots_cache[host] = rp
    return rp.can_fetch(UA, url)


def clean(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    return re.sub(r"\s+", " ", text).strip()


def parse_page(html: str, level: str, dept_code: str, url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.select_one("h1.page-title")
    page_title = clean(h1.get_text(" ")) if h1 else ""
    m = DEPT_RE.match(page_title)
    if m:
        dept_name = m.group(2)
    else:
        m2 = re.match(r"^([A-Z]{2,5})\s*-\s*(.+)$", page_title)
        dept_name = clean(m2.group(2)) if m2 else dept_code
    out = []
    for block in soup.select(".courseblock"):
        title_el = block.select_one(".courseblocktitle")
        desc_el = block.select_one(".courseblockdesc")
        if not title_el or not desc_el:
            continue
        title_text = clean(title_el.get_text(" "))
        cm = CODE_RE.match(title_text)
        if not cm:
            continue
        subject, number = cm.groups()
        code = f"{subject} {number}"
        title = clean(title_text[cm.end():]).strip(" .:-")
        title = re.sub(r"^(?:/\s*[A-Z]{2,5}\s*\d{3,4}[A-Z]?\s*)+", "", title).strip(" .:-")
        if not title:
            title = code
        hours_el = desc_el.select_one(".hours")
        credits = None
        if hours_el:
            hm = CREDIT_RE.search(clean(hours_el.get_text(" ")))
            if hm:
                credits = hm.group(1).replace(" ", "")
            hours_el.decompose()
        body = clean(desc_el.get_text(" "))
        body = re.sub(r"^\([A-Z]{2,5}\s*\d{3,4}[A-Z]?\)\s*", "", body)
        prereq = ""
        coreq = ""
        pm = re.search(r"Prerequisites?(?:\s*\([^)]*\))?\s*:\s*(.*)", body, re.I)
        cm2 = re.search(r"Corequisites?(?:\s*\([^)]*\))?\s*:\s*(.*)", body, re.I)
        if pm:
            prereq = re.split(r"(?:\.\s+(?=[A-Z])|\.$)", pm.group(1))[0].strip(" .")
            body = body[: pm.start()].strip()
        if cm2:
            coreq = re.split(r"(?:\.\s+(?=[A-Z])|\.$)", cm2.group(1))[0].strip(" .")
        body = re.sub(r"\s*(?:Cross Listing|Registration|May be repeated)[^.]*\.\s*$", "", body, flags=re.I).strip()
        # Drop trailing meeting/hour boilerplate that survived.
        body = re.sub(r"\s*\d+\s+(?:Lecture|Lab|Other|Recitation|Seminar)\s+Hours?\.", "", body, flags=re.I)
        body = clean(body).strip(" .")
        num = int(re.match(r"\d+", number).group(0))
        out.append({
            "id": f"{level}:{code.replace(' ', '-')}",
            "level": level,
            "code": code,
            "number": number,
            "title": title,
            "credits": credits,
            "description": body,
            "prerequisites": prereq,
            "corequisites": coreq,
            "department": dept_name,
            "dept_code": dept_code.upper(),
            "college": "",
            "course_level": (num // 1000 if num >= 1000 else num // 100),
            "url": url,
            "source_title": page_title,
        })
    return out


def fetch_one(level: str, dept: str, session: requests.Session) -> dict:
    url = f"{BASE}/{level}/course-descriptions/{dept}/"
    raw_path = RAW / level / f"{dept}.html.gz"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    row = {"level": level, "dept": dept, "url": url, "status": None, "bytes": 0,
           "sha256": None, "courses": 0, "blocks": 0, "error": None, "fetched_at": None}
    if not check_robots(url, session):
        row["error"] = "robots-disallowed"
        return row
    for attempt in range(1, RETRIES + 1):
        time.sleep(DELAY)
        try:
            r = session.get(url, timeout=TIMEOUT)
            row["status"] = r.status_code
            if r.status_code == 404:
                row["error"] = "404"
                break
            r.raise_for_status()
            html = r.text
            data = html.encode("utf-8")
            row["bytes"] = len(data)
            row["sha256"] = hashlib.sha256(data).hexdigest()
            row["fetched_at"] = datetime.now(timezone.utc).isoformat()
            with gzip.open(raw_path, "wb") as f:
                f.write(data)
            row["blocks"] = len(BeautifulSoup(html, "html.parser").select(".courseblock"))
            parsed = parse_page(html, level, dept, url)
            with lock:
                for rec in parsed:
                    key = (level, rec["code"])
                    if key in seen:
                        continue
                    seen.add(key)
                    records.append(rec)
            row["courses"] = len(parsed)
            row["error"] = None
            break
        except requests.RequestException as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"[:300]
            if attempt < RETRIES:
                time.sleep(0.5 * 2 ** (attempt - 1))
    return row


def main() -> int:
    PROC.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": UA})
    jobs = []
    for level, index_url in INDEXES:
        time.sleep(DELAY)
        r = session.get(index_url, timeout=TIMEOUT)
        r.raise_for_status()
        from bs4 import BeautifulSoup as BS
        soup = BS(r.text, "html.parser")
        links = set()
        for a in soup.select("ul.nav.leveltwo a"):
            href = a.get("href", "")
            if f"/{level}/course-descriptions/" in href:
                links.add(href.strip("/").split("/")[-1])
        print(f"{level}: {len(links)} departments", flush=True)
        jobs.extend((level, d) for d in sorted(links))

    print(f"crawling {len(jobs)} department pages with {WORKERS} workers", flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(fetch_one, lvl, dep, session): (lvl, dep) for lvl, dep in jobs}
        done = 0
        for fut in as_completed(futures):
            row = fut.result()
            with lock:
                manifest_rows.append(row)
                done += 1
                if done % 40 == 0:
                    print(f"  {done}/{len(jobs)} pages, {len(records)} unique courses", flush=True)

    from college_map import college_for
    for rec in records:
        rec["college"] = college_for(rec["dept_code"])
    records.sort(key=lambda r: (r["level"], r["code"]))

    out_path = PROC / "courses.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()

    manifest_rows.sort(key=lambda r: (r["level"], r["dept"]))
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_agent": UA,
        "workers": WORKERS,
        "delay_seconds": DELAY,
        "indexes": [u for _, u in INDEXES],
        "pages_requested": len(jobs),
        "pages_ok": sum(1 for r in manifest_rows if r["status"] == 200 and not r["error"]),
        "pages_with_block": sum(1 for r in manifest_rows if r.get("blocks", 0) > 0),
        "pages_with_records": sum(1 for r in manifest_rows if r.get("courses", 0) > 0),
        "pages_empty": sum(1 for r in manifest_rows if r["status"] == 200 and r.get("blocks", 0) == 0),
        "pages_404": sum(1 for r in manifest_rows if r["status"] == 404),
        "pages_error": sum(1 for r in manifest_rows if r["error"] and r["status"] != 404),
        "courses_unique": len(records),
        "courses_output_sha256": digest,
        "output": str(out_path.relative_to(ROOT)),
        "rows": manifest_rows,
    }
    (PROC / "crawl_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {len(records)} courses, sha256 {digest}")
    print(f"manifest pages ok={manifest['pages_ok']} 404={manifest['pages_404']} error={manifest['pages_error']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
