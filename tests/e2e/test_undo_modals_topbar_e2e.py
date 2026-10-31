"""
Browser tests for editor undo history, the shared modal layer and the responsive top bar:
  - Ctrl+Z / Ctrl+Shift+Z / Ctrl+Y undo and redo Ctrl+/ comment toggles (single and multi-line) with the
    selection restored; consecutive edits undo in order; ordinary typing undo still works; same in the file editor
  - every dialog renders above the top bar (portal layer), centred, scrolls internally, closes with its
    close button or Escape (topmost dialog only), in the dark and light themes
  - the top bar has no horizontal overflow, overlapping or clipped controls from 1920px down to 320px,
    and every control stays reachable (in the bar or in the More / account menus)

Requires a running server (default http://127.0.0.1:8765, override with PCS_E2E_URL).
"""
import os

import pytest
from playwright.async_api import async_playwright, expect

import cm_helpers as cm

pytestmark = pytest.mark.asyncio

SERVER_URL = os.environ.get("PCS_E2E_URL", "http://127.0.0.1:8765")


async def open_studio(p, width=1440, height=900, theme=None):
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": width, "height": height})
    if theme:
        # Init scripts also run in the sandboxed output frames, where storage is off limits: top page only
        await context.add_init_script(f"if (window.top === window) localStorage.setItem('pcs_theme', '{theme}')")
    page = await context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    await page.goto(SERVER_URL, wait_until="networkidle")
    await page.locator("header.pcs-topbar").wait_for(state="visible", timeout=15000)
    await page.wait_for_timeout(500)
    # Phones open with the explorer drawer showing; close it like a user would (tap outside)
    backdrop = page.get_by_test_id("mobile-left-backdrop")
    if await backdrop.count() and await backdrop.is_visible():
        await page.mouse.click(width - 10, height // 2)
        await expect(backdrop).to_have_count(0)
    return browser, page, errors


async def new_code_cell(page, code):
    editors = page.locator('textarea[data-testid="code-cell-editor"]')
    await editors.first.wait_for(state="visible", timeout=15000)
    index = await editors.count()
    await page.get_by_role("button", name="Add Code Cell").click()
    editor = editors.nth(index)
    await editor.wait_for(state="visible")
    await editor.fill(code)
    await page.keyboard.press("Escape")
    return editor


async def select(editor, start, end):
    await editor.evaluate("(el, [s, e]) => { el.focus(); el.setSelectionRange(s, e); }", [start, end])


async def state(editor):
    return await editor.evaluate("el => [el.value, el.selectionStart, el.selectionEnd]")


async def delete_cell(editor):
    await editor.locator('xpath=ancestor::div[@data-testid="notebook-cell"][1]').get_by_title("Delete Cell").click()


# --- Task 1: undo / redo ------------------------------------------------------------------------------


async def test_ctrl_slash_comment_toggles_undo_and_redo_with_selection():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        code = "a = 1\nb = 2"
        editor = await new_code_cell(page, code)

        # Multi-line comment, undo, redo
        await select(editor, 0, len(code))
        await page.keyboard.press("Control+/")
        commented = "# a = 1\n# b = 2"
        assert (await state(editor))[0] == commented
        await page.keyboard.press("Control+z")
        assert await state(editor) == [code, 0, len(code)], "undo must restore the text and the selection"
        await page.keyboard.press("Control+Shift+z")
        value, s, e = await state(editor)
        assert value == commented and (s, e) == (0, len(commented)), "redo must restore the commented lines"

        # Uncomment, undo, redo (Ctrl+Y)
        await page.keyboard.press("Control+/")
        assert (await state(editor))[0] == code
        await page.keyboard.press("Control+z")
        assert (await state(editor))[0] == commented
        await page.keyboard.press("Control+y")
        assert (await state(editor))[0] == code

        # Single line (cursor only): comment, undo, redo
        await select(editor, 8, 8)  # inside "b = 2"
        await page.keyboard.press("Control+/")
        assert (await state(editor))[0] == "a = 1\n# b = 2"
        await page.keyboard.press("Control+z")
        assert await state(editor) == [code, 8, 8]
        await page.keyboard.press("Control+Shift+z")
        assert (await state(editor))[0] == "a = 1\n# b = 2"

        # The cell's stored source follows the undone text (React state, not just the DOM)
        await page.keyboard.press("Control+z")
        await page.keyboard.press("Escape")
        await expect(editor).to_have_value(code)
        await delete_cell(editor)
        assert not errors, errors
        await browser.close()


async def test_consecutive_edits_and_typing_undo_in_order():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        code = "x = 1"
        editor = await new_code_cell(page, code)

        await select(editor, 0, 0)
        await page.keyboard.press("Control+/")  # "# x = 1"
        await page.keyboard.press("Tab")  # inserts 4 spaces at the cursor (after "# ")
        after_tab = (await state(editor))[0]
        assert after_tab == "#     x = 1", after_tab
        await page.keyboard.press("Control+/")  # uncomment
        assert (await state(editor))[0] == "    x = 1"

        await page.keyboard.press("Control+z")
        assert (await state(editor))[0] == after_tab
        await page.keyboard.press("Control+z")
        assert (await state(editor))[0] == "# x = 1"
        await page.keyboard.press("Control+z")
        assert (await state(editor))[0] == code

        # Ordinary typing still undoes natively
        await select(editor, len(code), len(code))
        await page.keyboard.type(" + 2")  # no identifiers: avoids the autocomplete popup
        assert (await state(editor))[0] == code + " + 2"
        # The cell editor undoes typing in word-sized steps (unchanged behaviour); it must get back to the original
        for _ in range(4):
            await page.keyboard.press("Control+z")
            if (await state(editor))[0] == code:
                break
        assert (await state(editor))[0] == code
        await delete_cell(editor)
        assert not errors, errors
        await browser.close()


async def test_file_editor_comment_toggle_undo_redo():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        await page.get_by_text("main.py", exact=True).first.dblclick()
        await cm.wait_for_editor(page)
        original = await cm.doc(page)
        assert original

        await cm.set_cursor(page, 0)
        await page.keyboard.press("Control+/")
        value = await cm.doc(page)
        first = original.splitlines()[0]
        expected_first = first.replace("# ", "", 1) if first.lstrip().startswith("#") else "# " + first
        assert value.splitlines()[0] == expected_first, value.splitlines()[0]
        await page.keyboard.press("Control+z")
        assert await cm.doc(page) == original
        assert await cm.selection(page) == [0, 0]
        await page.keyboard.press("Control+Shift+z")
        assert await cm.doc(page) == value
        await page.keyboard.press("Control+z")
        assert await cm.doc(page) == original
        assert not errors, errors
        await browser.close()


# --- Task 3: modals ------------------------------------------------------------------------------------


async def assert_dialog_on_top(page, dialog):
    """The dialog is portal-rendered on <body>, centred, inside the viewport and painted above the top bar."""
    info = await dialog.evaluate(
        """el => {
          const r = el.getBoundingClientRect();
          const header = document.querySelector('header.pcs-topbar').getBoundingClientRect();
          const backdrop = el.closest('.pcs-modal-backdrop');
          // Probe points where the dialog overlaps the top bar's band, or its top edge
          const y = Math.max(r.top + 4, Math.min(header.bottom - 4, r.bottom - 4));
          const hits = [r.left + 12, r.left + r.width / 2, r.right - 12].map(x => el.contains(document.elementFromPoint(x, y)));
          const topHit = el.contains(document.elementFromPoint(r.left + r.width / 2, r.top + 6));
          return {
            portal: !!backdrop && backdrop.parentElement === document.body,
            inView: r.top >= 0 && r.left >= 0 && r.bottom <= innerHeight + 0.5 && r.right <= innerWidth + 0.5,
            centred: Math.abs((r.left + r.right) / 2 - innerWidth / 2) < 2,
            hits, topHit,
            bodyScrolls: (() => { const b = el.querySelector('.pcs-modal-body'); return !b || getComputedStyle(b).overflowY === 'auto'; })(),
          };
        }"""
    )
    assert info["portal"], "dialog must be rendered through the portal on document.body"
    assert info["inView"], "dialog must fit inside the viewport"
    assert info["centred"], "dialog must be horizontally centred"
    assert info["topHit"] and all(info["hits"]), f"dialog is covered by another layer: {info}"
    assert info["bodyScrolls"]


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("width,height", [(1440, 900), (768, 1024), (375, 667)])
async def test_shortcuts_dialog_is_above_top_bar_and_closes(theme, width, height):
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, width, height, theme)
        await page.locator('textarea[data-testid="code-cell-editor"]').first.wait_for(state="visible", timeout=15000)
        await page.get_by_role("button", name="Shortcuts").first.click()
        dialog = page.get_by_test_id("shortcuts-modal")
        await expect(dialog).to_be_visible()
        await assert_dialog_on_top(page, dialog)

        # Long content scrolls inside the body, the header and close button stay visible
        body = dialog.locator(".pcs-modal-body")
        scroll = await body.evaluate("b => { b.scrollTop = 99999; return [b.scrollHeight > b.clientHeight, b.scrollTop > 0]; }")
        if scroll[0]:
            assert scroll[1], "dialog body must scroll internally"
        close = dialog.get_by_role("button", name="Close")
        await expect(close).to_be_visible()
        await close.click()
        await expect(dialog).to_be_hidden()

        await page.get_by_role("button", name="Shortcuts").first.click()
        await expect(dialog).to_be_visible()
        await page.keyboard.press("Escape")
        await expect(dialog).to_be_hidden()
        assert not errors, errors
        await browser.close()


