"""
Browser tests for notebook editing and execution controls:
  - Ctrl+/ toggles comments on the current line and on selected lines
  - Stop (toolbar and per-cell) and Ctrl+C interrupt a running infinite loop without a page refresh
  - when an interrupt cannot stop the code, a restart prompt recovers the kernel
  - runtime errors (ZeroDivisionError) do not block later executions; duplicate runs are ignored
  - the notebook toolbar (+ Code, + Text, Clear All Outputs, Shortcuts) stays visible while scrolling
  - the signature tooltip can be scrolled, entered, selected/copied, and stays inside the visible area
  - the Shortcuts dialog lists every shortcut; Ctrl+S saves, Ctrl+B toggles the sidebar, Tab/Shift+Tab indent

Requires a running server (default http://127.0.0.1:8765, override with PCS_E2E_URL).
"""
import os

import pytest
from playwright.async_api import async_playwright, expect

pytestmark = pytest.mark.asyncio

SERVER_URL = os.environ.get("PCS_E2E_URL", "http://127.0.0.1:8765")


async def open_notebook(p, width=1440, height=900):
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": width, "height": height})
    await context.grant_permissions(["clipboard-read", "clipboard-write"], origin=SERVER_URL)
    page = await context.new_page()
    await page.goto(SERVER_URL, wait_until="networkidle")
    await page.locator('textarea[data-testid="code-cell-editor"]').first.wait_for(state="visible", timeout=15000)
    await expect(page.locator('[data-testid="kernel-status"][data-status="idle"]')).to_be_visible(timeout=30000)
    return browser, page


async def new_code_cell(page, code=""):
    editors = page.locator('textarea[data-testid="code-cell-editor"]')
    index = await editors.count()
    await page.get_by_role("button", name="Add Code Cell").click()
    # Pin to this cell's index: .last would follow later-added cells
    editor = editors.nth(index)
    await editor.wait_for(state="visible")
    await editor.fill(code)
    await page.keyboard.press("Escape")  # close any autocomplete popup opened by the input
    return editor


def cell_of(editor):
    return editor.locator('xpath=ancestor::div[@data-testid="notebook-cell"][1]')


async def run_cell(page, editor):
    await editor.focus()
    await page.keyboard.press("Control+Enter")


async def wait_until_running(editor, running=True, timeout=30000):
    label = "Stop execution" if running else "Run cell"
    await expect(cell_of(editor).locator('[data-testid="cell-run-btn"]')).to_have_attribute(
        "aria-label", label, timeout=timeout
    )


async def output_text(editor):
    outputs = cell_of(editor).locator('[data-testid="cell-output-container"]')
    return await outputs.inner_text() if await outputs.count() else ""


async def test_ctrl_slash_toggles_comments():
    async with async_playwright() as p:
        browser, page = await open_notebook(p)
        editor = await new_code_cell(page, "x = 1\ndef f():\n    return x\n\nprint(f())")

        # No selection: current line only
        await editor.focus()
        await editor.evaluate("el => el.setSelectionRange(2, 2)")
        await page.keyboard.press("Control+Slash")
        assert await editor.input_value() == "# x = 1\ndef f():\n    return x\n\nprint(f())"
        await page.keyboard.press("Control+Slash")
        assert await editor.input_value() == "x = 1\ndef f():\n    return x\n\nprint(f())"

        # Multi-line selection: commented at common indentation, blank line untouched, toggles back
        await editor.evaluate("el => el.setSelectionRange(6, el.value.length)")
        await page.keyboard.press("Control+Slash")
        assert await editor.input_value() == "x = 1\n# def f():\n#     return x\n\n# print(f())"
        selection = await editor.evaluate("el => el.value.substring(el.selectionStart, el.selectionEnd)")
        assert selection == "# def f():\n#     return x\n\n# print(f())", "selection should keep covering the lines"
        await page.keyboard.press("Control+Slash")
        assert await editor.input_value() == "x = 1\ndef f():\n    return x\n\nprint(f())"

        # The commented code still runs normally
        await page.keyboard.press("Control+Slash")
        await run_cell(page, editor)
        await wait_until_running(editor, running=False)
        assert "Error" not in await output_text(editor)
        await browser.close()


