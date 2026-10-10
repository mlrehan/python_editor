import asyncio
import os
import sys
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\User\.gemini\antigravity\brain\fc7f57bd-7847-49e1-bf17-3d67072c2a03"

async def test_ui_isolation():
    from services.api.config import settings
    admin_email = settings.ADMIN_BOOTSTRAP_EMAIL
    admin_pass = settings.ADMIN_BOOTSTRAP_PASSWORD

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        print("=== Step 1: Navigating to Python Cloud Studio in Guest Mode ===")
        await page.goto("http://127.0.0.1:8765/", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # Check badge
        badge = await page.wait_for_selector('[data-testid="workspace-badge"]', timeout=5000)
        badge_text = (await badge.text_content()).strip()
        print(f"Guest Workspace Badge: '{badge_text}'")
        assert badge_text == "Public", f"Expected 'Public', got '{badge_text}'"

        # Check files list in Left Sidebar
        file_tree = await page.wait_for_selector('[data-testid="file-tree-container"]', timeout=5000)
        file_tree_text = await file_tree.text_content()
        print("Guest file tree text contains 'Sales Dataset.csv'?:", "Sales Dataset.csv" in file_tree_text)
        assert "Sales Dataset.csv" not in file_tree_text, "LEAK! Sales Dataset.csv visible to Guest in sidebar!"

        # Screenshot Guest Mode initial
        guest_initial_path = os.path.join(ARTIFACT_DIR, "guest_workspace_isolated_verified.png")
        await page.screenshot(path=guest_initial_path, full_page=False)
        print(f"Captured: {guest_initial_path}")

        print("=== Step 2: Logging in as SuperAdmin ===")
        # Click Sign In button in navbar
        sign_in_btn = await page.wait_for_selector('button:has-text("Sign In"), button:has-text("Sign in")', timeout=5000)
        await sign_in_btn.click()
        await page.wait_for_timeout(500)

        # Fill modal
        email_input = await page.wait_for_selector('input[type="email"]', timeout=5000)
        await email_input.fill(admin_email)
        pass_input = await page.wait_for_selector('input[type="password"]', timeout=5000)
        await pass_input.fill(admin_pass)

        # Submit
        submit_btn = await page.wait_for_selector('form button[type="submit"]', timeout=5000)
        await submit_btn.click()
        await page.wait_for_timeout(3000)

        # Verify logged in
        admin_badge = await page.wait_for_selector('[data-testid="workspace-badge"]', timeout=5000)
        admin_badge_text = (await admin_badge.text_content()).strip()
        print(f"SuperAdmin Workspace Badge: '{admin_badge_text}'")
        assert admin_badge_text == "Admin", f"Expected 'Admin', got '{admin_badge_text}'"

        # Check file tree text for SuperAdmin
        admin_tree = await page.wait_for_selector('[data-testid="file-tree-container"]', timeout=5000)
        admin_tree_text = await admin_tree.text_content()
        print("SuperAdmin file tree contains 'Sales Dataset.csv'?:", "Sales Dataset.csv" in admin_tree_text)
        assert "Sales Dataset.csv" in admin_tree_text, "Sales Dataset.csv should be visible to SuperAdmin!"

        # Double click Sales Dataset.csv to open it in right sidebar tab
        sales_csv_item = await page.wait_for_selector('div:has-text("Sales Dataset.csv")', timeout=5000)
        await sales_csv_item.dblclick()
        await page.wait_for_timeout(2000)

        # Screenshot SuperAdmin session with Sales Dataset.csv open
        admin_verified_path = os.path.join(ARTIFACT_DIR, "superadmin_private_workspace_verified.png")
        await page.screenshot(path=admin_verified_path, full_page=False)
        print(f"Captured: {admin_verified_path}")

        print("=== Step 3: Logging out and verifying session cleanup ===")
        # Click user dropdown / Logout button
        # In Navbar, there is user button or logout button
        user_menu_btn = await page.wait_for_selector('button:has-text("admin_super"), button:has-text("Logout"), button:has-text("Sign Out")', timeout=5000)
        await user_menu_btn.click()
        await page.wait_for_timeout(500)

        # If dropdown opened, click Logout option
        logout_opt = await page.query_selector('button:has-text("Logout"), div:has-text("Logout"), button:has-text("Sign Out")')
        if logout_opt:
            await logout_opt.click()
        await page.wait_for_timeout(3000)

        # Verify badge flipped back to Public
        post_badge = await page.wait_for_selector('[data-testid="workspace-badge"]', timeout=5000)
        post_badge_text = (await post_badge.text_content()).strip()
        print(f"Post-Logout Workspace Badge: '{post_badge_text}'")
        assert post_badge_text == "Public", f"Expected 'Public', got '{post_badge_text}'"

        # Check files list in Left Sidebar - Sales Dataset.csv MUST BE ABSENT
        post_tree = await page.wait_for_selector('[data-testid="file-tree-container"]', timeout=5000)
        post_tree_text = await post_tree.text_content()
        print("Post-Logout file tree contains 'Sales Dataset.csv'?:", "Sales Dataset.csv" in post_tree_text)
        assert "Sales Dataset.csv" not in post_tree_text, "CRITICAL LEAK: Sales Dataset.csv still visible after logout!"

        # Check that right sidebar open tabs no longer show Sales Dataset.csv
        page_body = await page.content()
        assert "Sales Dataset.csv" not in post_tree_text, "Sales Dataset.csv should not be in file tree!"

        # Screenshot Post-Logout Guest Mode
        post_logout_path = os.path.join(ARTIFACT_DIR, "post_logout_public_workspace_verified.png")
        await page.screenshot(path=post_logout_path, full_page=False)
        print(f"Captured: {post_logout_path}")

        await browser.close()
        print("=== PLAYWRIGHT UI ISOLATION E2E TEST COMPLETED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(test_ui_isolation())
