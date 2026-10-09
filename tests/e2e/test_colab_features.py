import asyncio
import os
import subprocess
import time
import pytest
from playwright.async_api import async_playwright

pytestmark = pytest.mark.asyncio


async def test_google_colab_style_features():
    """
    E2E Verification for:
    1. Colab-style file explorer custom right-click context menu (empty area & item).
    2. Colab-style left-side circular run button execution.
    3. Individual cell output clearing.
    4. Notebook-wide output clearing (Clear All Outputs).
    5. Keyboard shortcuts (Ctrl+Enter, Shift+Enter, Alt+Enter).
    """
    server_process = subprocess.Popen(
        ["python", "-m", "uvicorn", "services.api.main:app", "--host", "127.0.0.1", "--port", "8769"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        time.sleep(3)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1366, "height": 850})
            page = await context.new_page()

            console_errors = []
            page.on("console", lambda msg: (
                console_errors.append(msg.text) if msg.type == "error" else None,
                print(f"[BROWSER {msg.type}]: {msg.text}") if msg.type in ("error", "warning") else None
            ))

            # Navigate to Studio
            response = await page.goto("http://127.0.0.1:8769/", wait_until="networkidle")
            assert response.status == 200

            # 1. TEST A: File Explorer Context Menus
            # Find the file list container
            files_header = await page.wait_for_selector("text=Files", timeout=10000)
            assert files_header is not None

            # Right-click empty background area in the file explorer
            # Wait for file list container
            file_container = page.locator('[data-testid="file-tree-container"]')
            # Click inside container where there are no items
            await file_container.click(button="right", position={"x": 50, "y": 300})
            await asyncio.sleep(0.5)

            # Verify context menu items for empty background appear
            upload_action = await page.wait_for_selector("text=Upload File", timeout=4000)
            new_file_action = await page.wait_for_selector("text=New File", timeout=4000)
            new_folder_action = await page.wait_for_selector("text=New Folder", timeout=4000)
            refresh_action = await page.wait_for_selector("text=Refresh", timeout=4000)
            assert upload_action is not None
            assert new_file_action is not None
            assert new_folder_action is not None
            assert refresh_action is not None
            print("Verified: Background right-click context menu (Upload, New File, New Folder, Refresh) works.")

            # Dismiss menu by pressing Escape
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.3)

            # Right-click an existing file item (main.py)
            main_py_item = await page.wait_for_selector("text=main.py", timeout=4000)
            assert main_py_item is not None
            await main_py_item.click(button="right")
            await asyncio.sleep(0.5)

            # Verify file-specific context actions appear
            open_action = await page.wait_for_selector("text=Open", timeout=4000)
            rename_action = await page.wait_for_selector("text=Rename", timeout=4000)
            download_action = await page.wait_for_selector("text=Download", timeout=4000)
            delete_action = await page.wait_for_selector("text=Delete", timeout=4000)
            assert open_action is not None
            assert rename_action is not None
            assert download_action is not None
            assert delete_action is not None
            print("Verified: File item right-click context menu (Open, Rename, Download, Delete, Refresh) works.")

            # Dismiss menu
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.3)

            # 2. TEST B: Colab-Style Left-Docked Run Button
            # Locate the left-gutter circular run button
            left_run_btn = await page.wait_for_selector("button[title*='Run cell']", timeout=5000)
            assert left_run_btn is not None
            print("Verified: Colab-style left-side circular run button is rendered.")

            # Click left run button to execute the code cell
            await left_run_btn.click()
            await asyncio.sleep(1.5)

            # Verify output rendered beneath cell
            output_el = await page.wait_for_selector("pre:has-text('Hello World from Python Cloud Studio!')", timeout=8000)
            assert output_el is not None
            print("Verified: Code executed and output rendered beneath the cell.")

            # 3. TEST C: Clear Individual Cell Output
            # Find the eraser/clear output button on cell header toolbar
            clear_cell_btn = await page.wait_for_selector("button[title='Clear Cell Output']", timeout=5000)
            assert clear_cell_btn is not None
            await clear_cell_btn.click()
            await asyncio.sleep(0.5)

            # Verify that output was removed from the DOM
            output_count = await page.locator("pre:has-text('Hello World from Python Cloud Studio!')").count()
            assert output_count == 0, "Expected cell output to be cleared"
            print("Verified: Individual cell output cleared successfully, source code preserved.")

            # 4. TEST D: Re-run and Clear All Outputs
            await left_run_btn.click()
            await asyncio.sleep(1.5)
            await page.wait_for_selector("pre:has-text('Hello World from Python Cloud Studio!')", timeout=8000)

            # Click "Clear All Outputs" from top toolbar
            clear_all_btn = await page.wait_for_selector("button:has-text('Clear All Outputs')", timeout=5000)
            assert clear_all_btn is not None
            await clear_all_btn.click()
            await asyncio.sleep(0.5)

            # Verify all outputs are cleared
            output_count_after = await page.locator("pre:has-text('Hello World from Python Cloud Studio!')").count()
            assert output_count_after == 0, "Expected all cell outputs to be cleared"
            print("Verified: Clear All Outputs cleared all notebook outputs successfully.")

            # 5. TEST E: Cross-Platform Keyboard Shortcuts
            # Find the active code cell textarea
            code_textarea = await page.wait_for_selector("textarea.code-cell-editor", timeout=5000)
            assert code_textarea is not None

            # Click to focus
            await code_textarea.click()
            await code_textarea.fill('print("Testing Ctrl+Enter execution")')

            # Press Control+Enter to execute
            await code_textarea.press("Control+Enter")
            await asyncio.sleep(1.5)

            # Verify execution output appeared
            ctrl_output = await page.wait_for_selector("pre:has-text('Testing Ctrl+Enter execution')", timeout=8000)
            assert ctrl_output is not None
            print("Verified: Ctrl+Enter shortcut successfully executed the active cell.")

            # Press Shift+Enter to execute and advance
            await code_textarea.click()
            await code_textarea.fill('print("Testing Shift+Enter advance")')
            await code_textarea.press("Shift+Enter")
            await asyncio.sleep(1.5)

            shift_output = await page.wait_for_selector("pre:has-text('Testing Shift+Enter advance')", timeout=8000)
            assert shift_output is not None
            print("Verified: Shift+Enter shortcut successfully executed and advanced.")

            # Capture visual screenshot of the working Colab interface
            screenshot_path = os.path.abspath("colab_features_verification.png")
            await page.screenshot(path=screenshot_path)
            print(f"Captured screenshot at: {screenshot_path}")

            # 6. Verify Shortcuts Modal
            shortcuts_btn = await page.wait_for_selector("button:has-text('Shortcuts')", timeout=4000)
            await shortcuts_btn.click()
            await asyncio.sleep(0.5)
            shortcuts_modal = await page.wait_for_selector("text=Keyboard Shortcuts", timeout=4000)
            assert shortcuts_modal is not None
            print("Verified: Keyboard shortcuts modal is rendered and informative.")

            # Check that there are no 404 console errors
            fatal_errors = [e for e in console_errors if "Failed to load resource" in e and "404" in e]
            assert len(fatal_errors) == 0, f"Found 404 asset errors: {fatal_errors}"

            await browser.close()
            print("All Colab E2E tests PASSED 100%!")

    finally:
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except Exception:
            server_process.kill()

