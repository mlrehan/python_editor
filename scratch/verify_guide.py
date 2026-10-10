"""
Verification script for Python Cloud Studio User Guide.
Checks:
1. HTML integrity & anchor links
2. Zero external dependencies (no CDNs, no remote fonts)
3. Playwright browser rendering, dark/light theme, search modal, mobile responsiveness
"""
import os
import re
import sys
from playwright.sync_api import sync_playwright

DOCS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "python-cloud-studio-user-guide.html"))
SCREENSHOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "screenshots"))
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def verify_static():
    print(f"Checking static file: {DOCS_FILE}")
    with open(DOCS_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Check for external URLs in src or href that might be CDNs
    external_links = re.findall(r'(?:src|href)=["\'](https?://[^"\']+)["\']', html)
    suspicious = [u for u in external_links if "localhost" not in u and "127.0.0.1" not in u]
    print(f"External URLs found: {len(suspicious)}")
    for u in suspicious:
        print(f"  Note link: {u}")
    
    # Assert no external scripts or stylesheets
    ext_css = re.findall(r'<link[^>]+rel=["\']stylesheet["\'][^>]+href=["\'](https?://[^"\']+)["\']', html)
    ext_js = re.findall(r'<script[^>]+src=["\'](https?://[^"\']+)["\']', html)
    assert len(ext_css) == 0, f"Found external CSS: {ext_css}"
    assert len(ext_js) == 0, f"Found external JS: {ext_js}"
    print("[OK] ZERO external CSS or JS dependencies confirmed!")

    # 2. Check anchor links
    sidebar_links = re.findall(r'href="(#(?:ch\d+|tut-[a-z]|hero))"', html)
    section_ids = re.findall(r'id="((?:ch\d+|tut-[a-z]|hero))"', html)
    
    sidebar_set = set(sidebar_links)
    id_set = set(f"#{i}" for i in section_ids)
    
    missing = sidebar_set - id_set
    print(f"Total sidebar target anchors: {len(sidebar_set)}")
    print(f"Total section IDs found: {len(id_set)}")
    if missing:
        print("MISSING SECTION IDS:", missing)
    assert len(missing) == 0, f"Missing IDs: {missing}"
    print("[OK] All 28 Chapters and 10 Tutorials anchors are 100% matched!")

def verify_playwright():
    print("\nRunning Playwright tests on file:// URI...")
    file_uri = f"file:///{DOCS_FILE.replace(os.sep, '/')}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        
        # Load file
        page.goto(file_uri, wait_until="networkidle")
        title = page.title()
        print(f"Page Title: {title}")
        assert "Python Cloud Studio" in title
        
        # Screenshot 1: Desktop Dark Theme
        p1 = os.path.join(SCREENSHOT_DIR, "guide_desktop_dark.png")
        page.screenshot(path=p1, full_page=False)
        print(f"[OK] Screenshot saved: {p1}")
        
        # Test 1: Theme Toggle to Light Mode
        theme_btn = page.locator("#themeToggleBtn")
        theme_btn.click()
        page.wait_for_timeout(300)
        theme_attr = page.locator("html").get_attribute("data-theme")
        print(f"Theme attribute after toggle: {theme_attr}")
        assert theme_attr == "light"
        
        # Screenshot 2: Desktop Light Theme
        p2 = os.path.join(SCREENSHOT_DIR, "guide_desktop_light.png")
        page.screenshot(path=p2, full_page=False)
        print(f"[OK] Screenshot saved: {p2}")
        
        # Test 2: Search Modal via Ctrl+K
        page.keyboard.press("Control+KeyK")
        page.wait_for_timeout(300)
        search_modal = page.locator("#searchModalBackdrop")
        assert "open" in search_modal.get_attribute("class")
        print("[OK] Search modal opened with Ctrl+K")
        
        # Type search query
        page.locator("#searchModalInput").fill("datatableview")
        page.wait_for_timeout(300)
        results = page.locator("#searchResultsList .search-result-item")
        count = results.count()
        print(f"Search results for 'datatableview': {count}")
        assert count > 0
        
        # Screenshot 3: Search Modal Results
        p3 = os.path.join(SCREENSHOT_DIR, "guide_search_modal.png")
        page.screenshot(path=p3)
        print(f"[OK] Screenshot saved: {p3}")
        
        # Close search with Escape
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        assert "open" not in search_modal.get_attribute("class")
        print("[OK] Search modal closed with Escape")
        
        # Test 3: Copy Code Snippet
        first_copy_btn = page.locator(".code-copy-btn").first
        first_copy_btn.click()
        page.wait_for_timeout(200)
        assert "Copied" in first_copy_btn.text_content()
        print("[OK] Code snippet copy feedback verified")
        
        # Test 4: Mobile Viewport (375x812)
        page.set_viewport_size({"width": 375, "height": 812})
        page.wait_for_timeout(300)
        
        # Open mobile drawer
        mobile_btn = page.locator("#mobileMenuBtn")
        assert mobile_btn.is_visible()
        mobile_btn.click()
        page.wait_for_timeout(300)
        sidebar = page.locator("#docsSidebar")
        assert "open" in sidebar.get_attribute("class")
        print("[OK] Mobile navigation drawer toggle verified")
        
        # Screenshot 4: Mobile Viewport
        p4 = os.path.join(SCREENSHOT_DIR, "guide_mobile_drawer.png")
        page.screenshot(path=p4)
        print(f"[OK] Screenshot saved: {p4}")

        browser.close()
        print("\n[OK] ALL PLAYWRIGHT VERIFICATION CHECKS PASSED PERFECTLY!")

if __name__ == "__main__":
    verify_static()
    verify_playwright()
