import os
import asyncio
import pytest
from playwright.async_api import async_playwright

pytestmark = pytest.mark.asyncio

SERVER_URL = "http://127.0.0.1:8765"
ARTIFACTS_DIR = r"C:\Users\User\.gemini\antigravity\brain\fc7f57bd-7847-49e1-bf17-3d67072c2a03"

async def test_theme_switching_system_dark_light():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # 1. Navigate to Web Dashboard
        response = await page.goto(SERVER_URL, wait_until="networkidle")
        assert response.status == 200

        # Wait for navbar and theme button
        theme_btn = page.locator('[data-testid="theme-toggle-btn"]')
        await theme_btn.wait_for(state="visible", timeout=10000)

        # Ensure cell editor is visible
        code_editor = page.locator('textarea[data-testid="code-cell-editor"]').first
        await code_editor.wait_for(state="visible", timeout=10000)

        # ========================================================
        # TEST A: SWITCH TO LIGHT THEME
        # ========================================================
        await theme_btn.click()
        light_option = page.locator('[data-testid="theme-option-light"]')
        await light_option.wait_for(state="visible", timeout=3000)
        await light_option.click()
        await asyncio.sleep(0.5)

        # Verify html attribute
        html_theme = await page.evaluate("document.documentElement.getAttribute('data-theme')")
        assert html_theme == "light", f"Expected html data-theme to be 'light', got '{html_theme}'"

        # Verify computed styles for Light theme
        navbar = page.locator('header')
        navbar_bg = await navbar.evaluate("el => window.getComputedStyle(el).backgroundColor")
        assert navbar_bg == "rgb(255, 255, 255)", f"Expected Light navbar background to be white, got {navbar_bg}"

        body_bg = await page.evaluate("window.getComputedStyle(document.body).backgroundColor")
        assert body_bg in ["rgb(248, 250, 252)", "rgb(255, 255, 255)"], f"Expected Light body background, got {body_bg}"

        # Capture Screenshot for Light Theme
        light_screenshot = os.path.join(ARTIFACTS_DIR, "theme_light_verified.png")
        await page.screenshot(path=light_screenshot)
        print(f"Captured Light Theme screenshot: {light_screenshot}")

        # ========================================================
        # TEST B: AUTOCOMPLETE DROPDOWN IN LIGHT THEME
        # ========================================================
        await code_editor.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await code_editor.fill("import numpy as np\nnp.")
        await code_editor.dispatch_event("input")
        await page.keyboard.press("Control+Space")

        dropdown = page.locator('[data-testid="autocomplete-dropdown"]')
        await dropdown.wait_for(state="visible", timeout=8000)
        assert await dropdown.is_visible()

        dropdown_bg = await dropdown.evaluate("el => window.getComputedStyle(el).backgroundColor")
        assert dropdown_bg == "rgb(255, 255, 255)", f"Expected Light dropdown bg to be white, got {dropdown_bg}"

        # Capture Autocomplete in Light Theme Screenshot
        auto_light_screenshot = os.path.join(ARTIFACTS_DIR, "autocomplete_light_theme_verified.png")
        await page.screenshot(path=auto_light_screenshot)
        print(f"Captured Autocomplete in Light Theme screenshot: {auto_light_screenshot}")

        # Close dropdown with Escape
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.2)

        # ========================================================
        # TEST C: SWITCH TO DARK THEME
        # ========================================================
        await theme_btn.click()
        dark_option = page.locator('[data-testid="theme-option-dark"]')
        await dark_option.wait_for(state="visible", timeout=3000)
        await dark_option.click()
        await asyncio.sleep(0.5)

        html_theme_dark = await page.evaluate("document.documentElement.getAttribute('data-theme')")
        assert html_theme_dark == "dark", f"Expected html data-theme to be 'dark', got '{html_theme_dark}'"

        navbar_dark_bg = await navbar.evaluate("el => window.getComputedStyle(el).backgroundColor")
        assert navbar_dark_bg == "rgb(15, 23, 42)", f"Expected Dark navbar bg to be #0f172a, got {navbar_dark_bg}"

        # Capture Screenshot for Dark Theme
        dark_screenshot = os.path.join(ARTIFACTS_DIR, "theme_dark_verified.png")
        await page.screenshot(path=dark_screenshot)
        print(f"Captured Dark Theme screenshot: {dark_screenshot}")

        # ========================================================
        # TEST D: SWITCH TO SYSTEM THEME
        # ========================================================
        await theme_btn.click()
        system_option = page.locator('[data-testid="theme-option-system"]')
        await system_option.wait_for(state="visible", timeout=3000)
        await system_option.click()
        await asyncio.sleep(0.5)

        saved_theme = await page.evaluate("localStorage.getItem('pcs_theme')")
        assert saved_theme == "system", f"Expected localStorage pcs_theme to be 'system', got '{saved_theme}'"

        await browser.close()


