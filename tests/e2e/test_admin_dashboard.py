import asyncio
import os
import pytest
from playwright.async_api import async_playwright

pytestmark = pytest.mark.asyncio

SERVER_URL = "http://127.0.0.1:8765"


async def test_admin_dashboard_open_and_all_tabs():
    """
    E2E Verification for:
    1. Super Admin authentication.
    2. Clicking 'Admin' button in Navbar opens Super Admin Console modal immediately.
    3. No empty screen or React crash occurs.
    4. Overview tab displays system metrics (Users, Notebooks, RAM, Disk).
    5. All other tabs (Users, Packages, Runtimes, Workspaces, Audit, Profile) open and render without error.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda msg: (
            console_errors.append(msg.text) if msg.type == "error" else None,
            print(f"[BROWSER {msg.type}]: {msg.text}") if msg.type in ("error", "warning") else None
        ))

        # 1. Navigate to Studio
        response = await page.goto(f"{SERVER_URL}/", wait_until="domcontentloaded")
        assert response.status == 200

        # Wait for page elements to mount
        await page.wait_for_selector('header', timeout=8000)

        # 2. Check if already signed in as admin or need to sign in
        admin_btn = page.locator('[data-testid="admin-panel-btn"]')
        if await admin_btn.count() == 0:
            # Need to sign in
            signin_btn = await page.wait_for_selector('[data-testid="signin-button"]', timeout=8000)
            await signin_btn.click()
            await asyncio.sleep(0.5)

            # Fill Super Admin Credentials
            await page.wait_for_selector('[data-testid="auth-modal"]', timeout=5000)
            await page.locator('[data-testid="auth-modal"] input[type="email"]').fill("admin@example.com")
            await page.locator('[data-testid="auth-modal"] input[type="password"]').fill("AdminSecurePassword2026!")
            await page.locator('[data-testid="auth-modal"] button[type="submit"]').click()
            await asyncio.sleep(2.0)

            # Auth modal should close
            assert await page.locator('[data-testid="auth-modal"]').count() == 0, "Auth modal should close on successful login"

        # 3. Find Admin Button in Navbar
        admin_btn_elem = await page.wait_for_selector('[data-testid="admin-panel-btn"]', timeout=8000)
        assert admin_btn_elem is not None, "Admin button must be visible for Super Admin"
        print("Verified: 'Admin' button is visible in Navbar.")

        # 4. Click Admin Button
        await admin_btn_elem.click()
        await asyncio.sleep(1.0)

        # 5. Verify Admin Dashboard Modal is Open and Rendered (NOT EMPTY!)
        modal = await page.wait_for_selector('[data-testid="admin-dashboard-modal"]', timeout=8000)
        assert modal is not None, "Admin Dashboard modal must open upon clicking Admin button!"
        print("Verified: Admin Dashboard modal is open and visible.")

        # Verify Modal Header & Content
        modal_text = await modal.text_content()
        assert "Super Admin Console" in modal_text, "Modal title must display 'Super Admin Console'"
        assert "Platform Health & Overview" in modal_text, "Overview tab heading must display"

        # Verify Overview Metrics
        assert "Registered Users" in modal_text, "Registered Users card must render"
        assert "Notebooks Created" in modal_text, "Notebooks Created card must render"
        assert "System RAM Memory" in modal_text, "System RAM card must render"
        assert "Server Disk Storage" in modal_text, "Server Disk card must render"
        print("Verified: Overview tab statistics and hardware metrics rendered successfully.")

        # 6. Test Tab: Users
        users_tab_btn = await page.wait_for_selector('[data-testid="admin-tab-users"]', timeout=5000)
        await users_tab_btn.click()
        await asyncio.sleep(0.8)
        modal_text = await modal.text_content()
        assert "Add New User" in modal_text, "User management actions must render"
        assert "admin@example.com" in modal_text, "Super admin user must be listed in users table"
        print("Verified: User Management tab rendered successfully.")

        # 7. Test Tab: Packages
        pkg_tab_btn = await page.wait_for_selector('[data-testid="admin-tab-packages"]', timeout=5000)
        await pkg_tab_btn.click()
        await asyncio.sleep(0.8)
        modal_text = await modal.text_content()
        assert "numpy" in modal_text.lower(), "Packages tab must display installed packages (e.g. numpy)"
        print("Verified: Python Packages tab rendered successfully.")

        # 8. Test Tab: Kernel Memory / Runtimes
        rt_tab_btn = await page.wait_for_selector('[data-testid="admin-tab-runtimes"]', timeout=5000)
        await rt_tab_btn.click()
        await asyncio.sleep(0.8)
        modal_text = await modal.text_content()
        assert "Active Kernel Runtimes" in modal_text or "Kernel Runtimes" in modal_text
        print("Verified: Kernel Memory tab rendered successfully.")

        # 9. Test Tab: Global Workspaces
        ws_tab_btn = await page.wait_for_selector('[data-testid="admin-tab-workspaces"]', timeout=5000)
        await ws_tab_btn.click()
        await asyncio.sleep(0.8)
        modal_text = await modal.text_content()
        assert "Global Workspace" in modal_text
        print("Verified: Global Workspaces tab rendered successfully.")

        # 10. Test Tab: Audit Logs
        audit_tab_btn = await page.wait_for_selector('[data-testid="admin-tab-audit"]', timeout=5000)
        await audit_tab_btn.click()
        await asyncio.sleep(0.8)
        modal_text = await modal.text_content()
        assert "Audit Log" in modal_text
        print("Verified: Audit Logs tab rendered successfully.")

        # 11. Test Tab: Admin Profile
        settings_tab_btn = await page.wait_for_selector('[data-testid="admin-tab-settings"]', timeout=5000)
        await settings_tab_btn.click()
        await asyncio.sleep(0.8)
        modal_text = await modal.text_content()
        assert "Admin Email" in modal_text and "New Password" in modal_text
        print("Verified: Admin Profile tab rendered successfully.")

        # Switch back to Overview tab for screenshot
        overview_tab_btn = await page.wait_for_selector('[data-testid="admin-tab-overview"]', timeout=5000)
        await overview_tab_btn.click()
        await asyncio.sleep(0.8)

        # 12. Capture Verification Screenshot
        screenshot_path = os.path.abspath("admin_dashboard_verified.png")
        await page.screenshot(path=screenshot_path)
        print(f"Captured Admin Dashboard verification screenshot at: {screenshot_path}")

        # Verify no React crash console errors
        uncaught_errors = [e for e in console_errors if "Uncaught" in e or "TypeError" in e]
        assert len(uncaught_errors) == 0, f"Uncaught console errors detected: {uncaught_errors}"

        await browser.close()
