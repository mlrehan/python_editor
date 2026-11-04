"""
Suggestion popup placement, scrolling and layering (Google Colab as the reference):
  - near the notebook toolbar, near the bottom of the window, after resizing and while scrolling, the
    suggestions stay next to the caret, fully visible, never under the toolbars or clipped by a cell
  - the mouse wheel / trackpad scrolls the list (not the notebook); outside it the notebook scrolls
  - hundreds of suggestions: arrow keys keep the selection in view
  - the selected suggestion's documentation is beside the list (inside it on a phone), scrollable,
    never covering the suggestions; the signature help never overlaps the suggestions

Requires a running server (PCS_E2E_URL, default http://127.0.0.1:8765) with numpy and pandas.
"""
import os

import pytest
from playwright.async_api import async_playwright, expect

pytestmark = pytest.mark.asyncio

SERVER_URL = os.environ.get("PCS_E2E_URL", "http://127.0.0.1:8765")
FILLER = "\n".join(f"value_{i} = {i}" for i in range(12))


async def open_studio(p, width=1440, height=900):
    browser = await p.chromium.launch(headless=True)
    page = await (await browser.new_context(viewport={"width": width, "height": height})).new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    await page.goto(SERVER_URL, wait_until="networkidle")
    await expect(page.locator('[data-testid="kernel-status"][data-status="idle"]')).to_be_visible(timeout=60000)
    return browser, page, errors


async def add_cells(page, sources):
    editors = []
    cells = page.get_by_test_id("notebook-cell")
    for src in sources:
        index = await cells.count()
        await page.get_by_role("button", name="Add Code Cell").click()
        # Pinned to this cell (".last" would follow whichever cell is last later on)
        editor = cells.nth(index).locator('textarea[data-testid="code-cell-editor"]')
        await editor.fill(src)
        editors.append(editor)
    await page.keyboard.press("Escape")
    return editors


async def rect(locator):
    return await locator.evaluate("el => { const r = el.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, left: r.left, right: r.right, height: r.height }; }")


async def visible_area(page):
    """The part of the window where code is shown: below the app bar and the notebook toolbar."""
    toolbar = await rect(page.get_by_test_id("notebook-sticky-toolbar"))
    viewport = page.viewport_size
    return toolbar["bottom"], viewport["height"], viewport["width"]


async def type_at_end(page, editor, text):
    await editor.click()
    await editor.press("Control+End")
    await page.keyboard.type(text)


async def assert_fully_visible_and_on_top(page, locator):
    box = await rect(locator)
    top, bottom, width = await visible_area(page)
    assert box["top"] >= top - 1, (box, top)
    assert box["bottom"] <= bottom + 1, (box, bottom)
    assert box["left"] >= 0 and box["right"] <= width + 1, box
    # Nothing covers it: the topmost element at its corners belongs to it
    covered = await locator.evaluate("""el => { const r = el.getBoundingClientRect();
        return [[r.left + 6, r.top + 6], [r.right - 6, r.top + 6], [r.left + 6, r.bottom - 6], [r.right - 6, r.bottom - 6]]
          .filter(([x, y]) => !el.contains(document.elementFromPoint(x, y))).length; }""")
    assert covered == 0, f"{covered} corner(s) covered"


async def poll(fn, check, timeout=3.0):
    """Waits until check(await fn()) holds; returns the last value."""
    import asyncio
    value = None
    for _ in range(int(timeout / 0.1)):
        value = await fn()
        if check(value):
            return value
        await asyncio.sleep(0.1)
    raise AssertionError(f"condition not met, last value: {value}")


def overlaps(a, b):
    return not (a["right"] <= b["left"] or b["right"] <= a["left"] or a["bottom"] <= b["top"] or b["bottom"] <= a["top"])


