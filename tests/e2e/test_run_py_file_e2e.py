"""
Running a .py file from the notebook, as a new user would:
  - a new .py file opens in the editor with a green Run button
  - Run saves unsaved edits first, adds a "%run file.py" cell at the end of the notebook and runs it
  - the file's functions are then available in other cells
  - "Run in notebook" in the Files menu works for files in folders and with spaces in their names
  - on a phone the editor closes so the output is visible

Requires a running server (PCS_E2E_URL, default http://127.0.0.1:8765).
"""
import os
import re

import pytest
from playwright.async_api import async_playwright, expect

pytestmark = pytest.mark.asyncio

SERVER_URL = os.environ.get("PCS_E2E_URL", "http://127.0.0.1:8765")


async def open_studio(p, width=1440, height=900):
    browser = await p.chromium.launch(headless=True)
    page = await (await browser.new_context(viewport={"width": width, "height": height})).new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    await page.goto(SERVER_URL, wait_until="networkidle")
    await expect(page.locator('[data-testid="kernel-status"][data-status="idle"]')).to_be_visible(timeout=60000)
    return browser, page, errors


async def api(page, method, path, body=None):
    return await page.evaluate(
        """async ([m, p, b]) => { const r = await fetch('/api/v1' + p, { method: m,
             headers: { 'X-Guest-Token': localStorage.getItem('pcs_guest_token'), 'Content-Type': 'application/json' },
             body: b ? JSON.stringify(b) : undefined });
           let j = null; try { j = await r.json(); } catch (e) {} return [r.status, j]; }""",
        [method, path, body],
    )


def last_cell(page):
    return page.get_by_test_id("notebook-cell").last


async def test_new_py_file_runs_from_the_editor():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        cells = page.get_by_test_id("notebook-cell")
        before = await cells.count()

        # A new user creates a file with the Files panel
        await page.get_by_title(re.compile("New File")).click()
        await page.get_by_role("dialog").get_by_role("textbox").fill("greeting.py")
        await page.get_by_role("dialog").get_by_role("button", name="Confirm").click()
        run = page.get_by_test_id("file-run-btn")
        await expect(run).to_be_visible()
        await expect(run).to_have_text("Run")

        # Writes code (not saved yet) and clicks Run
        editor = page.locator(".cm-content").first
        await editor.click()
        await page.keyboard.press("Control+a")
        await page.keyboard.type("def greet(who):\n")
        await page.keyboard.type("return f'Hi {who}!'\n")
        await page.keyboard.press("Shift+Tab")
        await page.keyboard.type("print(greet('new user'))")
        await expect(page.locator(".fe-status")).to_contain_text("Unsaved")
        await run.click()

        await expect(cells).to_have_count(before + 1)
        await expect(last_cell(page).locator('textarea[data-testid="code-cell-editor"]')).to_have_value("%run greeting.py")
        await expect(last_cell(page).get_by_test_id("cell-output-container")).to_contain_text("Hi new user!", timeout=60000)
        await expect(page.locator(".fe-status")).to_contain_text("Saved")
        st, saved = await api(page, "GET", "/files/read?path=greeting.py")
        assert "print(greet('new user'))" in saved["content"]

        # Its function is available in the notebook
        await page.get_by_role("button", name="Add Code Cell").click()
        await last_cell(page).locator('textarea[data-testid="code-cell-editor"]').fill("greet('notebook')")
        await last_cell(page).get_by_test_id("cell-run-btn").click()
        await expect(last_cell(page).get_by_test_id("cell-output-container")).to_contain_text("Hi notebook!", timeout=60000)

        for _ in range(2):
            await last_cell(page).get_by_title("Delete Cell").click()
        await api(page, "DELETE", "/files?path=greeting.py")
        assert not errors, errors
        await browser.close()


async def test_run_in_notebook_from_the_files_menu():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        await api(page, "POST", "/files/folder", {"path": "my scripts"})
        await api(page, "POST", "/files/write", {"path": "my scripts/data report.py",
                                                 "content": "import pandas as pd\nprint('rows:', len(pd.read_csv('sample_data.csv')))\n"})
        await page.evaluate("window.dispatchEvent(new CustomEvent('pcs-refresh-files'))")
        await page.locator('[data-testid="file-tree-item"][data-path="my scripts"]').click()
        item = page.locator('[data-testid="file-tree-item"][data-path="my scripts/data report.py"]')
        await item.click(button="right")
        await page.get_by_test_id("file-menu-run").click()
        await expect(last_cell(page).locator('textarea[data-testid="code-cell-editor"]')).to_have_value('%run "my scripts/data report.py"')
        await expect(last_cell(page).get_by_test_id("cell-output-container")).to_contain_text(re.compile(r"rows: \d+"), timeout=60000)

        # Not offered for other files
        await page.locator('[data-testid="file-tree-item"][data-path="README.md"]').click(button="right")
        await expect(page.get_by_test_id("file-menu-run")).to_have_count(0)
        await page.keyboard.press("Escape")

        await last_cell(page).get_by_title("Delete Cell").click()
        await api(page, "DELETE", "/files?path=my scripts")
        assert not errors, errors
        await browser.close()


async def test_on_a_phone_the_output_is_shown():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, width=390, height=844)
        await api(page, "POST", "/files/write", {"path": "phone.py", "content": "print('from the phone')\n"})
        await page.get_by_test_id("left-sidebar-toggle").click()
        await page.locator('[data-testid="file-tree-item"][data-path="phone.py"]').dblclick()
        await page.get_by_test_id("file-run-btn").click()
        await expect(page.get_by_test_id("file-run-btn")).to_have_count(0)  # the editor made way for the notebook
        output = last_cell(page).get_by_test_id("cell-output-container")
        await expect(output).to_contain_text("from the phone", timeout=60000)
        await expect(last_cell(page)).to_be_in_viewport()
        await last_cell(page).get_by_title("Delete Cell").click()
        await api(page, "DELETE", "/files?path=phone.py")
        assert not errors, errors
        await browser.close()


async def test_page_is_revalidated_so_new_releases_load():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        res = await page.request.get(SERVER_URL + "/")
        assert res.ok and res.headers.get("cache-control") == "no-cache"
        await browser.close()
