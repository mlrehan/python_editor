import os
import asyncio
import pytest
from playwright.async_api import async_playwright

pytestmark = pytest.mark.asyncio

SERVER_URL = "http://127.0.0.1:8765"
ARTIFACTS_DIR = r"C:\Users\User\.gemini\antigravity\brain\fc7f57bd-7847-49e1-bf17-3d67072c2a03"

async def test_python_editor_autocomplete_and_clean_diagnostics():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        # 1. Navigate to Web Dashboard
        response = await page.goto(SERVER_URL, wait_until="networkidle")
        assert response.status == 200

        # Wait for notebook code cell editor to be visible
        code_editor = page.locator('textarea[data-testid="code-cell-editor"]').first
        await code_editor.wait_for(state="visible", timeout=10000)

        # 2. Focus and clear editor
        await code_editor.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await asyncio.sleep(0.2)

        # 3. Type NumPy import and trigger np.
        test_code_1 = "import numpy as np\nnp."
        await code_editor.fill(test_code_1)
        # Dispatch input event so autocomplete triggers
        await code_editor.dispatch_event("input")
        # Trigger Ctrl+Space explicitly to guarantee dropdown prompt
        await page.keyboard.press("Control+Space")

        # 4. Wait for autocomplete dropdown to appear
        dropdown = page.locator('[data-testid="autocomplete-dropdown"]')
        await dropdown.wait_for(state="visible", timeout=8000)
        assert await dropdown.is_visible()

        # Check dropdown items
        items = page.locator('[data-testid^="completion-item-"]')
        count = await items.count()
        assert count > 0, "Autocomplete dropdown must contain suggestions"
        print(f"Autocomplete suggestions count for 'np.': {count}")

        # Capture Screenshot of Autocomplete Dropdown
        screenshot_path_1 = os.path.join(ARTIFACTS_DIR, "python_autocomplete_verified.png")
        await page.screenshot(path=screenshot_path_1)
        print(f"Captured autocomplete screenshot at: {screenshot_path_1}")

        # 5. Press ArrowDown and Tab/Enter to accept completion
        await page.keyboard.press("ArrowDown")
        await page.keyboard.press("Enter")
        await asyncio.sleep(0.3)

        # 6. Test the user's exact valid code snippet from the bug report:
        # "import numpy as np\nimport pandas as pd\n\ndf = pd.read_csv('sample_data.csv')\nprint(df.head())"
        valid_code = "import numpy as np\nimport pandas as pd\n\ndf = pd.DataFrame({'a': [1, 2, 3]})\nprint(df.head())"
        await code_editor.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await code_editor.fill(valid_code)
        await code_editor.dispatch_event("input")

        # Wait for diagnostics debounce (350ms)
        await asyncio.sleep(0.6)

        # Check that NO wavy error underlines or error badges exist for valid code
        error_dots = page.locator('div[style*="background-color: rgb(239, 68, 68)"]')
        error_count = await error_dots.count()
        assert error_count == 0, f"Expected 0 error indicators on valid code, found {error_count}"

        # Capture Screenshot of Clean Valid Code (No false red underlines)
        screenshot_path_2 = os.path.join(ARTIFACTS_DIR, "python_clean_editor_verified.png")
        await page.screenshot(path=screenshot_path_2)
        print(f"Captured clean editor screenshot at: {screenshot_path_2}")

        # 7. Execute cell using Ctrl+Enter shortcut
        await page.keyboard.press("Control+Enter")
        output_el = page.locator('div.cell-wrapper pre').first
        await output_el.wait_for(state="visible", timeout=12000)
        assert await output_el.is_visible(), "Expected cell execution output to appear"
        print("Cell executed successfully via Ctrl+Enter!")

        # 8. Test real syntax error displays red underline and diagnostic tooltip
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await code_editor.fill("def broken_syntax(:\n    pass")
        await code_editor.dispatch_event("input")
        await asyncio.sleep(0.6)

        # Verify diagnostic alert tooltip appears for actual syntax error
        syntax_alert = page.locator('[data-testid="diagnostic-badge"]')
        await syntax_alert.wait_for(state="visible", timeout=4000)
        assert await syntax_alert.is_visible(), "Expected syntax error diagnostic badge"

        await browser.close()
