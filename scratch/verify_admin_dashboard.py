import asyncio
import os
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\User\.gemini\antigravity\brain\fc7f57bd-7847-49e1-bf17-3d67072c2a03"

async def test_admin():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        await page.goto("http://localhost:8765", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # Sign In
        await page.click("[data-testid='signin-button']")
        await page.wait_for_timeout(1000)
        await page.fill("input[type='email']", "admin@example.com")
        await page.fill("input[type='password']", "AdminSecurePassword2026!")
        await page.click("button[type='submit']")
        await page.wait_for_timeout(3000)

        # Click Admin button
        admin_btn = page.locator("button:has-text('Admin')").first
        await admin_btn.click()
        await page.wait_for_timeout(2500)

        admin_dash_screenshot = os.path.join(ARTIFACT_DIR, "docker_browser_admin_dashboard.png")
        await page.screenshot(path=admin_dash_screenshot)
        print(f"Captured: {admin_dash_screenshot}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_admin())

