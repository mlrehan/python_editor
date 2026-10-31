"""
Browser tests for the responsive workspace:
  - the sidebar toggle is visible, inside the top bar and touch-sized at every width (320px to 2560px)
  - below 1024px the file sidebar is an overlay drawer painted above its backdrop; it closes with the
    backdrop, Escape, the toggle, and after opening a file; desktop keeps the docked, resizable sidebar
  - phones: the file editor fills the workspace; several files can be opened (tap), switched with tabs
    or the open-files switcher, edited without losing unsaved text, cursor or scroll; tabs close individually
  - the mobile keyboard (a height-only resize) does not close the editor
  - narrow notebooks move secondary cell actions into a menu; code still runs and shows output
  - no horizontal page overflow at any width

Requires a running server (default http://127.0.0.1:8765, override with PCS_E2E_URL).
"""
import os

import pytest
from playwright.async_api import async_playwright, expect

import cm_helpers as cm

pytestmark = pytest.mark.asyncio

SERVER_URL = os.environ.get("PCS_E2E_URL", "http://127.0.0.1:8765")
ALL_WIDTHS = [320, 360, 375, 414, 480, 600, 768, 900, 1024, 1280, 1440, 1920, 2560]


async def open_studio(p, width, height=800, touch=False):
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": width, "height": height}, has_touch=touch, is_mobile=touch)
    page = await context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    await page.goto(SERVER_URL, wait_until="networkidle")
    await page.locator('textarea[data-testid="code-cell-editor"]').first.wait_for(state="visible", timeout=15000)
    return browser, page, errors


async def no_page_overflow(page):
    return await page.evaluate("document.documentElement.scrollWidth - innerWidth") == 0


async def settle(page):
    """Wait for open/close animations (drawers slide in) before measuring."""
    await page.evaluate("Promise.all(document.getAnimations().map(a => a.finished))")


def tree_item(page, name):
    return page.locator(f'[data-testid="file-tree-item"][data-path$="{name}"]').first


@pytest.mark.parametrize("width", ALL_WIDTHS)
async def test_sidebar_toggle_always_visible_and_reachable(width):
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, width)
        toggle = page.get_by_test_id("left-sidebar-toggle")
        await expect(toggle).to_be_visible()
        box = await toggle.bounding_box()
        header = await page.locator("header.pcs-topbar").bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= width
        assert box["y"] >= header["y"] and box["y"] + box["height"] <= header["y"] + header["height"]
        assert box["width"] >= 28 and box["height"] >= 28
        # Nothing covers it: the toggle itself receives a press at its centre
        hit = await page.evaluate(
            "([x, y]) => !!document.elementFromPoint(x, y)?.closest('[data-testid=left-sidebar-toggle]')",
            [box["x"] + box["width"] / 2, box["y"] + box["height"] / 2],
        )
        assert hit
        assert await no_page_overflow(page)
        assert not errors, errors
        await browser.close()


@pytest.mark.parametrize("width,height", [(375, 740), (768, 1024)])
async def test_compact_sidebar_is_a_drawer_above_its_backdrop(width, height):
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, width, height, touch=True)
        assert await page.get_by_test_id("left-drawer").count() == 0, "drawer starts closed on small screens"
        notebook_before = await page.get_by_test_id("notebook-editor-container").bounding_box()

        toggle = page.get_by_test_id("left-sidebar-toggle")
        await toggle.tap()
        drawer = page.get_by_test_id("left-drawer")
        await expect(drawer).to_be_visible()
        await expect(page.get_by_test_id("mobile-left-backdrop")).to_be_visible()
        await settle(page)
        # Overlay: the notebook keeps its size
        assert await page.get_by_test_id("notebook-editor-container").bounding_box() == notebook_before
        # The drawer is painted above the backdrop (it used to sit underneath it)
        d = await drawer.bounding_box()
        on_top = await page.evaluate(
            "([x, y]) => !!document.elementFromPoint(x, y)?.closest('[data-testid=left-drawer]')",
            [d["x"] + d["width"] / 2, d["y"] + d["height"] / 2],
        )
        assert on_top, "drawer must not be covered by its backdrop"
        assert d["x"] + d["width"] <= width - 40, "a strip of the backdrop stays visible to tap"

        # Close: backdrop tap, Escape, toggle
        await page.touchscreen.tap(width - 12, d["y"] + d["height"] / 2)
        await expect(drawer).to_have_count(0)
        await toggle.tap()
        await expect(drawer).to_be_visible()
        await page.keyboard.press("Escape")
        await expect(drawer).to_have_count(0)
        await toggle.tap()
        await expect(drawer).to_be_visible()
        await toggle.tap()
        await expect(drawer).to_have_count(0)
        assert await no_page_overflow(page)
        assert not errors, errors
        await browser.close()


