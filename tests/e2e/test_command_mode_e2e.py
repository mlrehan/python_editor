"""
Colab-style command and edit modes in the notebook:
  - page load does not put the caret in a cell; typing letters in a cell is never intercepted
  - Esc leaves the editor (command mode); Enter edits again; Up/Down (and k/j) move the selection
  - A / B insert a cell above / below, D D deletes and selects the neighbour, M / Y convert the type
  - the Run button keeps the caret in the editor; clicking a cell header selects the cell
  - Run cells above / Run this and below (cell menu and Ctrl+F8 / Ctrl+F10)

Requires a running server (PCS_E2E_URL, default http://127.0.0.1:8765).
"""
import os
import re

import pytest
from playwright.async_api import async_playwright, expect

pytestmark = pytest.mark.asyncio

SERVER_URL = os.environ.get("PCS_E2E_URL", "http://127.0.0.1:8765")


async def open_notebook(p):
    browser = await p.chromium.launch(headless=True)
    page = await (await browser.new_context(viewport={"width": 1440, "height": 900})).new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    await page.goto(SERVER_URL, wait_until="networkidle")
    await expect(page.locator('[data-testid="kernel-status"][data-status="idle"]')).to_be_visible(timeout=60000)
    return browser, page, errors


def editor_of(cell):
    return cell.locator('textarea[data-testid="code-cell-editor"]')


async def focused_cell_id(page):
    return await page.evaluate("""() => { const a = document.activeElement;
        const c = a && a.closest('[data-testid="notebook-cell"]'); return c ? c.dataset.cellId : null; }""")


async def focused_is_cell(page):
    return await page.evaluate("() => document.activeElement?.dataset?.testid === 'notebook-cell'")


async def add_cells(page, sources):
    """Adds code cells at the end with the given sources; returns their ids."""
    ids = []
    cells = page.get_by_test_id("notebook-cell")
    for src in sources:
        n = await cells.count()
        await page.get_by_role("button", name="Add Code Cell").click()
        await editor_of(cells.nth(n)).fill(src)
        ids.append(await cells.nth(n).get_attribute("data-cell-id"))
    return ids


async def test_load_does_not_steal_focus_and_letters_are_typed():
    async with async_playwright() as p:
        browser, page, errors = await open_notebook(p)
        tag = await page.evaluate("document.activeElement.tagName")
        assert tag in ("BODY", "HTML"), f"focus went to {tag} on load"
        (cid,) = await add_cells(page, [""])
        cell = page.locator(f'[data-cell-id="{cid}"]')
        await editor_of(cell).click()
        await page.keyboard.type("abdmyjk = 1")
        await expect(editor_of(cell)).to_have_value("abdmyjk = 1")
        await expect(page.get_by_test_id("notebook-editor-container")).to_have_attribute("data-mode", "edit")
        assert not errors, errors
        await browser.close()


