import pytest
from playwright.async_api import async_playwright
import time
import os

BASE_URL = "http://127.0.0.1:8765"
SCREENSHOT_DIR = r"C:\Users\User\.gemini\antigravity\brain\fc7f57bd-7847-49e1-bf17-3d67072c2a03"

@pytest.mark.asyncio
async def test_ui_restart_kernel_and_pip_rich_execution():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        # 1. Open app
        await page.goto(BASE_URL)
        await page.wait_for_selector('[data-testid="navbar-restart-btn"]', timeout=15000)

        # 2. Login as SuperAdmin so package installation is authorized
        await page.click('button:has-text("Sign In")')
        await page.wait_for_selector('input[type="email"]', timeout=5000)
        await page.fill('input[type="email"]', "admin@example.com")
        await page.fill('input[type="password"]', "AdminSecurePassword2026!")
        await page.click('button[type="submit"]')

        # Wait for signed in indicator
        await page.wait_for_selector('[data-testid="workspace-indicator-private"]', timeout=10000)
        print("\n[E2E STEP 1] Successfully signed in to private workspace as SuperAdmin")

        # 3. Click "Restart" button on top bar
        restart_btn = page.locator('[data-testid="navbar-restart-btn"]')
        await restart_btn.click()

        # Check for Restarting visual feedback (button disabled, toast banner visible)
        toast = page.locator('[data-testid="kernel-toast-banner"]')
        await toast.wait_for(state="visible", timeout=5000)
        toast_text = await toast.text_content()
        print(f"[E2E STEP 2] Toast appeared immediately during restart: '{toast_text.strip()}'")

        # Wait for restart completion toast
        await page.wait_for_function(
            "() => document.querySelector('[data-testid=\"kernel-toast-banner\"]')?.textContent?.includes('restarted successfully')",
            timeout=15000
        )
        print("[E2E STEP 3] Kernel restart completed and green confirmation toast displayed")

        # Capture screenshot of restarted state
        screenshot_path = os.path.join(SCREENSHOT_DIR, "kernel_restart_toast_verified.png")
        await page.screenshot(path=screenshot_path)
        print(f"[E2E STEP 4] Screenshot saved to: {screenshot_path}")

        # 4. In the first code cell, execute: from rich import print as rprint; rprint('[bold green]RICH WORKS![/bold green]')
        first_cell_textarea = page.locator('textarea').first
        await first_cell_textarea.fill("from rich import print as rprint\nrprint('[bold green]RICH WORKS![/bold green]')\nprint('VERIFIED_RICH_OUTPUT')")

        # Run cell with run button
        run_btn = page.locator('[data-testid="cell-run-btn"]').first
        await run_btn.click()

        # Wait for cell execution output to appear
        output_locator = page.locator('[data-testid="cell-output-container"]').first
        await output_locator.wait_for(state="visible", timeout=20000)
        await page.wait_for_function(
            "() => document.querySelector('[data-testid=\"cell-output-container\"]')?.textContent?.includes('VERIFIED_RICH_OUTPUT')",
            timeout=15000
        )
        output_content = await output_locator.text_content()
        print(f"[E2E STEP 5] Cell output successfully received: '{output_content.strip()}'")
        assert "VERIFIED_RICH_OUTPUT" in output_content

        # Capture screenshot of rich module working inside the code cell output
        screenshot_path_rich = os.path.join(SCREENSHOT_DIR, "rich_module_output_verified.png")
        await page.screenshot(path=screenshot_path_rich)
        print(f"[E2E STEP 6] Rich execution screenshot saved to: {screenshot_path_rich}")

        await browser.close()
        print("[E2E COMPLETED] Full user journey verified successfully with zero errors!")
