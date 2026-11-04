"""
Editor productivity: Python indentation, error details, typography and text (Markdown) cells.
  1. Enter / Backspace / ":" indent like VS Code in notebook cells and .py files
  2. Hovering a problem shows Python's exact error, its type and line; runtime errors are marked at the
     line that raised them and traceback locations open the cell or file at that line
  3. JetBrains Mono (bundled), 14px / 22px by default in cells and files; the size can be changed
  4. Text cells: a formatting toolbar and shortcuts, rendered on leaving, kept after save and reload,
     existing Markdown untouched, unsafe HTML removed

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


async def new_code_cell(page):
    await page.get_by_role("button", name="Add Code Cell").click()
    editor = last_cell(page).locator('textarea[data-testid="code-cell-editor"]')
    await expect(editor).to_be_focused()
    return editor


async def run_last(page):
    await page.keyboard.press("Control+Enter")
    await expect(last_cell(page).locator(".cell-header").first).to_contain_text(re.compile(r"\[\d+\]"), timeout=60000)


# --- 1. Indentation ------------------------------------------------------------------------------


async def test_smart_indentation_in_cells():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        editor = await new_code_cell(page)
        kb = page.keyboard
        await kb.type("class Shop:")
        await kb.press("Enter")
        await kb.type("def total(self, items):")
        await kb.press("Enter")
        await kb.type("for x in items:")
        await kb.press("Enter")
        await kb.type("if x:")
        await kb.press("Enter")
        await kb.type("pass")
        await kb.press("Enter")  # the word is complete: a new line (not "accept pass"), back one level
        await kb.type("else:")
        await kb.press("Enter")
        await kb.type("continue")
        await kb.press("Enter")
        # Backspace in leading spaces: one level (4 spaces) per press
        await kb.press("Backspace")
        await kb.type("return sum(")  # "(" closes itself: sum()
        await kb.press("Enter")  # between the brackets: split over three lines
        await kb.type("items")
        assert await editor.input_value() == (
            "class Shop:\n"
            "    def total(self, items):\n"
            "        for x in items:\n"
            "            if x:\n"
            "                pass\n"
            "            else:\n"
            "                continue\n"
            "        return sum(\n"
            "            items\n"
            "        )"
        ), await editor.input_value()

        # "else:" typed at the body's level moves under its "if"
        await editor.fill("if a:\n    x = 1\n    ")
        await editor.press("Control+End")
        await kb.type("else:")
        assert await editor.input_value() == "if a:\n    x = 1\nelse:"

        # f(|) -> three lines with the caret on the indented middle one
        await editor.fill("")
        await kb.type("print(")  # auto-closes to print()
        await kb.press("Enter")
        await kb.type("1")
        assert await editor.input_value() == "print(\n    1\n)"

        # Backspace on code characters is the normal one
        await editor.fill("x = 12")
        await editor.press("End")
        await kb.press("Backspace")
        assert await editor.input_value() == "x = 1"
        # Ctrl+Z undoes a smart Backspace as one step
        await editor.fill("if a:\n        ")
        await editor.press("Control+End")
        await kb.press("Backspace")
        assert await editor.input_value() == "if a:\n    "
        await kb.press("Control+z")
        assert await editor.input_value() == "if a:\n        "

        await last_cell(page).get_by_title("Delete Cell").click()
        assert not errors, errors
        await browser.close()


async def test_smart_indentation_in_python_files():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        await api(page, "POST", "/files/write", {"path": "indent_check.py", "content": ""})
        await page.evaluate("window.dispatchEvent(new CustomEvent('pcs-refresh-files'))")
        await page.locator('[data-testid="file-tree-item"][data-path="indent_check.py"]').dblclick()
        content = page.locator(".cm-content").first
        await content.click()
        kb = page.keyboard
        await kb.type("def f(x):")
        await kb.press("Enter")
        await kb.type("if x:")
        await kb.press("Enter")
        await kb.type("return 1")
        await kb.press("Enter")  # back to the "if" level after return
        await kb.type("y = 2")
        await kb.press("Enter")
        await kb.press("Backspace")  # one level, not one space
        await kb.type("z = 3")
        doc = await page.evaluate("document.querySelector('.cm-editor').cmView.state.doc.toString()")
        assert doc == "def f(x):\n    if x:\n        return 1\n    y = 2\nz = 3", doc
        await api(page, "DELETE", "/files?path=indent_check.py")
        assert not errors, errors
        await browser.close()


# --- 2. Errors -----------------------------------------------------------------------------------


async def hover_problem(page, cell, line, col):
    """Moves the real mouse over a character of a code cell."""
    editor = cell.locator('textarea[data-testid="code-cell-editor"]')
    box = await editor.bounding_box()
    metrics = await editor.evaluate("""el => { const cs = getComputedStyle(el); const c = document.createElement('canvas').getContext('2d');
        c.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
        return [parseFloat(cs.paddingLeft), parseFloat(cs.paddingTop), parseFloat(cs.lineHeight), c.measureText('MMMMMMMMMM').width / 10]; }""")
    pad_x, pad_y, line_h, char_w = metrics
    await page.mouse.move(box["x"] + pad_x + char_w * (col + 0.5), box["y"] + pad_y + line_h * (line - 0.5))


async def test_hover_shows_pythons_exact_syntax_error():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        editor = await new_code_cell(page)
        await editor.fill("if True:\nprint('x')")
        cell = last_cell(page)
        await expect(cell.get_by_test_id("diagnostic-badge")).to_contain_text("Line 2: IndentationError", timeout=8000)
        await hover_problem(page, cell, 2, 1)
        card = cell.get_by_test_id("diagnostic-tooltip")
        await expect(card).to_be_visible()
        await expect(card.get_by_test_id("diagnostic-type")).to_have_text("IndentationError")
        await expect(card.get_by_test_id("diagnostic-message")).to_have_text("expected an indented block after 'if' statement on line 1")
        await expect(card.get_by_test_id("diagnostic-location")).to_have_text("Line 2, column 1")
        # The gutter marker shows it too; the badge selects the problem
        await page.mouse.move(0, 0)
        await expect(card).to_have_count(0, timeout=3000)
        await cell.get_by_test_id("diagnostic-badge").click()
        await expect(card).to_be_visible()
        sel = await editor.evaluate("el => el.value.slice(el.selectionStart, el.selectionEnd)")
        assert sel.startswith("p"), sel
        await cell.get_by_title("Delete Cell").click()
        assert not errors, errors
        await browser.close()


async def test_runtime_error_is_marked_and_links_to_its_source():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        await api(page, "POST", "/files/write", {"path": "buggy.py", "content": "def check(n):\n    if n < 0:\n        raise ValueError(f'negative: {n}')\n    return n\n"})
        editor = await new_code_cell(page)
        await editor.fill("from buggy import check\nvalues = [1, -2]\nresult = [check(v) for v in values]")
        await run_last(page)
        cell = last_cell(page)
        out = cell.get_by_test_id("cell-output-container")
        await expect(out).to_contain_text("ValueError: negative: -2")
        # The full traceback is kept
        await expect(out).to_contain_text("Traceback (most recent call last)")
        # Marked at the line of this cell that raised it, with Python's message on hover
        await expect(cell.get_by_test_id("diagnostic-gutter-marker")).to_have_attribute("aria-label", "Line 3: ValueError: negative: -2")
        await hover_problem(page, cell, 3, 12)
        card = cell.get_by_test_id("diagnostic-tooltip")
        await expect(card.get_by_test_id("diagnostic-type")).to_have_text("ValueError")
        await expect(card).to_contain_text("raised when this cell ran")
        await expect(card.get_by_test_id("diagnostic-location")).to_have_text("Line 3")
        # Traceback locations: this cell and the file, each a link
        links = cell.get_by_test_id("error-location-link")
        await expect(links.filter(has_text="This cell, line 3")).to_have_count(1)
        file_link = links.filter(has_text="buggy.py, line 3")
        await expect(file_link).to_have_count(1)
        await file_link.click()
        await expect(page.get_by_test_id("active-file-indicator")).to_contain_text("buggy.py")
        await page.wait_for_function("""() => { const v = document.querySelector('.cm-editor')?.cmView;
            return !!v && v.state.doc.toString().includes('raise ValueError') && v.state.doc.lineAt(v.state.selection.main.head).number === 3; }""", timeout=10000)
        assert await page.evaluate("document.activeElement.closest('.cm-editor') !== null")
        # A cell link puts the caret on that line
        await links.filter(has_text="This cell, line 3").click()
        await expect(editor).to_be_focused()
        caret_line = await editor.evaluate("el => el.value.slice(0, el.selectionStart).split('\\n').length")
        assert caret_line == 3
        await cell.get_by_title("Delete Cell").click()
        await api(page, "DELETE", "/files?path=buggy.py")
        assert not errors, errors
        await browser.close()


@pytest.mark.parametrize("code,error_type", [
    ("x = undefined_thing", "NameError"),
    ("'a' + 1", "TypeError"),
    ("int('abc')", "ValueError"),
    ("import module_that_does_not_exist_xyz", "ModuleNotFoundError"),
    ("raise RuntimeError('stopped')", "RuntimeError"),
])
async def test_common_runtime_errors_are_marked(code, error_type):
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        editor = await new_code_cell(page)
        await editor.fill(code)
        await run_last(page)
        cell = last_cell(page)
        await expect(cell.get_by_test_id("diagnostic-gutter-marker").first).to_have_attribute("aria-label", re.compile(rf"^Line 1: {error_type}"))
        await expect(cell.get_by_test_id("cell-output-container")).to_contain_text(error_type)
        await cell.get_by_title("Delete Cell").click()
        assert not errors, errors
        await browser.close()


# --- 3. Typography -------------------------------------------------------------------------------


async def test_default_typography_and_font_size_setting():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        await page.evaluate("document.fonts.ready")
        editor = page.locator('textarea[data-testid="code-cell-editor"]').first
        style = await editor.evaluate("el => { const s = getComputedStyle(el); return [s.fontFamily, s.fontSize, s.lineHeight]; }")
        assert style[0].startswith('"JetBrains Mono Variable"') and style[1:] == ["14px", "22px"], style
        assert await page.evaluate("document.fonts.check('14px \"JetBrains Mono Variable\"')")
        # Bundled with the app: nothing is fetched from Google Fonts (blocked by the CSP)
        assert not await page.evaluate("performance.getEntriesByType('resource').some(e => /googleapis|gstatic/.test(e.name))")

        # A larger size applies to cells and is remembered
        await page.get_by_role("button", name=re.compile("More actions", re.I)).first.click()
        await page.get_by_test_id("editor-font-larger").click()
        await page.get_by_test_id("editor-font-larger").click()
        await expect(page.get_by_test_id("editor-font-size-value")).to_have_text("16px")
        await page.keyboard.press("Escape")
        assert await editor.evaluate("el => [getComputedStyle(el).fontSize, getComputedStyle(el).lineHeight]") == ["16px", "26px"]
        await page.reload(wait_until="networkidle")
        editor = page.locator('textarea[data-testid="code-cell-editor"]').first
        await expect(editor).to_have_css("font-size", "16px")
        await page.evaluate("localStorage.removeItem('pcs_editor_font_size')")
        assert not errors, errors
        await browser.close()


# --- 4. Text (Markdown) cells --------------------------------------------------------------------


async def new_text_cell(page):
    await page.get_by_role("button", name="Add Text Cell").click()
    editor = last_cell(page).get_by_test_id("markdown-cell-editor")
    await expect(editor).to_be_focused()
    await expect(last_cell(page).get_by_test_id("markdown-toolbar")).to_be_visible()
    return editor


async def select(editor, text):
    await editor.evaluate("(el, t) => { const i = el.value.indexOf(t); el.focus(); el.setSelectionRange(i, i + t.length); }", text)


async def test_text_cell_toolbar_formats_without_markdown_knowledge():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        editor = await new_text_cell(page)
        cell = last_cell(page)
        tb = cell.get_by_test_id("markdown-toolbar")
        kb = page.keyboard
        await kb.type("Project notes\nThis is important and urgent.\nFirst step\nSecond step\nSee the docs here.")

        await select(editor, "Project notes")
        await tb.get_by_test_id("md-heading-menu").click()
        await tb.get_by_test_id("md-opt-h1").click()
        await select(editor, "important")
        await tb.get_by_test_id("md-bold").click()
        await expect(editor).to_be_focused()  # the toolbar never takes the focus
        await select(editor, "urgent")
        await tb.get_by_test_id("md-italic").click()
        await tb.get_by_test_id("md-highlight").click()
        await select(editor, "First step\nSecond step")
        await tb.get_by_test_id("md-numbers").click()
        await select(editor, "docs")
        await tb.get_by_test_id("md-link").click()
        await tb.get_by_test_id("md-link-url").fill("https://docs.python.org/3/")
        await tb.get_by_test_id("md-link-apply").click()
        await editor.press("Control+End")
        await kb.press("Enter")
        await tb.get_by_test_id("md-tasks").click()
        await kb.type("Write tests")
        await kb.press("Enter")
        await kb.press("Enter")  # an empty item ends the list
        await tb.get_by_test_id("md-codeblock").click()
        await tb.get_by_test_id("md-code-python").click()
        await kb.type("total = sum([1, 2])")
        await editor.press("Control+End")
        await kb.press("Enter")
        await tb.get_by_test_id("md-math").click()
        await tb.get_by_test_id("md-math-block").click()
        await editor.press("Control+End")
        await kb.press("Enter")
        await kb.type("Red note")
        await select(editor, "Red note")
        await tb.get_by_test_id("md-color").click()
        await tb.get_by_test_id("md-color-red").click()

        source = await editor.input_value()
        # The list is kept apart from the paragraphs around it (blank lines), so it shows as a list
        assert source.startswith("# Project notes\nThis is **important** and *<mark>urgent</mark>*.\n\n1. First step\n2. Second step\n\nSee the [docs](https://docs.python.org/3/) here.\n- [ ] Write tests\n"), source
        assert "```python\ntotal = sum([1, 2])\n```" in source
        assert "$$\nE = mc^2\n$$" in source
        assert '<span style="color: #dc2626">Red note</span>' in source

        # The live preview, then the rendered cell after leaving it
        preview = cell.get_by_test_id("markdown-live-preview")
        await expect(preview.locator("h1")).to_have_text("Project notes")
        await page.keyboard.press("Escape")
        rendered = cell.get_by_test_id("markdown-rendered")
        await expect(rendered).to_be_visible()
        await expect(rendered.locator("h1")).to_have_text("Project notes")
        await expect(rendered.locator("strong")).to_have_text("important")
        await expect(rendered.locator("em mark")).to_have_text("urgent")
        await expect(rendered.locator("ol li")).to_have_text(["First step", "Second step"])
        await expect(rendered.locator('a[href="https://docs.python.org/3/"]')).to_have_attribute("target", "_blank")
        await expect(rendered.locator('input[type="checkbox"]')).to_have_count(1)
        await expect(rendered.locator("pre.md-code .tok-keyword, pre.md-code .tok-builtin").first).to_be_visible()
        await expect(rendered.locator(".md-math-block .katex")).to_be_visible(timeout=10000)
        await expect(rendered.get_by_text("Red note")).to_have_css("color", "rgb(220, 38, 38)")

        # Saved, reloaded, still formatted
        await page.keyboard.press("Control+s")
        await page.wait_for_timeout(1500)
        await page.reload(wait_until="networkidle")
        rendered = last_cell(page).get_by_test_id("markdown-rendered")
        await expect(rendered.locator("h1")).to_have_text("Project notes")
        await expect(rendered.locator("ol li")).to_have_count(2)
        await last_cell(page).get_by_title("Delete Cell").click()
        assert not errors, errors
        await browser.close()


async def test_text_cell_shortcuts_lists_and_undo():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        sidebar_open = await page.get_by_test_id("left-sidebar").count()
        editor = await new_text_cell(page)
        kb = page.keyboard
        await kb.type("word")
        await select(editor, "word")
        await kb.press("Control+b")
        assert await editor.input_value() == "**word**"
        # Ctrl+B was Bold, not "toggle the Files sidebar"
        assert await page.get_by_test_id("left-sidebar").count() == sidebar_open
        await kb.press("Control+i")
        assert await editor.input_value() == "***word***"
        await kb.press("Control+Shift+S")
        assert await editor.input_value() == "***~~word~~***"
        # Undo, step by step
        await kb.press("Control+z")
        assert await editor.input_value() == "***word***"
        await kb.press("Control+z")
        assert await editor.input_value() == "**word**"
        await kb.press("Control+Shift+z")
        assert await editor.input_value() == "***word***"

        await editor.fill("")
        await kb.type("alpha")
        await kb.press("Control+Shift+8")
        assert await editor.input_value() == "- alpha"
        await editor.press("End")
        await kb.press("Enter")
        await kb.type("beta")
        await kb.press("Tab")  # nests the item
        await kb.press("Enter")
        await kb.type("gamma")
        assert await editor.input_value() == "- alpha\n    - beta\n    - gamma"

        await editor.fill("")
        await kb.type("one")
        await kb.press("Control+Shift+7")
        await editor.press("End")
        await kb.press("Enter")
        await kb.type("two")
        await kb.press("Enter")
        await kb.type("three")
        assert await editor.input_value() == "1. one\n2. two\n3. three"
        await editor.press("Control+Home")
        await editor.press("End")
        await kb.press("Enter")
        await kb.type("inserted")
        assert await editor.input_value() == "1. one\n2. inserted\n3. two\n4. three"

        # Prose is not treated as code: no automatic quotes or brackets
        await editor.fill("")
        await kb.type("don't (really)")
        assert await editor.input_value() == "don't (really)"

        # Ctrl+Alt+2 heading, Ctrl+K link
        await kb.press("Control+Alt+2")
        assert await editor.input_value() == "## don't (really)"
        await select(editor, "really")
        await kb.press("Control+k")
        await page.get_by_test_id("md-link-url").fill("https://example.org")
        await page.keyboard.press("Enter")
        assert await editor.input_value() == "## don't ([really](https://example.org))"
        await expect(editor).to_be_focused()

        await page.keyboard.press("Escape")
        await last_cell(page).get_by_title("Delete Cell").click()
        assert not errors, errors
        await browser.close()


async def test_existing_markdown_is_kept_and_unsafe_html_removed():
    source = (
        "## Results\n\n| Model | Score |\n|---|---|\n| A | 0.91 |\n| B | 0.87 |\n\n"
        "> A quote\n\n1. one\n    - nested\n2. two\n\n![chart](https://example.org/c.png)\n\n"
        "Inline $a^2 + b^2$ maths.\n\n<img src=x onerror=\"window.__pwned=1\"><script>window.__pwned=2</script>"
        "<a href=\"javascript:window.__pwned=3\">bad</a>\n<span style=\"position:fixed;top:0;color:red\">styled</span>"
    )
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        await page.get_by_role("button", name="Add Text Cell").click()
        editor = last_cell(page).get_by_test_id("markdown-cell-editor")
        await editor.fill(source)
        await page.keyboard.press("Escape")
        rendered = last_cell(page).get_by_test_id("markdown-rendered")
        await expect(rendered.locator("table tr")).to_have_count(3)
        await expect(rendered.locator("blockquote")).to_have_text("A quote")
        await expect(rendered.locator("ol > li > ul > li")).to_have_text("nested")
        await expect(rendered.locator('img[alt="chart"]')).to_have_count(1)
        await expect(rendered.locator(".md-math .katex")).to_be_visible(timeout=10000)
        assert await page.evaluate("window.__pwned") is None
        assert await rendered.locator("script").count() == 0
        assert await rendered.locator("[onerror]").count() == 0
        href = await rendered.get_by_text("bad").get_attribute("href")
        assert not href or not href.startswith("javascript:")
        style = await rendered.get_by_text("styled").get_attribute("style")
        assert style == "color:red", style
        # Opening and leaving the editor does not change the text
        await rendered.dblclick()
        await expect(editor).to_be_focused()
        assert await editor.input_value() == source
        await page.keyboard.press("Escape")
        await expect(rendered).to_be_visible()
        await last_cell(page).get_by_title("Delete Cell").click()
        assert not errors, errors
        await browser.close()