async def test_popup_near_the_toolbar_and_near_the_bottom():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, height=820)
        editors = await add_cells(page, ["import numpy as np\nimport pandas as pd\n" + FILLER, FILLER, FILLER])
        scroller = page.get_by_test_id("notebook-editor-container")
        dropdown = page.get_by_test_id("autocomplete-dropdown")

        # 1. Caret on a line just under the sticky notebook toolbar
        first = editors[0]
        await first.click()
        await first.evaluate("el => { el.focus(); el.setSelectionRange(0, 0); }")
        await page.keyboard.press("End")
        line_box = await rect(first)
        top, _, _ = await visible_area(page)
        await scroller.evaluate("(el, d) => el.scrollTop += d", line_box["top"] - top - 4)
        await page.keyboard.press("Enter")
        await page.keyboard.type("np.")
        await expect(dropdown).to_be_visible(timeout=10000)
        await assert_fully_visible_and_on_top(page, dropdown)
        assert await dropdown.get_attribute("data-placement") == "below"
        # The popup is not inside the cell (no scroll area or cell can clip it)
        assert await dropdown.evaluate("el => !el.closest('[data-testid=notebook-cell]')")
        await page.keyboard.press("Escape")

        # 2. Caret near the bottom of the window: it opens above the caret, still below the toolbar
        last = editors[-1]
        await last.click()
        await scroller.evaluate("el => el.scrollTop = el.scrollHeight")
        last_box = await rect(last)
        viewport_h = page.viewport_size["height"]
        await scroller.evaluate("(el, d) => el.scrollTop -= d", max(0, viewport_h - 60 - last_box["bottom"]))
        await last.evaluate("el => { el.focus(); el.setSelectionRange(el.value.length, el.value.length); }")
        await page.keyboard.press("Enter")
        await page.keyboard.type("pd.")
        await expect(dropdown).to_be_visible(timeout=10000)
        caret_line_bottom = (await rect(last))["bottom"]
        await assert_fully_visible_and_on_top(page, dropdown)
        box = await rect(dropdown)
        if box["top"] < caret_line_bottom - 30:
            assert await dropdown.get_attribute("data-placement") == "above"
        assert not errors, errors
        await browser.close()


async def test_wheel_scrolls_the_list_and_keys_keep_the_selection_visible():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        (editor,) = await add_cells(page, ["import numpy as np\n"])
        scroller = page.get_by_test_id("notebook-editor-container")
        await type_at_end(page, editor, "np.")
        dropdown = page.get_by_test_id("autocomplete-dropdown")
        listbox = page.get_by_test_id("autocomplete-list")
        await expect(dropdown).to_be_visible(timeout=10000)
        await expect(listbox.locator('[role="option"]').nth(100)).to_be_attached(timeout=10000)  # hundreds of suggestions

        notebook_before = await scroller.evaluate("el => el.scrollTop")
        box = await rect(listbox)
        await page.mouse.move((box["left"] + box["right"]) / 2, (box["top"] + box["bottom"]) / 2)
        # A list that opens under a still pointer keeps the first suggestion selected
        await page.keyboard.press("Escape")
        await expect(dropdown).to_have_count(0)
        await page.keyboard.press("Backspace")
        await page.keyboard.type(".")
        await expect(dropdown).to_be_visible(timeout=10000)
        await expect(listbox.locator('[role="option"]').first).to_have_attribute("aria-selected", "true")
        # Mouse wheel
        await page.mouse.wheel(0, 400)
        await poll(lambda: listbox.evaluate("el => el.scrollTop"), lambda v: v > 100)
        # Trackpad: many small deltas, both directions
        for _ in range(10):
            await page.mouse.wheel(0, -12)
        after_trackpad = await listbox.evaluate("el => el.scrollTop")
        assert 100 < after_trackpad + 120 and after_trackpad < 400
        # Reaching the end of the list does not scroll the notebook behind it
        await page.mouse.wheel(0, 100000)
        await page.wait_for_timeout(300)
        assert await scroller.evaluate("el => el.scrollTop") == notebook_before
        await expect(dropdown).to_be_visible()

        # Keyboard: the selected suggestion stays in view, far down the list
        for _ in range(60):
            await page.keyboard.press("ArrowDown")
        selected = listbox.locator('[role="option"][aria-selected="true"]')
        sel_box, list_box = await rect(selected), await rect(listbox)
        assert sel_box["top"] >= list_box["top"] - 1 and sel_box["bottom"] <= list_box["bottom"] + 1
        label = (await selected.get_attribute("data-testid")).removeprefix("completion-item-")
        await page.keyboard.press("Enter")
        assert (await editor.input_value()).endswith(f"np.{label}")

        # Popup closed: the wheel scrolls the notebook as usual
        await add_cells(page, [FILLER, FILLER, FILLER])
        nb = await rect(scroller)
        await page.mouse.move((nb["left"] + nb["right"]) / 2, (nb["top"] + nb["bottom"]) / 2)
        before = await scroller.evaluate("el => el.scrollTop")
        await page.mouse.wheel(0, 300)
        await poll(lambda: scroller.evaluate("el => el.scrollTop"), lambda v: v > before)
        assert not errors, errors
        await browser.close()


