import asyncio
import os
import time
import pytest
from playwright.async_api import async_playwright

pytestmark = pytest.mark.asyncio

SERVER_URL = "http://127.0.0.1:8765"


async def test_layout_guest_mode_and_resizing():
    """
    E2E Verification for:
    1. Zero Login Wall & Guest Mode: Immediate access to notebook, files, and code execution.
    2. Edge-to-Edge Layout: 100% available horizontal space utilization without unnecessary margins.
    3. Draggable Resizing Panels: Left and Right vertical divider dragging with localStorage persistence.
    4. Guest vs Private Workspace: Visual badges, dismissible public notice banner.
    5. Seamless Transition: Non-intrusive sign-in modal, private workspace isolation, and clean sign-out.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda msg: (
            console_errors.append(msg.text) if msg.type == "error" else None,
            print(f"[BROWSER {msg.type}]: {msg.text}") if msg.type in ("error", "warning") else None
        ))

        # 1. Zero Login Wall: Navigate to Studio
        response = await page.goto(f"{SERVER_URL}/", wait_until="networkidle")
        assert response.status == 200, f"Expected 200, got {response.status}"

        # Ensure no full-page blocking login wall is present
        auth_modal = page.locator('[data-testid="auth-modal"]')
        assert await auth_modal.count() == 0, "Auth modal should NOT block guest access on load"

        # 2. Verify Guest Mode indicators
        # Public workspace indicator in Navbar
        public_badge = await page.wait_for_selector('[data-testid="workspace-indicator-public"]', timeout=8000)
        assert public_badge is not None
        badge_text = await public_badge.text_content()
        assert "Guest Mode" in badge_text and "Public Workspace" in badge_text

        # Dismissible Guest Privacy Notice Banner
        guest_banner = await page.wait_for_selector('[data-testid="guest-privacy-banner"]', timeout=5000)
        assert guest_banner is not None
        banner_text = await guest_banner.text_content()
        assert "public workspace" in banner_text.lower()

        # Sign In button visible in Navbar
        signin_btn = await page.wait_for_selector('[data-testid="signin-button"]', timeout=5000)
        assert signin_btn is not None

        # 3. Verify Edge-to-Edge Layout (No 960px constriction)
        # Wait for notebook editor
        editor_elem = await page.wait_for_selector('textarea', timeout=8000)
        assert editor_elem is not None

        # Measure width of center editor container
        center_box = await page.evaluate("""() => {
            const el = document.querySelector('textarea').closest('.cell-container') || document.querySelector('textarea').parentElement;
            return {
                width: el ? el.getBoundingClientRect().width : 0,
                parentWidth: el && el.parentElement ? el.parentElement.getBoundingClientRect().width : 0
            };
        }""")
        print(f"Center Editor Cell Width: {center_box['width']}px, Parent Width: {center_box['parentWidth']}px")
        # On a 1400px wide screen with 280px sidebar, width should easily exceed 1000px (far wider than old 960px limit)
        assert center_box["width"] > 950, f"Expected width > 950px, got {center_box['width']}px"

        # 4. Test Left Panel Resizing via Draggable Divider
        left_resizer = await page.wait_for_selector('[data-testid="left-resizer"]', timeout=5000)
        assert left_resizer is not None

        resizer_box = await left_resizer.bounding_box()
        assert resizer_box is not None

        # Drag left divider from current position (around 280px) to 400px (drag by +120px)
        start_x = resizer_box["x"] + resizer_box["width"] / 2
        start_y = resizer_box["y"] + 200
        target_x = start_x + 120

        await page.mouse.move(start_x, start_y)
        await page.mouse.down()
        await page.mouse.move(target_x, start_y, steps=10)
        await page.mouse.up()
        await asyncio.sleep(0.5)

        # Check localStorage persistence
        saved_left_width = await page.evaluate("() => localStorage.getItem('pcs_left_sidebar_width')")
        print(f"Resized Left Sidebar Width in localStorage: {saved_left_width}")
        assert saved_left_width is not None
        assert int(saved_left_width) >= 350, f"Expected left width >= 350, got {saved_left_width}"

        # 5. Test Right Sidebar Expansion and Draggable Resizer
        toggle_right_btn = await page.wait_for_selector('button[title="Expand File Editor"]', timeout=5000)
        await toggle_right_btn.click()
        await asyncio.sleep(0.5)

        # Right resizer should now be present
        right_resizer = await page.wait_for_selector('[data-testid="right-resizer"]', timeout=5000)
        assert right_resizer is not None

        r_resizer_box = await right_resizer.bounding_box()
        assert r_resizer_box is not None

        # Drag right divider 80px to the left (making right panel wider)
        r_start_x = r_resizer_box["x"] + r_resizer_box["width"] / 2
        r_start_y = r_resizer_box["y"] + 200
        r_target_x = r_start_x - 80

        await page.mouse.move(r_start_x, r_start_y)
        await page.mouse.down()
        await page.mouse.move(r_target_x, r_start_y, steps=10)
        await page.mouse.up()
        await asyncio.sleep(0.5)

        saved_right_width = await page.evaluate("() => localStorage.getItem('pcs_right_sidebar_width')")
        print(f"Resized Right Sidebar Width in localStorage: {saved_right_width}")
        assert saved_right_width is not None
        assert int(saved_right_width) >= 450, f"Expected right width >= 450, got {saved_right_width}"

        # Close right sidebar
        collapse_right_btn = await page.wait_for_selector('button[title="Collapse File Editor"]', timeout=5000)
        await collapse_right_btn.click()
        await asyncio.sleep(0.3)

        # 6. Test Guest Code Execution
        code_textarea = await page.wait_for_selector("textarea.code-cell-editor", timeout=5000)
        assert code_textarea is not None
        await code_textarea.click()
        await code_textarea.fill('print("Guest Execution Output: 500")')
        await code_textarea.press("Control+Enter")
        await asyncio.sleep(2.0)

        # Verify output rendered
        cell_output = await page.wait_for_selector("pre:has-text('Guest Execution Output: 500')", timeout=10000)
        assert cell_output is not None
        print("Guest code execution verified successfully!")

        # 7. Test Guest-to-User Transition
        # Click Sign In button in Navbar
        await signin_btn.click()
        await asyncio.sleep(0.5)

        # Auth modal is now visible
        await page.wait_for_selector('[data-testid="auth-modal"]', timeout=4000)

        # Switch to "Create Account"
        create_acc_link = page.locator("text=Create Account")
        await create_acc_link.click()
        await asyncio.sleep(0.3)

        # Fill registration form
        unique_email = f"e2e_student_{int(time.time())}@example.com"
        await page.locator('[data-testid="auth-modal"] input[type="text"]').fill("E2E Test User")
        await page.locator('[data-testid="auth-modal"] input[type="email"]').fill(unique_email)
        await page.locator('[data-testid="auth-modal"] input[type="password"]').fill("TestPassword123!")

        await page.locator('[data-testid="auth-modal"] button[type="submit"]').click()
        await asyncio.sleep(3.0)

        modal_count = await page.locator('[data-testid="auth-modal"]').count()
        if modal_count > 0:
            modal_text = await page.locator('[data-testid="auth-modal"]').text_content()
            print("AUTH MODAL ERROR/CONTENT:", modal_text)

        # Verify Auth modal closed
        assert modal_count == 0, f"Auth modal did not close: {modal_text if modal_count > 0 else ''}"

        # Verify Navbar switched to Private Workspace
        private_badge = await page.wait_for_selector('[data-testid="workspace-indicator-private"]', timeout=6000)
        assert private_badge is not None
        priv_text = await private_badge.text_content()
        assert "Signed In" in priv_text and "Private Workspace" in priv_text

        # Guest notice banner should no longer be rendered
        assert await page.locator('[data-testid="guest-privacy-banner"]').count() == 0

        # User name and Sign out button appear
        assert await page.locator("text=E2E Test User").count() > 0
        signout_btn = page.locator("text=Sign out")
        assert await signout_btn.count() > 0

        # 8. Test Logout Transition back to Guest Mode
        await signout_btn.click()
        await asyncio.sleep(1.5)

        # Navbar should switch back to Public Guest Mode
        reverted_badge = await page.wait_for_selector('[data-testid="workspace-indicator-public"]', timeout=6000)
        assert reverted_badge is not None
        rev_text = await reverted_badge.text_content()
        assert "Guest Mode" in rev_text and "Public Workspace" in rev_text

        # Sign In button reappears
        assert await page.locator('[data-testid="signin-button"]').count() > 0

        # Capture screenshot for artifact evidence
        screenshot_path = "storage/e2e_layout_guest_verified.png"
        os.makedirs("storage", exist_ok=True)
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to {screenshot_path}")

        await browser.close()
        print("\n>>> ALL E2E LAYOUT, GUEST MODE & RESIZING TESTS PASSED SUCCESSFULLY! <<<")