async def test_vertical_cell_resizing_and_persistence():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        await page.goto(SERVER_URL, wait_until="networkidle")

        code_editor = page.locator('textarea[data-testid="code-cell-editor"]').first
        await code_editor.wait_for(state="visible", timeout=10000)

        # Identify the resize handle
        resize_handle = page.locator('[data-testid="cell-resize-handle"]').first
        await resize_handle.wait_for(state="visible", timeout=10000)
        assert await resize_handle.is_visible(), "Cell vertical resize handle must be visible"

        # Check initial height of code editor
        initial_box = await code_editor.bounding_box()
        assert initial_box is not None
        initial_height = initial_box["height"]
        print(f"Initial Code Editor Height: {initial_height}px")

        # ========================================================
        # 1. DRAG RESIZE HANDLE DOWNWARD (+120px)
        # ========================================================
        handle_box = await resize_handle.bounding_box()
        assert handle_box is not None
        start_x = handle_box["x"] + handle_box["width"] / 2
        start_y = handle_box["y"] + handle_box["height"] / 2

        await page.mouse.move(start_x, start_y)
        await page.mouse.down()
        await page.mouse.move(start_x, start_y + 120, steps=10)
        await page.mouse.up()
        await asyncio.sleep(0.3)

        new_box = await code_editor.bounding_box()
        assert new_box is not None
        expanded_height = new_box["height"]
        print(f"Expanded Code Editor Height: {expanded_height}px")
        assert expanded_height > initial_height + 80, f"Expected height > {initial_height + 80}, got {expanded_height}"

        # Capture screenshot of downward resize
        downward_screenshot = os.path.join(ARTIFACTS_DIR, "cell_resize_downward_verified.png")
        await page.screenshot(path=downward_screenshot)
        print(f"Captured downward resize screenshot: {downward_screenshot}")

        # ========================================================
        # 2. VERIFY HEIGHT PERSISTENCE ACROSS CELL EXECUTION
        # ========================================================
        await code_editor.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await code_editor.fill("print('Height persistence verification')")
        # Run cell with Ctrl+Enter
        await page.keyboard.press("Control+Enter")

        # Wait for execution output
        output_el = page.locator('div.cell-wrapper pre').first
        await output_el.wait_for(state="visible", timeout=10000)

        # Check height after execution
        post_exec_box = await code_editor.bounding_box()
        assert post_exec_box is not None
        print(f"Post-Execution Code Editor Height: {post_exec_box['height']}px")
        assert abs(post_exec_box["height"] - expanded_height) < 15, "Cell custom height must persist across cell execution"

        # ========================================================
        # 3. DOUBLE-CLICK TO RESET TO AUTO-FIT
        # ========================================================
        new_handle_box = await resize_handle.bounding_box()
        assert new_handle_box is not None
        h_x = new_handle_box["x"] + new_handle_box["width"] / 2
        h_y = new_handle_box["y"] + new_handle_box["height"] / 2

        await page.mouse.dblclick(h_x, h_y)
        await asyncio.sleep(0.3)

        reset_box = await code_editor.bounding_box()
        assert reset_box is not None
        print(f"Reset Code Editor Height: {reset_box['height']}px")
        assert reset_box["height"] < expanded_height - 50, "Double click should reset custom height to auto-fit"

        # Capture screenshot of reset height
        reset_screenshot = os.path.join(ARTIFACTS_DIR, "cell_resize_reset_verified.png")
        await page.screenshot(path=reset_screenshot)
        print(f"Captured reset height screenshot: {reset_screenshot}")

        await browser.close()