async def test_stop_button_interrupts_infinite_loop_and_kernel_keeps_working():
    async with async_playwright() as p:
        browser, page = await open_notebook(p)
        loop = await new_code_cell(page, "n = 0\nwhile True:\n    n += 1")
        await run_cell(page, loop)
        await wait_until_running(loop)
        await page.wait_for_timeout(1500)

        await page.get_by_test_id("stop-execution-btn").click()
        await wait_until_running(loop, running=False, timeout=15000)
        assert "KeyboardInterrupt" in await output_text(loop)

        # The kernel survived (variables kept) and runs the next cell
        after = await new_code_cell(page, "print('still alive', n > 0)")
        await run_cell(page, after)
        await wait_until_running(after, running=False)
        assert "still alive True" in await output_text(after)
        await browser.close()


async def test_cell_stop_button_and_ctrl_c_interrupt():
    async with async_playwright() as p:
        browser, page = await open_notebook(p)
        loop = await new_code_cell(page, "while True:\n    pass")

        # Per-cell button turns into Stop while running
        await run_cell(page, loop)
        await wait_until_running(loop)
        await page.wait_for_timeout(1000)
        await cell_of(loop).locator('[data-testid="cell-run-btn"]').click()
        await wait_until_running(loop, running=False, timeout=15000)
        assert "KeyboardInterrupt" in await output_text(loop)

        # Ctrl+C with nothing selected interrupts
        await run_cell(page, loop)
        await wait_until_running(loop)
        await page.wait_for_timeout(1000)
        await loop.evaluate("el => { el.focus(); el.setSelectionRange(0, 0); }")
        await page.keyboard.press("Control+c")
        await wait_until_running(loop, running=False, timeout=15000)
        assert "KeyboardInterrupt" in await output_text(loop)
        await browser.close()


async def test_ctrl_c_with_selection_copies_instead_of_interrupting():
    async with async_playwright() as p:
        browser, page = await open_notebook(p)
        loop = await new_code_cell(page, "import time\nfor i in range(40):\n    time.sleep(0.25)\nprint('finished')")
        await run_cell(page, loop)
        await wait_until_running(loop)

        other = await new_code_cell(page, "copy_me = 1")
        await other.evaluate("el => { el.focus(); el.setSelectionRange(0, 4); }")
        await page.keyboard.press("Control+c")
        assert await page.evaluate("navigator.clipboard.readText()") == "copy"
        await page.wait_for_timeout(1500)
        # Still running: Ctrl+C with a selection must not interrupt
        await wait_until_running(loop, running=True, timeout=1000)
        await page.get_by_test_id("stop-execution-btn").click()
        await wait_until_running(loop, running=False, timeout=15000)
        await browser.close()


async def test_recovery_prompt_restarts_kernel_when_interrupt_is_ignored():
    async with async_playwright() as p:
        browser, page = await open_notebook(p)
        stubborn = await new_code_cell(
            page, "import signal\nsignal.signal(signal.SIGINT, signal.SIG_IGN)\nwhile True:\n    pass"
        )
        await run_cell(page, stubborn)
        await wait_until_running(stubborn)
        await page.wait_for_timeout(1000)

        await page.get_by_test_id("stop-execution-btn").click()
        prompt = page.get_by_test_id("kernel-recovery-prompt")
        await expect(prompt).to_be_visible(timeout=15000)
        assert "clears all variables" in await prompt.inner_text()

        await page.get_by_test_id("recovery-restart-btn").click()
        await wait_until_running(stubborn, running=False, timeout=45000)
        await expect(prompt).to_be_hidden(timeout=5000)

        check = await new_code_cell(page, "print('fresh kernel ok')")
        await run_cell(page, check)
        await wait_until_running(check, running=False, timeout=30000)
        assert "fresh kernel ok" in await output_text(check)
        await browser.close()


async def test_runtime_error_does_not_block_next_execution_and_duplicate_runs_ignored():
    async with async_playwright() as p:
        browser, page = await open_notebook(p)
        bad = await new_code_cell(page, "1 / 0")
        await run_cell(page, bad)
        await wait_until_running(bad, running=False)
        assert "ZeroDivisionError" in await output_text(bad)

        good = await new_code_cell(page, "import time\ntime.sleep(2)\nprint('ran once')")
        await run_cell(page, good)
        await wait_until_running(good)
        # Pressing run again while it is running must not start a second execution
        await good.focus()
        await page.keyboard.press("Control+Enter")
        await wait_until_running(good, running=False, timeout=15000)
        await page.wait_for_timeout(1500)
        assert (await output_text(good)).count("ran once") == 1
        await browser.close()