async def test_all_top_bar_dialogs_render_above_top_bar():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, 1280, 800)
        for opener, testid in [
            ("navbar-notebooks-btn", "notebooks-modal"),
            ("navbar-secrets-btn", "secrets-modal"),
            ("signin-button", "auth-modal"),
        ]:
            await page.get_by_test_id(opener).click()
            backdrop = page.get_by_test_id(testid)
            await expect(backdrop).to_be_visible()
            dialog = backdrop.locator(".pcs-modal")
            await assert_dialog_on_top(page, dialog)
            await page.keyboard.press("Escape")
            await expect(backdrop).to_be_hidden()

        # Explorer dialog (New Folder) uses the same layer
        await page.get_by_role("button", name="Folder").first.click()
        file_dialog = page.get_by_test_id("file-action-modal")
        await expect(file_dialog).to_be_visible()
        await assert_dialog_on_top(page, file_dialog.locator(".pcs-modal"))
        await page.keyboard.press("Escape")
        await expect(file_dialog).to_be_hidden()
        assert not errors, errors
        await browser.close()


async def test_escape_closes_only_the_topmost_dialog():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, 1440, 900)
        await page.get_by_test_id("signin-button").click()
        auth = page.get_by_test_id("auth-modal")
        await page.locator("#auth-email").fill("admin@example.com")
        await page.locator("#auth-password").fill("AdminSecurePassword2026!")
        await auth.locator('button[type="submit"]').click()
        await expect(auth).to_be_hidden(timeout=10000)

        await page.get_by_test_id("admin-panel-btn").click()
        console = page.get_by_test_id("admin-dashboard-modal")
        await expect(console).to_be_visible()
        await assert_dialog_on_top(page, console)

        # Open a sub-dialog (create user) on top of the console; Escape closes only that one
        await console.get_by_role("button", name="User Management").first.click()
        await console.get_by_role("button", name="Add New User").first.click()
        sub = page.locator(".pcs-modal-backdrop").last
        await expect(sub.get_by_text("Create New User", exact=False)).to_be_visible()
        assert await page.locator(".pcs-modal-backdrop").count() == 2
        await page.keyboard.press("Escape")
        await expect(page.locator(".pcs-modal-backdrop")).to_have_count(1)
        await expect(console).to_be_visible()
        await page.keyboard.press("Escape")
        await expect(console).to_be_hidden()
        assert not errors, errors
        await browser.close()


