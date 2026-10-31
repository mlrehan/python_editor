"""
Browser tests for the file editor (CodeMirror 6), with real key events, against VS Code behaviour:
  - Python auto-indent after ":", Shift+Tab dedent, auto-closed brackets/quotes typed over
  - Ctrl+/ comment toggle with undo/redo, Ctrl+D multi-cursor editing, Alt+Up/Down move line,
    Ctrl+Shift+K delete line, Ctrl+F / Ctrl+H find and replace, code folding
  - IntelliSense (backend completions) and live diagnostics (syntax errors underlined)
  - each open file keeps its own undo history across tab switches; Ctrl+S saves the file

Requires a running server (default http://127.0.0.1:8765, override with PCS_E2E_URL).
Files are restored to their original content (nothing is left changed on disk).
"""
import os

import pytest
from playwright.async_api import async_playwright, expect

import cm_helpers as cm

pytestmark = pytest.mark.asyncio

SERVER_URL = os.environ.get("PCS_E2E_URL", "http://127.0.0.1:8765")


async def open_file(p, name="main.py", width=1440, height=900, theme=None):
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": width, "height": height})
    if theme:
        # Init scripts also run in the sandboxed output frames, where storage is off limits: top page only
        await context.add_init_script(f"if (window.top === window) localStorage.setItem('pcs_theme', '{theme}')")
    page = await context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    await page.goto(SERVER_URL, wait_until="networkidle")
    if not await page.locator('[data-testid="file-tree-item"]').count():
        await page.get_by_test_id("left-sidebar-toggle").click()
    await page.locator(f'[data-testid="file-tree-item"][data-path$="{name}"]').first.dblclick()
    await cm.wait_for_editor(page)
    return browser, page, errors


async def test_typing_python_auto_indents_and_closes_brackets():
    async with async_playwright() as p:
        browser, page, errors = await open_file(p)
        await cm.set_doc(page, "")
        await cm.set_cursor(page, 0)
        kb = page.keyboard
        await kb.type("def greet(name):")
        await kb.press("Enter")
        await kb.type('message = f"Hi {name}"')
        await kb.press("Enter")
        await kb.type("if name:")
        await kb.press("Enter")
        await kb.type("print(message)")
        await kb.press("Enter")
        await kb.press("Shift+Tab")
        await kb.type("return [1, 2]")
        assert await cm.doc(page) == (
            'def greet(name):\n'
            '    message = f"Hi {name}"\n'
            '    if name:\n'
            '        print(message)\n'
            '    return [1, 2]'
        )
        # Typing "(" inserts the pair; the caret sits between them
        await kb.press("Enter")
        await kb.type("x = len(")
        text = await cm.doc(page)
        assert text.endswith("x = len()"), text[-20:]
        assert (await cm.selection(page))[0] == len(text) - 1
        await kb.press("Control+a")
        await kb.press("Delete")
        assert not errors, errors
        await browser.close()


async def test_comment_toggle_multicursor_move_delete_and_undo():
    async with async_playwright() as p:
        browser, page, errors = await open_file(p)
        original = await cm.doc(page)
        await cm.set_doc(page, "a = 1\nb = 2\nc = a + b\n")
        kb = page.keyboard

        # Ctrl+/ on a selection spanning two lines, then undo and redo
        await cm.set_cursor(page, 0, 9)
        await kb.press("Control+/")
        assert await cm.doc(page) == "# a = 1\n# b = 2\nc = a + b\n"
        await kb.press("Control+z")
        assert await cm.doc(page) == "a = 1\nb = 2\nc = a + b\n"
        await kb.press("Control+Shift+z")
        assert await cm.doc(page) == "# a = 1\n# b = 2\nc = a + b\n"
        await kb.press("Control+z")

        # Ctrl+D selects the next occurrence: rename both "a" usages at once (VS Code multi-cursor)
        await cm.set_cursor(page, 0, 1)  # the "a" in "a = 1"
        await kb.press("Control+d")
        await kb.press("Control+d")
        assert await page.evaluate(f"{cm.VIEW}.state.selection.ranges.length") == 2
        await kb.type("alpha")
        assert await cm.doc(page) == "alpha = 1\nb = 2\nc = alpha + b\n"

        # Alt+Down moves the line, Ctrl+Shift+K deletes it
        await cm.set_cursor(page, 0)
        await kb.press("Alt+ArrowDown")
        assert await cm.doc(page) == "b = 2\nalpha = 1\nc = alpha + b\n"
        await kb.press("Control+Shift+k")
        assert await cm.doc(page) == "b = 2\nc = alpha + b\n"
        await cm.set_doc(page, original)
        assert not errors, errors
        await browser.close()


async def test_find_replace_and_folding():
    async with async_playwright() as p:
        browser, page, errors = await open_file(p)
        original = await cm.doc(page)
        await cm.set_doc(page, "def f():\n    x = 1\n    y = 2\n    return x + y\n\nz = f()\n")
        kb = page.keyboard

        # Ctrl+F opens the search panel and highlights matches
        await cm.set_cursor(page, 0)
        await kb.press("Control+f")
        search = page.locator(".cm-search input[name=search]")
        await expect(search).to_be_visible()
        await search.press_sequentially("x")
        await expect(page.locator(".cm-searchMatch").first).to_be_visible()
        # Replace all
        await page.locator(".cm-search input[name=replace]").press_sequentially("value")
        await page.locator(".cm-search button[name=replaceAll]").click()
        assert await cm.doc(page) == "def f():\n    value = 1\n    y = 2\n    return value + y\n\nz = f()\n"
        await kb.press("Escape")
        await expect(search).to_have_count(0)

        # Folding: the function body collapses to a placeholder and expands again
        fold_marker = page.locator(".cm-foldGutter .cm-gutterElement span[title='Fold line']").first
        await fold_marker.click()
        await expect(page.locator(".cm-foldPlaceholder")).to_be_visible()
        await expect(page.locator(".cm-line", has_text="return value")).to_have_count(0)
        await page.locator(".cm-foldPlaceholder").click()  # unfold
        await expect(page.locator(".cm-line", has_text="return value")).to_be_visible()
        await cm.set_doc(page, original)
        assert not errors, errors
        await browser.close()