@pytest.mark.parametrize("width,height", [(1440, 900), (900, 640)])
async def test_notebook_toolbar_stays_visible_while_scrolling(width, height):
    async with async_playwright() as p:
        browser, page = await open_notebook(p, width, height)
        for i in range(12):
            await new_code_cell(page, f"# filler cell {i}\n" + "x = 1\n" * 4)

        container = page.get_by_test_id("notebook-editor-container")
        toolbar = page.get_by_test_id("notebook-sticky-toolbar")
        await container.evaluate("el => el.scrollTo(0, el.scrollHeight)")
        # Focusing a cell used to scroll the whole layout row under the guest banner
        await page.locator('textarea[data-testid="code-cell-editor"]').last.focus()
        await page.wait_for_timeout(300)

        box = await toolbar.bounding_box()
        container_box = await container.bounding_box()
        assert box and container_box
        assert abs(box["y"] - container_box["y"]) <= 1, "toolbar should be pinned to the top of the notebook"
        assert container_box["y"] + container_box["height"] <= height + 1, "notebook bottom is clipped"
        banner = page.get_by_test_id("guest-privacy-banner")
        if await banner.count():
            b = await banner.bounding_box()
            assert b["y"] + b["height"] <= box["y"] + 1, "guest banner overlaps the toolbar"
        # Nothing (scrolled content, banners) covers the toolbar buttons
        for name in ["Code", "Text", "Clear All Outputs", "Shortcuts"]:
            button = toolbar.get_by_role("button", name=name).first
            b = await button.bounding_box()
            hit = await page.evaluate(
                "([x, y]) => document.elementFromPoint(x, y)?.closest('[data-testid=notebook-sticky-toolbar]') !== null",
                [b["x"] + b["width"] / 2, b["y"] + b["height"] / 2],
            )
            assert hit, f"{name} is covered by notebook content"
        # Toolbar still works while stuck: + Code adds a cell
        before = await page.locator('textarea[data-testid="code-cell-editor"]').count()
        await toolbar.get_by_role("button", name="Code").first.click()
        assert await page.locator('textarea[data-testid="code-cell-editor"]').count() == before + 1
        await browser.close()


@pytest.mark.parametrize("width,height", [(1440, 900), (1000, 620)])
async def test_signature_tooltip_is_scrollable_selectable_and_visible(width, height):
    async with async_playwright() as p:
        browser, page = await open_notebook(p, width, height)
        editor = await new_code_cell(page, "import pandas as pd\n")
        await editor.focus()
        await editor.evaluate("el => el.setSelectionRange(el.value.length, el.value.length)")
        await page.keyboard.type("pd.read_csv(", delay=40)

        tooltip = page.get_by_test_id("signature-help-tooltip")
        await expect(tooltip).to_be_visible(timeout=15000)
        await page.keyboard.press("Escape")  # leave only the tooltip if completions opened
        if not await tooltip.is_visible():
            await page.keyboard.type(" ", delay=40)
            await expect(tooltip).to_be_visible(timeout=10000)

        # A quick signature can appear before the documented one: wait for the long read_csv docs
        await page.wait_for_function(
            "() => { const el = document.querySelector('[data-testid=signature-help-tooltip]');"
            " return !!el && el.scrollHeight > el.clientHeight + 50; }",
            timeout=15000,
        )
        await page.wait_for_timeout(300)  # let the position settle after the resize

        # Stays within the visible notebook area (below the sticky toolbar)
        tip = await tooltip.bounding_box()
        container = await page.get_by_test_id("notebook-editor-container").bounding_box()
        toolbar = await page.get_by_test_id("notebook-sticky-toolbar").bounding_box()
        assert tip["y"] >= toolbar["y"] + toolbar["height"] - 1, "tooltip hidden under the toolbar"
        assert tip["y"] + tip["height"] <= container["y"] + container["height"] + 1, "tooltip below visible area"
        assert tip["x"] >= container["x"] and tip["x"] + tip["width"] <= container["x"] + container["width"] + 1

        # Pointer can enter it, and the wheel scrolls the tooltip, not the notebook
        metrics = await tooltip.evaluate("el => ({ sh: el.scrollHeight, ch: el.clientHeight })")
        assert metrics["sh"] > metrics["ch"], "read_csv docs should overflow and scroll"
        cx, cy = tip["x"] + tip["width"] / 2, tip["y"] + tip["height"] / 2
        assert await page.evaluate(
            "([x, y]) => !!document.elementFromPoint(x, y)?.closest('[data-testid=signature-help-tooltip]')", [cx, cy]
        ), "tooltip does not receive the pointer"
        notebook_scroll = await page.get_by_test_id("notebook-editor-container").evaluate("el => el.scrollTop")
        await page.mouse.move(cx, cy)
        await page.mouse.wheel(0, 300)
        await page.wait_for_timeout(300)
        assert await tooltip.evaluate("el => el.scrollTop") > 0, "wheel did not scroll the tooltip"
        assert await page.get_by_test_id("notebook-editor-container").evaluate("el => el.scrollTop") == notebook_scroll
        await expect(tooltip).to_be_visible()

        # Text can be selected with the mouse and copied
        await page.mouse.click(tip["x"] + 14, tip["y"] + 12)
        await page.mouse.dblclick(tip["x"] + 30, tip["y"] + 12)
        selected = await page.evaluate("window.getSelection().toString()")
        assert selected.strip(), "no text selected in tooltip"
        await page.keyboard.press("Control+c")
        assert (await page.evaluate("navigator.clipboard.readText()")).strip() == selected.strip()
        await expect(tooltip).to_be_visible()

        # Escape closes it and returns focus to the code; Ctrl+Space reopens it
        await page.keyboard.press("Escape")
        await expect(tooltip).to_be_hidden(timeout=3000)
        assert await page.evaluate("document.activeElement?.dataset?.testid") == "code-cell-editor"
        await page.keyboard.press("Control+Space")
        await expect(tooltip).to_be_visible(timeout=10000)

        # Leave valid code behind (guest tests share one notebook; other suites count error badges)
        await editor.fill("import pandas as pd\n")
        await page.wait_for_timeout(3000)  # let the debounced autosave store it
        await browser.close()