async def test_desktop_keeps_docked_resizable_sidebar():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, 1440, 900)
        await expect(page.get_by_test_id("workspace-row")).to_have_attribute("data-layout", "desktop")
        if await page.get_by_test_id("left-resizer").count() == 0:
            await page.get_by_test_id("left-sidebar-toggle").click()
        await expect(page.get_by_test_id("left-resizer")).to_be_visible()
        assert await page.get_by_test_id("left-drawer").count() == 0
        assert await page.get_by_test_id("mobile-left-backdrop").count() == 0

        await tree_item(page, "main.py").dblclick()
        panel = page.get_by_test_id("right-file-editor-panel")
        await expect(panel).to_have_attribute("data-layout", "docked")
        await expect(page.get_by_test_id("right-resizer")).to_be_visible()
        # Three panels side by side
        nb = await page.get_by_test_id("notebook-editor-container").bounding_box()
        pb = await panel.bounding_box()
        assert nb["width"] > 300 and pb["x"] >= nb["x"] + nb["width"] - 1
        assert not errors, errors
        await browser.close()


async def test_phone_multi_file_editing_preserves_state():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, 375, 740, touch=True)
        toggle = page.get_by_test_id("left-sidebar-toggle")

        # Tap opens a file; the drawer closes and the editor fills the workspace
        await toggle.tap()
        await tree_item(page, "main.py").tap()
        panel = page.get_by_test_id("right-file-editor-panel")
        await expect(panel).to_be_visible()
        await expect(panel).to_have_attribute("data-layout", "fullscreen")
        await expect(page.get_by_test_id("left-drawer")).to_have_count(0)
        row = await page.get_by_test_id("workspace-row").bounding_box()
        pb = await panel.bounding_box()
        assert abs(pb["width"] - row["width"]) < 1 and abs(pb["height"] - row["height"]) < 1
        await expect(page.get_by_test_id("active-file-indicator")).to_contain_text("main.py")

        # Edit main.py at a known spot (unsaved), remember cursor and scroll
        await cm.wait_for_editor(page)
        original = await cm.doc(page)
        await cm.set_cursor(page, 0)
        await page.keyboard.type("x_mobile = 1")
        await page.keyboard.press("Enter")
        edited = await cm.doc(page)
        assert edited == "x_mobile = 1\n" + original
        await expect(page.get_by_test_id("dirty-indicator-main.py")).to_be_visible()
        caret = await cm.selection(page)

        # The sidebar toggle stays usable above the full-screen editor: open a second file
        await toggle.tap()
        await expect(page.get_by_test_id("left-drawer")).to_be_visible()
        await tree_item(page, "README.md").tap()
        await expect(page.get_by_test_id("left-drawer")).to_have_count(0)
        await expect(page.get_by_test_id("active-file-indicator")).to_contain_text("README.md")
        await expect(page.get_by_test_id("file-tab-README.md")).to_have_attribute("aria-selected", "true")
        await expect(page.get_by_test_id("file-tab-main.py")).to_have_attribute("aria-selected", "false")

        # Switch back through the open-files switcher: unsaved text and cursor are intact
        await page.get_by_test_id("open-files-switcher").tap()
        menu = page.get_by_test_id("open-files-menu")
        await expect(menu).to_be_visible()
        mb = await menu.bounding_box()
        assert mb["x"] >= 0 and mb["x"] + mb["width"] <= 375, "switcher menu stays on screen"
        await menu.get_by_test_id("open-file-option-main.py").locator(".fe-switcher-select").tap()
        await expect(page.get_by_test_id("active-file-indicator")).to_contain_text("main.py")
        assert await cm.doc(page) == edited
        assert await cm.selection(page) == caret
        await expect(page.get_by_test_id("dirty-indicator-main.py")).to_be_visible()

        # Tabs switch too; closing one tab keeps the other
        await page.get_by_test_id("file-tab-README.md").tap()
        await expect(page.get_by_test_id("active-file-indicator")).to_contain_text("README.md")
        await page.get_by_test_id("close-tab-README.md").tap()
        await expect(page.get_by_test_id("file-tab-README.md")).to_have_count(0)
        await expect(page.get_by_test_id("active-file-indicator")).to_contain_text("main.py")
        assert await cm.doc(page) == edited

        # The mobile keyboard only changes the height: the editor must stay open
        await page.set_viewport_size({"width": 375, "height": 420})
        await page.wait_for_timeout(300)
        await expect(panel).to_be_visible()
        await page.set_viewport_size({"width": 375, "height": 740})

        # Closing the dirty tab asks first; discard leaves the file on disk unchanged
        await page.get_by_test_id("close-tab-main.py").tap()
        await expect(page.get_by_test_id("unsaved-changes-modal")).to_be_visible()
        await page.get_by_test_id("modal-discard-changes-btn").tap()
        await expect(panel).to_have_count(0)
        assert await no_page_overflow(page)
        assert not errors, errors
        await browser.close()