async def test_command_mode_keys():
    async with async_playwright() as p:
        browser, page, errors = await open_notebook(p)
        container = page.get_by_test_id("notebook-editor-container")
        cells = page.get_by_test_id("notebook-cell")
        first, second = await add_cells(page, ["x = 1", "y = 2"])
        start = await cells.count()

        # Esc: command mode, the cell itself has the focus
        await editor_of(page.locator(f'[data-cell-id="{second}"]')).click()
        await page.keyboard.press("Escape")
        await expect(container).to_have_attribute("data-mode", "command")
        assert await focused_is_cell(page) and await focused_cell_id(page) == second
        await expect(page.locator(f'[data-cell-id="{second}"]')).to_have_class(re.compile("is-selected"))

        # Up / Down move the selection
        await page.keyboard.press("ArrowUp")
        assert await focused_cell_id(page) == first
        await page.keyboard.press("j")
        assert await focused_cell_id(page) == second

        # B: new cell below, selected, nothing typed into it
        await page.keyboard.press("b")
        await expect(cells).to_have_count(start + 1)
        new_id = await focused_cell_id(page)
        assert new_id not in (first, second) and await focused_is_cell(page)
        assert await cells.nth(start).get_attribute("data-cell-id") == new_id
        await expect(editor_of(cells.nth(start))).to_have_value("")

        # A: new cell above the selection
        await page.keyboard.press("a")
        await expect(cells).to_have_count(start + 2)
        above = await focused_cell_id(page)
        assert await cells.nth(start).get_attribute("data-cell-id") == above

        # D D: deleted, the neighbour is selected (keyboard not lost)
        await page.keyboard.press("d")
        await page.keyboard.press("d")
        await expect(cells).to_have_count(start + 1)
        await expect(page.locator(f'[data-cell-id="{above}"]')).to_have_count(0)
        assert await focused_is_cell(page) and await focused_cell_id(page) == new_id

        # A single D does nothing
        await page.keyboard.press("d")
        await page.wait_for_timeout(900)
        await page.keyboard.press("d")
        await expect(cells).to_have_count(start + 1)

        # M / Y: markdown and back
        target = page.locator(f'[data-cell-id="{new_id}"]')
        await page.keyboard.press("m")
        await expect(target).to_have_attribute("data-cell-type", "markdown")
        await page.keyboard.press("y")
        await expect(target).to_have_attribute("data-cell-type", "code")

        # Enter: edit mode, caret in the editor; typing goes into the cell
        await page.keyboard.press("Enter")
        await expect(container).to_have_attribute("data-mode", "edit")
        await page.keyboard.type("z = 3")
        await expect(editor_of(target)).to_have_value("z = 3")

        # Clean up
        await page.keyboard.press("Escape")
        for cid in (new_id, second, first):
            await page.locator(f'[data-cell-id="{cid}"]').get_by_title("Delete Cell").click()
        await expect(cells).to_have_count(start - 2)
        assert not errors, errors
        await browser.close()


async def test_run_button_keeps_caret_and_header_click_selects():
    async with async_playwright() as p:
        browser, page, errors = await open_notebook(p)
        (cid,) = await add_cells(page, ["print('kept focus')"])
        cell = page.locator(f'[data-cell-id="{cid}"]')
        await editor_of(cell).click()
        await page.keyboard.press("End")
        await cell.get_by_test_id("cell-run-btn").click()
        await expect(cell.get_by_test_id("cell-output-container")).to_contain_text("kept focus", timeout=60000)
        assert await page.evaluate("document.activeElement.dataset.testid") == "code-cell-editor"
        assert await focused_cell_id(page) == cid
        await page.keyboard.type("  # more")
        await expect(editor_of(cell)).to_have_value("print('kept focus')  # more")

        # Clicking the header (not a control) selects the cell in command mode
        box = await cell.locator(".cell-header").first.bounding_box()
        await page.mouse.click(box["x"] + box["width"] * 0.4, box["y"] + box["height"] / 2)
        await expect(page.get_by_test_id("notebook-editor-container")).to_have_attribute("data-mode", "command")
        assert await focused_is_cell(page) and await focused_cell_id(page) == cid
        await cell.get_by_title("Delete Cell").click()
        assert not errors, errors
        await browser.close()


async def test_run_above_and_below():
    async with async_playwright() as p:
        browser, page, errors = await open_notebook(p)
        ids = await add_cells(page, ["print('one')", "print('two')", "print('three')"])
        cell = lambda i: page.locator(f'[data-cell-id="{ids[i]}"]')
        out = lambda i: cell(i).get_by_test_id("cell-output-container")

        # Menu: run the cells above the last one
        await cell(2).get_by_test_id("cell-more-btn").click()
        await page.get_by_role("menuitem", name="Run cells above").click()
        await expect(out(1)).to_contain_text("two", timeout=60000)
        await expect(out(0)).to_contain_text("one")
        await expect(cell(2).get_by_test_id("cell-output-container")).to_have_count(0)

        # Ctrl+F10 on the middle one: runs it and everything below
        await editor_of(cell(1)).fill("print('TWO')")
        await editor_of(cell(1)).click()
        await page.keyboard.press("Control+F10")
        await expect(out(2)).to_contain_text("three", timeout=60000)
        await expect(out(1)).to_contain_text("TWO")

        for cid in reversed(ids):
            await page.locator(f'[data-cell-id="{cid}"]').get_by_title("Delete Cell").click()
        assert not errors, errors
        await browser.close()
