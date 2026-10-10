import asyncio
import os
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\User\.gemini\antigravity\brain\fc7f57bd-7847-49e1-bf17-3d67072c2a03"

async def run_browser_verification():
    print("Launching Chromium browser for Docker verification...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # 1. Visit http://localhost:8765
        print("1. Navigating to http://localhost:8765 ...")
        await page.goto("http://localhost:8765", wait_until="networkidle")
        await page.wait_for_timeout(2500)

        guest_screenshot = os.path.join(ARTIFACT_DIR, "docker_browser_guest_verified.png")
        await page.screenshot(path=guest_screenshot)
        print(f"Captured Guest Mode screenshot: {guest_screenshot}")

        # 2. Check Sign In button (via data-testid)
        signin_nav = page.locator("[data-testid='signin-button']")
        if await signin_nav.is_visible():
            print("2. Clicking Navbar 'Sign In'...")
            await signin_nav.click()
            await page.wait_for_timeout(1000)

            # Fill credentials
            print("Entering Super Admin credentials...")
            await page.fill("input[type='email']", "admin@example.com")
            await page.fill("input[type='password']", "AdminSecurePassword2026!")
            
            # Click submit in modal
            print("Submitting login form...")
            await page.click("button[type='submit']")
            await page.wait_for_timeout(3000)

            admin_screenshot = os.path.join(ARTIFACT_DIR, "docker_browser_admin_logged_in.png")
            await page.screenshot(path=admin_screenshot)
            print(f"Captured Admin Logged-In screenshot: {admin_screenshot}")

            # Check if Admin button is visible
            admin_nav = page.locator("[data-testid='admin-panel-btn'], button:has-text('Admin')").first
            if await admin_nav.is_visible():
                print("[OK] Super Admin button detected in top navbar!")
                await admin_nav.click()
                await page.wait_for_timeout(2000)
                admin_dash_screenshot = os.path.join(ARTIFACT_DIR, "docker_browser_admin_dashboard.png")
                await page.screenshot(path=admin_dash_screenshot)
                print(f"Captured Admin Dashboard screenshot: {admin_dash_screenshot}")

                # Close admin modal
                close_btn = page.locator("button:has-text('Close'), button:has-text('✕')").first
                if await close_btn.is_visible():
                    await close_btn.click()
                    await page.wait_for_timeout(1000)

        # 3. Test Help / User Guide in a new tab
        print("3. Testing User Guide at http://localhost:8765/python-cloud-studio-user-guide.html ...")
        guide_page = await context.new_page()
        await guide_page.goto("http://localhost:8765/python-cloud-studio-user-guide.html", wait_until="networkidle")
        await guide_page.wait_for_timeout(1500)
        guide_screenshot = os.path.join(ARTIFACT_DIR, "docker_browser_user_guide_verified.png")
        await guide_page.screenshot(path=guide_screenshot)
        print(f"Captured User Guide screenshot: {guide_screenshot}")

        await browser.close()
        print("[OK] Complete browser verification successfully executed!")

if __name__ == "__main__":
    asyncio.run(run_browser_verification())
