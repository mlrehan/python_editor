import asyncio
import os
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\User\.gemini\antigravity\brain\fc7f57bd-7847-49e1-bf17-3d67072c2a03"

async def test_guest_execution():
    print("Testing Guest Mode code execution after Admin session...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Step 1: First login as Admin and run a cell (to populate admin kernel session)
        ctx_admin = await browser.new_context(viewport={"width": 1440, "height": 900})
        page_admin = await ctx_admin.new_page()
        await page_admin.goto("http://localhost:8765", wait_until="networkidle")
        await page_admin.wait_for_timeout(2000)

        await page_admin.click("[data-testid='signin-button']")
        await page_admin.wait_for_timeout(800)
        await page_admin.fill("input[type='email']", "admin@example.com")
        await page_admin.fill("input[type='password']", "AdminSecurePassword2026!")
        await page_admin.click("button[type='submit']")
        await page_admin.wait_for_timeout(2500)

        # Run a cell as Admin
        run_btn = page_admin.locator("button[title*='Run'], button:has-text('▶')").first
        if await run_btn.is_visible():
            await run_btn.click()
            await page_admin.wait_for_timeout(2500)
        await ctx_admin.close()
        print("[1/2] Admin session executed.")

        # Step 2: Now open a brand new Guest session and execute code in Guest Mode!
        ctx_guest = await browser.new_context(viewport={"width": 1440, "height": 900})
        page_guest = await ctx_guest.new_page()
        await page_guest.goto("http://localhost:8765", wait_until="networkidle")
        await page_guest.wait_for_timeout(2500)

        # Clear any old outputs first if needed
        clear_btn = page_guest.locator("button:has-text('Clear Outputs')").first
        if await clear_btn.is_visible():
            await clear_btn.click()
            await page_guest.wait_for_timeout(500)

        # Click "+ Add Code Cell" or "+ Code"
        add_code_btn = page_guest.locator("button:has-text('+ Code'), button:has-text('+ Add Code Cell')").first
        if await add_code_btn.is_visible():
            await add_code_btn.click()
            await page_guest.wait_for_timeout(1000)

        # Run the cells in Guest Mode
        run_all_btn = page_guest.locator("button:has-text('Run All')").first
        if await run_all_btn.is_visible():
            await run_all_btn.click()
            print("Clicked 'Run All' in Guest Mode. Waiting for execution...")
            await page_guest.wait_for_timeout(4000)

        guest_exec_screenshot = os.path.join(ARTIFACT_DIR, "guest_mode_execution_fixed_verified.png")
        await page_guest.screenshot(path=guest_exec_screenshot)
        print(f"[2/2] Captured Guest Mode Execution screenshot: {guest_exec_screenshot}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_guest_execution())