async def test_intellisense_and_live_diagnostics():
    async with async_playwright() as p:
        browser, page, errors = await open_file(p)
        original = await cm.doc(page)
        await cm.set_doc(page, "import sys\n")
        await cm.set_cursor(page, len("import sys\n"))
        kb = page.keyboard
        await kb.type("sys.pa")
        menu = page.locator(".cm-tooltip-autocomplete")
        await expect(menu).to_be_visible(timeout=8000)
        labels = await menu.locator(".cm-completionLabel").all_inner_texts()
        assert "path" in labels, labels
        await expect(menu.locator("li[aria-selected]")).to_have_count(1)
        # CodeMirror ignores Enter for 75 ms after the menu appears (so a menu popping up just as you
        # press Enter for a new line does not steal it); a person reads the menu first
        await page.wait_for_timeout(150)
        await kb.press("Enter")  # accept the selected suggestion
        assert (await cm.doc(page)).startswith("import sys\nsys.path"), await cm.doc(page)

        # A syntax error is underlined and marked in the gutter after a short pause
        await kb.press("End")
        await kb.press("Enter")
        await kb.type("def broken(:")
        await expect(page.locator(".cm-lintRange-error").first).to_be_visible(timeout=8000)
        await expect(page.locator(".cm-lint-marker-error").first).to_be_visible()
        await cm.set_doc(page, original)
        await expect(page.locator(".cm-lintRange-error")).to_have_count(0, timeout=8000)
        assert not errors, errors
        await browser.close()


async def test_each_file_keeps_its_own_undo_history_and_ctrl_s_saves():
    async with async_playwright() as p:
        browser, page, errors = await open_file(p)
        main_original = await cm.doc(page)
        await cm.set_cursor(page, len(main_original))
        await page.keyboard.type("# edited in main")

        # Open README.md, edit it, switch back to main.py: main's undo history is still there
        await page.locator('[data-testid="file-tree-item"][data-path$="README.md"]').first.dblclick()
        await expect(page.get_by_test_id("active-file-indicator")).to_contain_text("README.md")
        await page.get_by_test_id("right-file-editor-panel").get_by_title("Toggle Preview / Edit").click()  # Markdown opens in preview
        await cm.wait_for_editor(page)
        readme_original = await cm.doc(page)
        await cm.set_cursor(page, 0)
        await page.keyboard.type("Draft: ")
        assert (await cm.doc(page)).startswith("Draft: ")

        await page.get_by_test_id("file-tab-main.py").click()
        await expect(page.get_by_test_id("active-file-indicator")).to_contain_text("main.py")
        assert (await cm.doc(page)).endswith("# edited in main")
        await page.get_by_test_id("file-editor-content").focus()
        await page.keyboard.press("Control+z")
        assert await cm.doc(page) == main_original, "undo applies to main.py's own history"

        # README kept its unsaved edit; undo there restores it
        await page.get_by_test_id("file-tab-README.md").click()
        await cm.wait_for_editor(page)
        assert (await cm.doc(page)).startswith("Draft: ")
        await page.get_by_test_id("file-editor-content").focus()
        await page.keyboard.press("Control+z")
        assert await cm.doc(page) == readme_original

        # Ctrl+S saves the active file (save a change, then save the original back)
        await page.get_by_test_id("file-tab-main.py").click()
        await cm.wait_for_editor(page)
        await cm.set_cursor(page, len(main_original))
        await page.keyboard.type("\n# saved")
        await expect(page.get_by_test_id("dirty-indicator-main.py")).to_be_visible()
        await page.keyboard.press("Control+s")
        await expect(page.get_by_test_id("dirty-indicator-main.py")).to_have_count(0, timeout=8000)
        saved = await page.request.get(f"{SERVER_URL}/api/v1/files/read?path=main.py")
        if saved.ok:
            assert (await saved.json()).get("content", "").endswith("# saved")
        await cm.set_doc(page, main_original)
        await page.get_by_test_id("file-editor-content").focus()
        await page.keyboard.press("Control+s")
        await expect(page.get_by_test_id("dirty-indicator-main.py")).to_have_count(0, timeout=8000)
        assert not errors, errors
        await browser.close()


@pytest.mark.parametrize("theme", ["dark", "light"])
async def test_editor_is_monospace_and_themed(theme):
    async with async_playwright() as p:
        browser, page, errors = await open_file(p, theme=theme)
        font = await page.locator(".cm-content").evaluate("e => getComputedStyle(e).fontFamily")
        assert "JetBrains Mono" in font or "monospace" in font, font
        # Monospace: every character advances the caret by the same width
        widths = await page.locator(".cm-line").first.evaluate(
            """l => { const r = document.createRange(); const t = l.firstChild && (l.firstChild.firstChild || l.firstChild);
                     const w = []; for (const ch of ['i', 'W', '#']) { const s = document.createElement('span'); s.textContent = ch.repeat(10); l.appendChild(s);
                     w.push(s.getBoundingClientRect().width); s.remove(); } return w; }"""
        )
        assert max(widths) - min(widths) < 0.5, widths
        bg = await page.locator(".cm-editor").evaluate("e => getComputedStyle(e).backgroundColor")
        panel = await page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--bg-panel').trim()")
        assert bg != "rgba(0, 0, 0, 0)" and panel
        assert not errors, errors
        await browser.close()
