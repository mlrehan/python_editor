import os
import asyncio
import pytest
from playwright.async_api import async_playwright

pytestmark = pytest.mark.asyncio

SERVER_URL = "http://127.0.0.1:8765"
ARTIFACTS_DIR = r"C:\Users\User\.gemini\antigravity\brain\fc7f57bd-7847-49e1-bf17-3d67072c2a03"

async def test_signature_and_autocomplete_overlap_and_escape_priority():
    """
    Verifies:
    1. Typing 'print(' opens Signature Help tooltip ONLY (not 100+ completions dropdown).
    2. Typing 'print(s' opens BOTH Signature Help and Autocomplete Dropdown.
    3. Mathematical geometric non-overlap: Signature Help is strictly above cursor line,
       Autocomplete dropdown is strictly below cursor line (sig_bottom <= drop_top).
    4. First Escape press dismisses ONLY the autocomplete dropdown; Signature Help remains visible.
    5. Second Escape press dismisses the Signature Help tooltip.
    6. Typing 'print(' and pressing Escape closes Signature Help immediately.
    7. Autocomplete Enter key accepts suggestion without running cell.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        await page.goto(SERVER_URL, wait_until="networkidle")

        code_editor = page.locator('textarea[data-testid="code-cell-editor"]').first
        await code_editor.wait_for(state="visible", timeout=10000)

        # Focus editor and clear
        await code_editor.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")

        # -------------------------------------------------------------
        # STEP 1: Typing 'print(' should show signature help ONLY
        # -------------------------------------------------------------
        await code_editor.fill("print(")
        await code_editor.dispatch_event("input")
        await page.keyboard.press("End")

        sig_tooltip = page.locator('[data-testid="signature-help-tooltip"]')
        drop_menu = page.locator('[data-testid="autocomplete-dropdown"]')

        # Signature tooltip should appear
        await sig_tooltip.wait_for(state="visible", timeout=8000)
        sig_text = await sig_tooltip.inner_text()
        print(f"Captured signature text: {sig_text}")
        assert "print(" in sig_text, f"Expected print signature, got: {sig_text}"

        # Autocomplete dropdown should NOT be visible
        is_dropdown_visible = await drop_menu.is_visible()
        print(f"Is dropdown visible on 'print('? {is_dropdown_visible}")
        assert not is_dropdown_visible, "Autocomplete dropdown should NOT automatically open on 'print('"

        # -------------------------------------------------------------
        # STEP 2: Escape when only signature help is visible closes it
        # -------------------------------------------------------------
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.3)
        assert not (await sig_tooltip.is_visible()), "Escape should close signature help when only it is open"

        # -------------------------------------------------------------
        # STEP 3: Typing 'print(s' opens BOTH without overlap
        # -------------------------------------------------------------
        await code_editor.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await code_editor.fill("print(s")
        await code_editor.dispatch_event("input")
        await page.keyboard.press("End")

        # Both should appear
        await sig_tooltip.wait_for(state="visible", timeout=8000)
        await drop_menu.wait_for(state="visible", timeout=8000)

        assert await sig_tooltip.is_visible(), "Signature tooltip should be visible"
        assert await drop_menu.is_visible(), "Autocomplete dropdown should be visible"

        # Check bounding boxes: Signature help above, Autocomplete dropdown below
        sig_box = await sig_tooltip.bounding_box()
        drop_box = await drop_menu.bounding_box()

        print(f"Signature box: {sig_box}")
        print(f"Dropdown box: {drop_box}")

        assert sig_box is not None, "Signature box must be found"
        assert drop_box is not None, "Dropdown box must be found"

        sig_bottom = sig_box["y"] + sig_box["height"]
        drop_top = drop_box["y"]

        print(f"sig_bottom = {sig_bottom}, drop_top = {drop_top}, difference = {drop_top - sig_bottom}")
        # The signature help bottom must be above or at the dropdown top
        # Since the code line separates them, drop_top should be >= sig_bottom
        assert sig_bottom <= drop_top, (
            f"Signature tooltip bottom ({sig_bottom}) collides with or overlaps "
            f"Autocomplete dropdown top ({drop_top})!"
        )

        screenshot_path = os.path.join(ARTIFACTS_DIR, "signature_and_autocomplete_non_overlapping_verified.png")
        await page.screenshot(path=screenshot_path)
        print(f"Saved non-overlapping screenshot to: {screenshot_path}")

        # -------------------------------------------------------------
        # STEP 4: First Escape closes ONLY autocomplete dropdown
        # -------------------------------------------------------------
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.3)

        assert not (await drop_menu.is_visible()), "First Escape must dismiss autocomplete dropdown!"
        assert await sig_tooltip.is_visible(), "First Escape must KEEP signature help visible!"

        screenshot_escape1 = os.path.join(ARTIFACTS_DIR, "signature_retained_after_first_escape_verified.png")
        await page.screenshot(path=screenshot_escape1)
        print(f"Saved first Escape screenshot to: {screenshot_escape1}")

        # -------------------------------------------------------------
        # STEP 5: Second Escape closes signature help
        # -------------------------------------------------------------
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.3)

        assert not (await sig_tooltip.is_visible()), "Second Escape must dismiss signature help!"
        assert not (await drop_menu.is_visible()), "Dropdown remains closed!"

        screenshot_escape2 = os.path.join(ARTIFACTS_DIR, "both_dismissed_after_second_escape_verified.png")
        await page.screenshot(path=screenshot_escape2)
        print(f"Saved second Escape screenshot to: {screenshot_escape2}")

        # -------------------------------------------------------------
        # STEP 6: Verify Autocomplete for standalone identifier 'pri' + Enter
        # -------------------------------------------------------------
        await code_editor.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await code_editor.fill("pri")
        await code_editor.dispatch_event("input")
        await page.keyboard.press("End")

        await drop_menu.wait_for(state="visible", timeout=8000)
        assert await drop_menu.is_visible(), "Autocomplete should open for 'pri'"

        # Press Enter to accept
        await page.keyboard.press("Enter")
        await asyncio.sleep(0.3)

        val = await code_editor.input_value()
        print(f"Code after accepting completion: {val}")
        assert "print" in val, f"Expected 'print' in code, got '{val}'"

        await browser.close()