async def test_shortcuts_dialog_lists_every_shortcut_and_closes_with_escape():
    async with async_playwright() as p:
        browser, page = await open_notebook(p)
        await page.get_by_role("button", name="Shortcuts").first.click()
        dialog = page.get_by_test_id("shortcuts-modal")
        await expect(dialog).to_be_visible()
        text = await dialog.inner_text()
        for key in ["Ctrl + Enter", "Shift + Enter", "Alt + Enter", "Ctrl + C", "Ctrl + /", "Tab", "Shift + Tab",
                    "Ctrl + Space", "Esc", "Ctrl + S", "Ctrl + B"]:
            assert key in text, f"{key} missing from the shortcuts dialog"
        for section in ["Run & control", "Editing code", "Suggestions & function help", "Notebook & workspace"]:
            assert section.upper() in text.upper()
        await page.keyboard.press("Escape")
        await expect(dialog).to_be_hidden()
        await browser.close()


async def test_ctrl_s_saves_notebook_and_ctrl_b_toggles_sidebar():
    async with async_playwright() as p:
        browser, page = await open_notebook(p)
        editor = await new_code_cell(page, "saved_by_shortcut = 1")
        await page.wait_for_timeout(3500)  # let any pending auto-save finish first

        await editor.fill("saved_by_shortcut = 2")
        async with page.expect_request(
            lambda r: r.method == "PUT" and "/api/v1/notebooks/" in r.url, timeout=1500
        ) as request_info:
            await page.keyboard.press("Control+s")
        assert "saved_by_shortcut = 2" in (await request_info.value).post_data

        sidebar = page.get_by_test_id("left-sidebar")
        was_visible = await sidebar.is_visible()
        await page.keyboard.press("Control+b")
        await expect(sidebar).to_be_visible(visible=not was_visible)
        await page.keyboard.press("Control+b")
        await expect(sidebar).to_be_visible(visible=was_visible)
        await browser.close()


async def test_tab_and_shift_tab_indent_selected_lines_in_cell():
    async with async_playwright() as p:
        browser, page = await open_notebook(p)
        editor = await new_code_cell(page, "a = 1\nb = 2")
        await editor.focus()
        await editor.evaluate("el => el.setSelectionRange(0, el.value.length)")
        await page.keyboard.press("Tab")
        assert await editor.input_value() == "    a = 1\n    b = 2"
        await page.keyboard.press("Shift+Tab")
        assert await editor.input_value() == "a = 1\nb = 2"
        # No selection: Tab inserts four spaces at the cursor
        await editor.evaluate("el => el.setSelectionRange(0, 0)")
        await page.keyboard.press("Tab")
        assert await editor.input_value() == "    a = 1\nb = 2"
        await page.keyboard.press("Shift+Tab")
        assert await editor.input_value() == "a = 1\nb = 2"
        await browser.close()
