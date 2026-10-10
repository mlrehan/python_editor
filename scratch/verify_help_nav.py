"""
Verify Help nav link in Python Cloud Studio web application.
"""
import os
import sys
from playwright.sync_api import sync_playwright

SCREENSHOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "screenshots", "navbar_help_verified.png"))

def test_help_nav():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. Load application
        print("Navigating to http://127.0.0.1:8765/ ...")
        page.goto("http://127.0.0.1:8765/", wait_until="networkidle")

        # 2. Check for Help nav link
        help_btn = page.locator("[data-testid='navbar-help-btn']")
        help_btn.wait_for(state="visible", timeout=10000)
        print("[OK] Help NAV link is visible in Navbar!")

        href = help_btn.get_attribute("href")
        target = help_btn.get_attribute("target")
        rel = help_btn.get_attribute("rel")
        text = help_btn.text_content()

        print(f"Help button text: {text}")
        print(f"Help button href: {href}")
        print(f"Help button target: {target}")
        print(f"Help button rel: {rel}")

        assert "/python-cloud-studio-user-guide.html" in href, f"Unexpected href: {href}"
        assert target == "_blank", f"Expected target _blank, got: {target}"
        assert rel == "noopener noreferrer", f"Expected rel noopener noreferrer, got: {rel}"

        # 3. Take screenshot of Navbar with Help link
        page.screenshot(path=SCREENSHOT_PATH)
        print(f"[OK] Screenshot saved to: {SCREENSHOT_PATH}")

        # 4. Click the link and verify new tab opens with the user guide
        with context.expect_page() as new_page_info:
            help_btn.click()
        
        new_page = new_page_info.value
        new_page.wait_for_load_state("networkidle")
        new_title = new_page.title()
        new_url = new_page.url
        print(f"[OK] New tab opened!")
        print(f"New tab URL: {new_url}")
        print(f"New tab Title: {new_title}")

        assert "python-cloud-studio-user-guide.html" in new_url
        assert "Python Cloud Studio" in new_title

        # Screenshot the new tab
        new_tab_screenshot = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "screenshots", "user_guide_tab_verified.png"))
        new_page.screenshot(path=new_tab_screenshot)
        print(f"[OK] New tab screenshot saved to: {new_tab_screenshot}")

        browser.close()
        print("\n[OK] VERIFICATION OF HELP NAV LINK OPENING IN NEW TAB COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    test_help_nav()