# --- Task 2: top bar ------------------------------------------------------------------------------------

LAYOUT_PROBE = """
() => {
  const h = document.querySelector('header.pcs-topbar');
  const hr = h.getBoundingClientRect();
  const items = [...h.querySelectorAll('.tb-btn, .tb-chip, .tb-brand, .tb-title-input')]
    .filter(e => e.offsetParent !== null).map(e => ({ id: e.dataset.testid || e.className, r: e.getBoundingClientRect() }));
  const overlaps = [];
  for (let i = 0; i < items.length; i++)
    for (let j = i + 1; j < items.length; j++) {
      const a = items[i].r, b = items[j].r;
      if (a.left < b.right - 0.5 && b.left < a.right - 0.5 && a.top < b.bottom - 0.5 && b.top < a.bottom - 0.5)
        overlaps.push(items[i].id + ' x ' + items[j].id);
    }
  return {
    docOverflow: document.documentElement.scrollWidth - innerWidth,
    headerOverflow: h.scrollWidth - h.clientWidth,
    clipped: items.filter(i => i.r.left < hr.left - 0.5 || i.r.right > hr.right + 0.5).map(i => i.id),
    overlaps,
  };
}
"""


@pytest.mark.parametrize("width", [1920, 1440, 1280, 1024, 768, 480, 375, 320])
async def test_top_bar_fits_and_every_control_is_reachable(width):
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, width, 800)
        layout = await page.evaluate(LAYOUT_PROBE)
        assert layout == {"docOverflow": 0, "headerOverflow": 0, "clipped": [], "overlaps": []}, layout

        # Always in the bar
        for testid in ["left-sidebar-toggle", "run-all-btn", "stop-execution-btn", "navbar-restart-btn",
                       "kernel-status", "signin-button", "right-panel-toggle"]:
            await expect(page.get_by_test_id(testid)).to_be_visible()

        # Everything else is either in the bar or in the More menu
        more = page.get_by_test_id("navbar-more-btn")
        if await more.count():
            await more.click()
            await expect(page.get_by_test_id("navbar-more-menu")).to_be_visible()
        for testid in ["clear-outputs-btn", "save-btn", "navbar-notebooks-btn", "navbar-secrets-btn", "navbar-help-btn"]:
            await expect(page.get_by_test_id(testid)).to_be_visible()
        if await more.count():
            menu = await page.get_by_test_id("navbar-more-menu").bounding_box()
            assert menu["x"] >= 0 and menu["x"] + menu["width"] <= width, "More menu must stay inside the viewport"
            await page.keyboard.press("Escape")
            await expect(page.get_by_test_id("navbar-more-menu")).to_be_hidden()

        # Theme switcher: in the bar, or in the More menu on phones
        theme_btn = page.get_by_test_id("theme-toggle-btn")
        if await theme_btn.count():
            await theme_btn.click()
        else:
            await more.click()
        await page.get_by_test_id("theme-option-light").click()
        assert await page.evaluate("document.documentElement.getAttribute('data-theme')") == "light"
        assert not errors, errors
        await browser.close()