async def test_file_editor_line_numbers_follow_scroll():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, 1280, 700)
        if await page.get_by_test_id("left-resizer").count() == 0:
            await page.get_by_test_id("left-sidebar-toggle").click()
        await tree_item(page, "main.py").dblclick()
        await cm.wait_for_editor(page)
        original = await cm.doc(page)
        # Taller than the editor (in memory only); scroll to the end: the last line and its number show
        await cm.set_doc(page, "\n".join(f"line_{i} = {i}" for i in range(1, 201)))
        await cm.set_cursor(page, len(await cm.doc(page)))
        await page.wait_for_timeout(200)
        last_line = page.locator(".cm-line", has_text="line_200 = 200")
        await expect(last_line).to_be_visible()
        number = page.locator(".cm-lineNumbers .cm-gutterElement", has_text="200").last
        await expect(number).to_be_visible()
        lb, nb = await last_line.bounding_box(), await number.bounding_box()
        assert abs(lb["y"] - nb["y"]) < 2, "line number aligned with its line"
        await cm.set_doc(page, original)
        assert not errors, errors
        await browser.close()


@pytest.mark.parametrize("width", [320, 375, 480])
async def test_narrow_notebook_cells_use_action_menu_and_still_run(width):
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, width, 800, touch=True)
        cells = page.get_by_test_id("notebook-cell")
        count = await cells.count()
        await page.get_by_role("button", name="Add Code Cell").tap()
        await expect(cells).to_have_count(count + 1)
        cell = cells.nth(count)
        editor = cell.locator('textarea[data-testid="code-cell-editor"]')
        await editor.fill("print('narrow', 6 * 7)")
        await page.keyboard.press("Escape")

        # Secondary actions are in the menu, run and delete stay visible
        await expect(cell.get_by_title("Move Cell Up")).to_be_hidden()
        await expect(cell.get_by_test_id("cell-run-btn")).to_be_visible()
        await expect(cell.get_by_title("Delete Cell")).to_be_visible()
        await cell.get_by_test_id("cell-more-btn").tap()
        menu = cell.get_by_test_id("cell-menu")
        await expect(menu).to_be_visible()
        mb = await menu.bounding_box()
        assert mb["x"] >= 0 and mb["x"] + mb["width"] <= width
        await menu.get_by_role("menuitem", name="Duplicate").tap()
        await expect(cells).to_have_count(count + 2)
        await cells.nth(count + 1).get_by_title("Delete Cell").tap()
        await expect(cells).to_have_count(count + 1)

        # Code editing and execution work at this width
        await cell.get_by_test_id("cell-run-btn").tap()
        await expect(cell.get_by_test_id("cell-output-container")).to_contain_text("narrow 42", timeout=30000)
        gutter, textarea = await cell.evaluate(
            """c => [c.querySelector('textarea[data-testid=code-cell-editor]').previousElementSibling, c.querySelector('textarea[data-testid=code-cell-editor]')]
                 .map(e => e.getBoundingClientRect().width)"""
        )
        assert textarea >= width * 0.55, f"code area too narrow: {textarea}px of {width}px"
        assert await no_page_overflow(page)
        await cell.get_by_title("Delete Cell").tap()
        assert not errors, errors
        await browser.close()


async def test_tablet_file_editor_is_a_drawer_over_the_notebook():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, 768, 1024, touch=True)
        await expect(page.get_by_test_id("workspace-row")).to_have_attribute("data-layout", "tablet")
        nb_before = await page.get_by_test_id("notebook-editor-container").bounding_box()
        await page.get_by_test_id("left-sidebar-toggle").tap()
        await tree_item(page, "main.py").tap()
        panel = page.get_by_test_id("right-file-editor-panel")
        await expect(panel).to_have_attribute("data-layout", "drawer")
        await settle(page)
        pb = await panel.bounding_box()
        assert pb["width"] <= 768 - 48 and pb["x"] + pb["width"] == pytest.approx(768, abs=1)
        assert await page.get_by_test_id("notebook-editor-container").bounding_box() == nb_before
        await page.get_by_test_id("mobile-right-backdrop").tap(position={"x": 10, "y": 200})
        await expect(panel).to_have_count(0)
        assert not errors, errors
        await browser.close()


@pytest.mark.parametrize("width", ALL_WIDTHS)
async def test_no_overflow_with_editor_open(width):
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, width, 800)
        if not await tree_item(page, "main.py").is_visible():
            await page.get_by_test_id("left-sidebar-toggle").click()
        await tree_item(page, "main.py").dblclick()
        await expect(page.get_by_test_id("right-file-editor-panel")).to_be_visible()
        await settle(page)
        assert await no_page_overflow(page)
        # Every control in the editor's tab bar and toolbar is inside the viewport
        outside = await page.evaluate(
            """() => [...document.querySelectorAll('.fe-tabs-bar button, .fe-toolbar button, .fe-toolbar a')]
                 .filter(e => e.offsetParent).map(e => e.getBoundingClientRect())
                 .filter(r => r.left < -0.5 || r.right > innerWidth + 0.5).length"""
        )
        assert outside == 0
        assert not errors, errors
        await browser.close()
