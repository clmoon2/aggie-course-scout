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
        b = p.chromium.launch()
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


def test_typo_suggestion_and_correction_only(browser, server):
    page = browser.new_page()
    load(page, server)
    page.fill("#q", "databse")
    page.wait_for_selector(".suggest")
    assert "database" in page.locator(".suggest").inner_text().lower()
    assert page.locator(".card").count() > 0
    page.locator(".suggest .linkish").click()
    page.wait_for_timeout(600)
    assert page.input_value("#q") == "database"
    assert page.locator(".suggest").count() == 0
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


def test_credit_bucket_facet(browser, server):
    page = browser.new_page()
    load(page, server)
    page.fill("#q", "dental hygiene")
    page.wait_for_selector(".card")
    group = page.locator(".facet-group").filter(has=page.locator("h3", has_text="Credits"))
    button = group.locator('[data-facet-value="1-2"]')
    async_count = int(button.locator(".count").inner_text())
    button.click()
    page.wait_for_timeout(500)
    assert "credits:1-2" in page.input_value("#q")
    assert page.locator(".card").count() == min(async_count, 20)
    page.close()


def test_college_facet_filters_and_selected_state(browser, server):
    page = browser.new_page()
    load(page, server)
    page.fill("#q", "dental hygiene")
    page.wait_for_selector(".card")
    before = int(page.locator("#summary strong").inner_text())
    button = page.locator('[data-facet-value="college-of-dentistry"]')
    advertised = int(button.locator(".count").inner_text())
    assert advertised < before
    button.click()
    page.wait_for_timeout(600)
    assert "college:college-of-dentistry" in page.input_value("#q")
    assert int(page.locator("#summary strong").inner_text()) == advertised
    assert page.locator(".facet.selected").count() == 1
    assert page.locator(".facet.selected").get_attribute("aria-pressed") == "true"
    page.close()


def test_credits_facet_counts_match_all_buckets(browser, server):
    page = browser.new_page()
    load(page, server)
    page.fill("#q", "dental hygiene")
    page.wait_for_selector(".facet")
    group = page.locator(".facet-group").filter(has=page.locator("h3", has_text="Credits"))
    for label in ["0", "1-2", "3", "4", "5+"]:
        button = group.locator(f'[data-facet-value="{label}"]')
        advertised = int(button.locator(".count").inner_text())
        button.click()
        page.wait_for_timeout(500)
        assert int(page.locator("#summary strong").inner_text()) == advertised, label
        page.locator(".facet.selected").click()
        page.wait_for_timeout(400)
    page.close()


def test_initial_empty_is_full_width(browser, server):
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    load(page, server)
    assert page.locator("#facet-panel").is_hidden()
    assert page.locator("#empty").is_visible()
    assert page.locator("#empty").bounding_box()["width"] > 600
    assert page.locator("#empty-title").inner_text() == "Search the catalog."
    page.fill("#q", "zzzznotacourse")
    page.wait_for_timeout(700)
    assert page.locator("#summary").inner_text() == ""
    assert page.locator("#empty").bounding_box()["width"] > 600
    assert page.get_by_text("No courses matched.", exact=True).count() == 1
    page.close()


def test_mobile_scrolls_to_results(browser, server):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    load(page, server)
    page.fill("#q", "dental hygiene")
    page.press("#q", "Enter")
    page.wait_for_selector(".card")
    page.wait_for_timeout(800)
    assert page.evaluate("window.scrollY") > 300
    assert page.locator("#results").bounding_box()["y"] < 844
    page.close()


def test_detail_backdrop_and_focus_restore(browser, server):
    page = browser.new_page()
    load(page, server)
    page.fill("#q", "dental hygiene")
    page.wait_for_selector(".card")
    trigger = page.locator(".card h2 button").first
    trigger.focus()
    trigger.click()
    assert page.locator("#detail-backdrop").is_visible()
    page.locator("#detail-close").click()
    assert not page.locator("#detail-backdrop").is_visible()
    assert page.evaluate("document.activeElement === document.querySelector('.card h2 button')")
    page.close()


def test_query_typed_during_boot_is_queued(browser, server):
    page = browser.new_page()
    import time as _time
    def slow(route):
        _time.sleep(1.2)
        route.continue_()
    page.route("**/data/index.json.gz", slow)
    page.goto(server, wait_until="domcontentloaded")
    page.fill("#q", "computer security")
    page.press("#q", "Enter")
    page.wait_for_function("window.__ready === true", timeout=30000)
    page.wait_for_selector(".card")
    assert page.input_value("#q") == "computer security"
    assert page.locator(".card").count() == 20
    page.close()


def test_error_panel_and_retry(browser, server):
    page = browser.new_page()
    failed = {"done": False}
    def fail_once(route):
        if not failed["done"]:
            failed["done"] = True
            route.abort()
        else:
            route.continue_()
    page.route("**/data/index.json.gz", fail_once)
    page.goto(server, wait_until="networkidle")
    page.wait_for_selector("#error-panel:not([hidden])")
    assert page.locator("#retry").is_visible()
    page.fill("#q", "dental hygiene")
    page.press("#q", "Enter")
    page.wait_for_timeout(200)
    assert page.locator("#error-panel").is_visible()
    page.locator("#retry").click()
    page.wait_for_function("window.__ready === true", timeout=30000)
    page.wait_for_selector(".card")
    assert page.locator(".card").count() == 20
    page.close()


def test_loading_state_paints_before_search(browser, server):
    page = browser.new_page()
    load(page, server)
    page.evaluate("""
      window.__sawLoading = false;
      const el = document.querySelector('#loading');
      new MutationObserver(() => { if (!el.hidden) window.__sawLoading = true; })
        .observe(el, { attributes: true, attributeFilter: ['hidden'] });
    """)
    page.fill("#q", "dental hygiene")
    page.press("#q", "Enter")
    page.wait_for_selector(".card")
    assert page.evaluate("window.__sawLoading") is True
    page.close()


def test_singular_summary(browser, server):
    page = browser.new_page()
    load(page, server)
    page.fill("#q", 'dept:DDHS "Preclinical Dental Hygiene"')
    page.wait_for_selector(".card")
    assert "1 course matches" in page.locator("#summary").inner_text()
    page.close()
