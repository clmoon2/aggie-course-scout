import http.server
import socketserver
import threading
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def server():
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=str(ROOT / "web"), **kw)
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
        port = httpd.server_address[1]
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        yield f"http://127.0.0.1:{port}/"
        httpd.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        yield b
        b.close()


def load(page, base):
    page.goto(base, wait_until="networkidle")
    page.wait_for_function("window.__ready === true", timeout=30000)


def test_desktop_search_and_detail(browser, server):
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    load(page, server)
    page.fill("#q", "computer security")
    page.wait_for_selector(".card")
    assert page.locator(".card").count() == 20
    assert "security" in page.locator(".card").first.inner_text().lower()
    page.locator(".why-toggle").first.click()
    assert page.locator(".why tr").count() > 0
    page.locator(".card h2 button").first.click()
    assert page.locator("#detail").is_visible()
    assert page.locator("#detail h2").inner_text().strip()
    page.locator("#detail-close").click()
    assert not page.locator("#detail").is_visible()
    page.close()


def test_typo_suggestion(browser, server):
    page = browser.new_page()
    load(page, server)
    page.fill("#q", "databse")
    page.wait_for_selector(".suggest")
    assert "database" in page.locator(".suggest").inner_text().lower()
    assert page.locator(".card").count() > 0
    page.close()


def test_facet_and_empty_state(browser, server):
    page = browser.new_page()
    load(page, server)
    page.fill("#q", "networks")
    page.wait_for_selector(".card")
    page.locator(".facet").first.click()
    page.wait_for_timeout(300)
    assert ":" in page.input_value("#q")
    page.fill("#q", "zzzznotacourse")
    page.wait_for_timeout(600)
    assert page.locator("#empty").is_visible()
    page.close()


def test_mobile_no_horizontal_scroll(browser, server):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    load(page, server)
    page.fill("#q", "machine learning")
    page.wait_for_selector(".card")
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= 390
    page.close()


def test_credit_range_facet(browser, server):
    page = browser.new_page()
    load(page, server)
    page.fill("#q", "dept:csce")
    page.wait_for_selector(".facet")
    page.locator(".facet", has_text="0to4").first.click()
    page.wait_for_timeout(400)
    assert "credits:>=0 credits:<=4" in page.input_value("#q")
    assert page.locator(".card").count() > 0
    page.close()
