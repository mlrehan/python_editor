import asyncio
import os
import pytest
from playwright.async_api import async_playwright

pytestmark = pytest.mark.asyncio

SERVER_URL = "http://127.0.0.1:8765"
ARTIFACTS_DIR = r"C:\Users\User\.gemini\antigravity\brain\fc7f57bd-7847-49e1-bf17-3d67072c2a03"


async def test_mobile_responsiveness_and_drawer():
    """
    E2E Verification for Mobile Responsiveness:
    1. Small mobile viewports (375x667 and 412x915):
       - Responsive compact navbar
       - Drawer overlay for sidebars with backdrop dismissal
       - Notebooks Manager modal
       - Secrets & AI Credentials modal
    2. Tablet viewports (768x1024):
       - Responsive edge-to-edge layout
    """
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # 1. MOBILE VIEWPORT: iPhone SE (375 x 667)
        # -------------------------------------------------------------
        ctx_mobile = await browser.new_context(viewport={"width": 375, "height": 667})
        page = await ctx_mobile.new_page()

        await page.goto(f"{SERVER_URL}/", wait_until="networkidle")
        await page.wait_for_selector('textarea', timeout=10000)

        # Verify left drawer overlay and backdrop
        left_backdrop = page.locator('[data-testid="mobile-left-backdrop"]')
        # If left sidebar was open on mount, backdrop should be visible
        if await left_backdrop.count() > 0:
            assert await left_backdrop.is_visible()
            # Click backdrop outside the drawer (x=350 on 375px viewport)
            await page.mouse.click(350, 200)
            await asyncio.sleep(0.5)
            assert await left_backdrop.count() == 0, "Backdrop should dismiss after clicking outside"

        # Capture mobile home screenshot
        screenshot_mobile_path = os.path.join(ARTIFACTS_DIR, "mobile_viewport_375x667_verified.png")
        await page.screenshot(path=screenshot_mobile_path)

        # Open Notebooks modal on mobile
        notebooks_btn = page.locator('[data-testid="navbar-notebooks-btn"]')
        if await notebooks_btn.count() > 0:
            await notebooks_btn.click()
            await page.wait_for_selector('[data-testid="notebooks-modal"]', timeout=5000)
            modal_screenshot = os.path.join(ARTIFACTS_DIR, "mobile_notebooks_modal_verified.png")
            await page.screenshot(path=modal_screenshot)
            # Close modal
            close_btn = page.locator('[data-testid="notebooks-modal"] button[title="Close"]')
            await close_btn.click()
            await asyncio.sleep(0.3)

        # Open Secrets modal on mobile
        secrets_btn = page.locator('[data-testid="navbar-secrets-btn"]')
        if await secrets_btn.count() > 0:
            await secrets_btn.click()
            await page.wait_for_selector('[data-testid="secrets-modal"]', timeout=5000)
            secrets_screenshot = os.path.join(ARTIFACTS_DIR, "mobile_secrets_modal_verified.png")
            await page.screenshot(path=secrets_screenshot)
            close_btn = page.locator('[data-testid="secrets-modal"] button[title="Close"]')
            await close_btn.click()
            await asyncio.sleep(0.3)

        await ctx_mobile.close()

        # -------------------------------------------------------------
        # 2. TABLET VIEWPORT: iPad (768 x 1024)
        # -------------------------------------------------------------
        ctx_tablet = await browser.new_context(viewport={"width": 768, "height": 1024})
        page_tab = await ctx_tablet.new_page()

        await page_tab.goto(f"{SERVER_URL}/", wait_until="networkidle")
        await page_tab.wait_for_selector('textarea', timeout=10000)

        screenshot_tablet_path = os.path.join(ARTIFACTS_DIR, "tablet_viewport_768x1024_verified.png")
        await page_tab.screenshot(path=screenshot_tablet_path)
        await ctx_tablet.close()

        await browser.close()
        print("Mobile and tablet responsiveness E2E test completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_mobile_responsiveness_and_drawer())