async def test_top_bar_menu_actions_work_at_phone_width():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, 375, 667)
        await page.get_by_test_id("navbar-more-btn").click()
        await page.get_by_test_id("navbar-notebooks-btn").click()
        await expect(page.get_by_test_id("notebooks-modal")).to_be_visible()
        await assert_dialog_on_top(page, page.get_by_test_id("notebooks-modal").locator(".pcs-modal"))
        await page.keyboard.press("Escape")
        await expect(page.get_by_test_id("notebooks-modal")).to_be_hidden()

        # Outside click closes the menu
        await page.get_by_test_id("navbar-more-btn").click()
        await expect(page.get_by_test_id("navbar-more-menu")).to_be_visible()
        await page.mouse.click(180, 400)
        await expect(page.get_by_test_id("navbar-more-menu")).to_be_hidden()
        assert not errors, errors
        await browser.close()


async def test_account_menu_holds_admin_and_sign_out():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, 768, 900)
        await page.get_by_test_id("signin-button").click()
        await page.locator("#auth-email").fill("admin@example.com")
        await page.locator("#auth-password").fill("AdminSecurePassword2026!")
        await page.get_by_test_id("auth-modal").locator('button[type="submit"]').click()
        account = page.get_by_test_id("account-menu-btn")
        await expect(account).to_be_visible(timeout=10000)
        layout = await page.evaluate(LAYOUT_PROBE)
        assert layout == {"docOverflow": 0, "headerOverflow": 0, "clipped": [], "overlaps": []}, layout

        await account.click()
        menu = page.get_by_test_id("account-menu")
        await expect(menu).to_be_visible()
        await expect(menu.get_by_test_id("admin-panel-btn")).to_be_visible()
        await menu.get_by_test_id("signout-btn").click()
        await expect(page.get_by_test_id("signin-button")).to_be_visible(timeout=10000)
        await expect(page.get_by_test_id("workspace-indicator-public")).to_be_attached()
        assert not errors, errors
        await browser.close()
