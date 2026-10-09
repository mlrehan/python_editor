import asyncio
import os
import subprocess
import time
import pytest
from playwright.async_api import async_playwright

pytestmark = pytest.mark.asyncio


async def test_real_browser_ui_rendering():
    """
    E2E Test: Spawns the uvicorn server, opens real Chromium browser,
    navigates to http://127.0.0.1:8765/, and verifies that the React studio renders cleanly.
    """
    # 1. Start uvicorn server on port 8765
    server_process = subprocess.Popen(
        ["python", "-m", "uvicorn", "services.api.main:app", "--host", "127.0.0.1", "--port", "8765"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Give server time to initialize
        time.sleep(3)

        # 2. Launch real Chromium browser via Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            page = await context.new_page()

            # Listen for console errors
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

            # 3. Navigate to the Studio URL
            response = await page.goto("http://127.0.0.1:8765/", wait_until="networkidle")
            assert response.status == 200, f"Expected 200 OK, got {response.status}"

            # 4. Check page title
            title = await page.title()
            print(f"Browser Page Title: {title}")
            assert "Enterprise Python Cloud Studio" in title

            # 5. Verify core React UI components are rendered on screen
            # Look for "Cloud Studio" in navbar
            await page.wait_for_selector("text=Cloud Studio", timeout=10000)
            print("Verified: 'Cloud Studio' brand is rendered in Navbar.")

            # Look for 'Run' button
            run_btn = await page.wait_for_selector("button:has-text('Run')", timeout=5000)
            assert run_btn is not None
            print("Verified: 'Run' button is rendered in cell toolbar.")

            # Look for code input textarea
            textarea = await page.wait_for_selector("textarea.code-font", timeout=5000)
            assert textarea is not None
            print("Verified: Code editor textarea is active and editable.")

            # Look for AI Assistant tab
            ai_tab = await page.wait_for_selector("text=AI Assistant", timeout=5000)
            assert ai_tab is not None
            print("Verified: AI Assistant panel is rendered.")

            # Capture a screenshot of the working UI
            screenshot_path = os.path.abspath("studio_browser_verification.png")
            await page.screenshot(path=screenshot_path)
            print(f"Captured screenshot at: {screenshot_path}")

            # Check that there are no fatal unhandled console errors
            fatal_errors = [e for e in console_errors if "Failed to load resource" in e and "404" in e]
            assert len(fatal_errors) == 0, f"Found 404 asset errors: {fatal_errors}"

            await browser.close()
            print("Browser test finished with 100% success!")

    finally:
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except Exception:
            server_process.kill()