async def test_documentation_beside_the_list_and_signature_apart():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        (editor,) = await add_cells(page, ["import pandas as pd\n"])
        await type_at_end(page, editor, "pd.read_exc")
        dropdown = page.get_by_test_id("autocomplete-dropdown")
        await expect(dropdown).to_be_visible(timeout=10000)
        details = page.get_by_test_id("completion-details")
        await expect(details).to_be_visible(timeout=10000)
        await expect(details).to_contain_text("read_excel")
        assert await details.get_attribute("data-side") in ("right", "left")
        d_box, l_box = await rect(details), await rect(dropdown)
        assert not overlaps(d_box, l_box), (d_box, l_box)
        await assert_fully_visible_and_on_top(page, details)
        # Long documentation scrolls on its own
        assert await details.evaluate("el => el.scrollHeight > el.clientHeight")
        await details.hover()
        await page.mouse.wheel(0, 300)
        await poll(lambda: details.evaluate("el => el.scrollTop"), lambda v: v > 0)
        await expect(dropdown).to_be_visible()

        # Inside a call: signature help and suggestions never overlap
        await page.keyboard.press("Escape")
        await editor.fill("import pandas as pd\n")
        await type_at_end(page, editor, "pd.read_csv('data.csv', se")
        signature = page.get_by_test_id("signature-help-tooltip")
        await expect(signature).to_be_visible(timeout=10000)
        await expect(dropdown).to_be_visible(timeout=10000)
        assert not overlaps(await rect(signature), await rect(dropdown))
        await assert_fully_visible_and_on_top(page, dropdown)
        await page.keyboard.press("Escape")
        await expect(dropdown).to_have_count(0)
        await page.keyboard.press("Escape")
        await expect(signature).to_have_count(0)
        assert not errors, errors
        await browser.close()


async def test_resize_and_scroll_while_open():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        # A short first cell, so its caret stays on screen in the smaller window
        editors = await add_cells(page, ["import numpy as np\nx = 1", FILLER, FILLER, FILLER])
        await page.get_by_test_id("notebook-editor-container").evaluate("el => el.scrollTop = el.scrollHeight")
        await editors[0].scroll_into_view_if_needed()
        await type_at_end(page, editors[0], "\nnp.")
        dropdown = page.get_by_test_id("autocomplete-dropdown")
        await expect(dropdown).to_be_visible(timeout=10000)

        # Resize: still beside the caret and fully visible
        await page.set_viewport_size({"width": 900, "height": 600})
        await page.wait_for_timeout(300)
        await assert_fully_visible_and_on_top(page, dropdown)

        # Scroll the notebook a little: the popup moves with the caret
        scroller = page.get_by_test_id("notebook-editor-container")
        before, editor_before = await rect(dropdown), await rect(editors[0])
        placement = await dropdown.get_attribute("data-placement")
        await scroller.evaluate("el => el.scrollTop -= 30")
        await page.wait_for_timeout(250)
        if await dropdown.get_attribute("data-placement") == placement:
            after, editor_after = await rect(dropdown), await rect(editors[0])
            moved = editor_after["top"] - editor_before["top"]
            assert moved != 0 and abs((after["top"] - before["top"]) - moved) <= 2, (before, after, moved)
        await assert_fully_visible_and_on_top(page, dropdown)

        # Caret scrolled out of view: the popup waits, hidden (it never floats over the toolbars)
        await scroller.evaluate("el => el.scrollTop = el.scrollHeight")
        await page.wait_for_timeout(250)
        assert (await rect(editors[0]))["bottom"] < (await visible_area(page))[0]
        await expect(dropdown).to_have_count(0)
        # Scrolled back: it is shown again next to the caret
        await scroller.evaluate("el => el.scrollTop = 0")
        await expect(dropdown).to_be_visible()
        await assert_fully_visible_and_on_top(page, dropdown)
        assert not errors, errors
        await browser.close()


async def test_phone_width_documentation_inside_the_list():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, width=390, height=844)
        (editor,) = await add_cells(page, ["import pandas as pd\n"])
        await type_at_end(page, editor, "pd.read_exc")
        dropdown = page.get_by_test_id("autocomplete-dropdown")
        await expect(dropdown).to_be_visible(timeout=10000)
        details = dropdown.get_by_test_id("completion-details")
        await expect(details).to_be_visible(timeout=10000)
        await assert_fully_visible_and_on_top(page, dropdown)
        # The suggestions keep room: at least one full row is visible above the documentation
        option = dropdown.locator('[role="option"]').first
        o_box, d_box = await rect(option), await rect(details)
        assert o_box["bottom"] <= d_box["top"] + 1
        assert not errors, errors
        await browser.close()
