#!/usr/bin/env python3
"""Measure in-browser query latency for the 25 evaluation queries."""
from __future__ import annotations

import http.server
import json
import statistics
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
QUERIES = json.loads((ROOT / "eval" / "queries.json").read_text())
OUT = ROOT / "eval" / "results" / "latency.json"


def main() -> None:
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=str(ROOT / "web"), **kw)
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome")
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
            page.wait_for_function("window.__ready === true", timeout=30000)
            node_count = page.evaluate("navigator.hardwareConcurrency")
            samples = []
            for _ in range(3):
                for q in QUERIES:
                    page.evaluate("window.__lastLatency = undefined")
                    page.fill("#q", q["query"])
                    page.wait_for_function("window.__lastLatency !== undefined")
                    samples.append(page.evaluate("window.__lastLatency"))
                    page.wait_for_timeout(40)
            # Clear and get a clean load measurement.
            load_ms = page.evaluate("window.__readyMs")
            index_fetch = page.evaluate("performance.getEntriesByType('resource').filter(r => r.name.includes('index.json.gz')).map(r => r.duration)")[0]
            browser.close()
        httpd.shutdown()
    samples.sort()
    p50 = statistics.median(samples)
    p95 = samples[int(len(samples) * 0.95) - 1]
    result = {
        "samples": len(samples),
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "min_ms": round(min(samples), 2),
        "max_ms": round(max(samples), 2),
        "mean_ms": round(statistics.mean(samples), 2),
        "index_load_ms": round(load_ms, 2),
        "index_fetch_ms": round(index_fetch, 2),
        "index_gzip_bytes": (ROOT / "web" / "data" / "index.json.gz").stat().st_size,
        "environment": "Chrome stable, Playwright, localhost, 1280x900, headless",
        "hardware_concurrency": node_count,
        "queries": len(QUERIES),
        "repetitions": 3,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
