"""
Browser tests for private, browser-persistent guest workspaces:
  - two browsers (separate profiles) never see or change each other's files, notebooks or kernel
  - files, notebook cells and their outputs survive a page refresh
  - when the server has removed a guest workspace, the browser copy (IndexedDB) restores it
  - with browser storage unavailable the app still works and says it keeps no browser copy
  - an invalid stored guest token is replaced automatically

Requires a running server (PCS_E2E_URL, default http://127.0.0.1:8765). The restore test deletes a
guest workspace on disk: PCS_E2E_WORKSPACES must point at the server's workspaces folder (default
./storage/workspaces, i.e. tests run from the server's directory); it is skipped otherwise.
"""
import asyncio
import os
import re
import shutil

import pytest
from playwright.async_api import async_playwright, expect

pytestmark = pytest.mark.asyncio

SERVER_URL = os.environ.get("PCS_E2E_URL", "http://127.0.0.1:8765")
WORKSPACES = os.path.abspath(os.environ.get("PCS_E2E_WORKSPACES", "storage/workspaces"))


async def new_guest(browser, init_script=None):
    """A fresh browser profile (like another person or a private window)."""
    context = await browser.new_context(viewport={"width": 1440, "height": 900})
    if init_script:
        await context.add_init_script(init_script)
    page = await context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    await page.goto(SERVER_URL, wait_until="networkidle")
    await expect(page.locator('[data-testid="kernel-status"][data-status="idle"]')).to_be_visible(timeout=60000)
    return context, page, errors


async def api(page, method, path, body=None):
    return await page.evaluate(
        """async ([m, p, b]) => { const r = await fetch('/api/v1' + p, { method: m,
             headers: { 'X-Guest-Token': localStorage.getItem('pcs_guest_token'), 'Content-Type': 'application/json' },
             body: b ? JSON.stringify(b) : undefined });
           let j = null; try { j = await r.json(); } catch (e) {} return [r.status, j]; }""",
        [method, path, body],
    )


async def wait_in_browser_copy(page, store, key, needle, timeout_s=10):
    """Waits until the browser's IndexedDB copy holds `key` (containing `needle`)."""
    for _ in range(int(timeout_s * 5)):
        found = await page.evaluate(
            """([store, key, needle]) => new Promise(res => { const r = indexedDB.open('pcs-guest-workspace');
                r.onsuccess = () => { const g = r.result.transaction(store).objectStore(store).get(key);
                  g.onsuccess = () => res(!!g.result && (!needle || JSON.stringify(g.result).includes(needle))); };
                r.onerror = () => res(false); })""",
            [store, key, needle])
        if found:
            return
        await asyncio.sleep(0.2)
    raise AssertionError(f"{store}/{key} not in the browser copy")


async def run_in_new_cell(page, code):
    cells = page.get_by_test_id("notebook-cell")
    n = await cells.count()
    await page.get_by_role("button", name="Add Code Cell").click()
    cell = cells.nth(n)
    editor = cell.locator('textarea[data-testid="code-cell-editor"]')
    await editor.fill(code)
    await page.keyboard.press("Escape")
    await cell.get_by_test_id("cell-run-btn").click()
    await expect(cell.locator(".cell-header").first).to_contain_text(re.compile(r"\[\d+\]"), timeout=60000)
    return cell


async def test_two_guests_are_isolated():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx_a, a, errors_a = await new_guest(browser)
        ctx_b, b, errors_b = await new_guest(browser)
        token_a = await a.evaluate("localStorage.getItem('pcs_guest_token')")
        token_b = await b.evaluate("localStorage.getItem('pcs_guest_token')")
        assert token_a and token_b and token_a != token_b
        assert re.fullmatch(r"gst_[\w-]+\.[0-9a-f]{32}", token_a), "server-issued, signed token"
        await expect(a.get_by_test_id("workspace-indicator-public")).to_contain_text("Private Workspace")

        # A's work
        assert (await api(a, "POST", "/files/write", {"path": "only_a.py", "content": "A = 1"}))[0] == 200
        st, nb = await api(a, "POST", "/notebooks", {"title": "Only A"})
        await run_in_new_cell(a, "secret_a = 'from A'")

        # B sees none of it, in the explorer or the API
        await b.reload(wait_until="networkidle")
        await expect(b.locator('[data-testid="file-tree-item"][data-path="only_a.py"]')).to_have_count(0)
        assert (await api(b, "GET", "/files/read?path=only_a.py"))[0] == 404
        assert all(n["title"] != "Only A" for n in (await api(b, "GET", "/notebooks"))[1])
        assert (await api(b, "GET", f"/notebooks/{nb['id']}"))[0] == 404
        cell_b = await run_in_new_cell(b, "print(secret_a)")
        await expect(cell_b.get_by_test_id("cell-output-container")).to_contain_text("NameError")

        # B changes its own workspace; A is unaffected
        assert (await api(b, "POST", "/files/write", {"path": "only_a.py", "content": "B wrote this"}))[0] == 200
        st, content = await api(a, "GET", "/files/read?path=only_a.py")
        assert content["content"] == "A = 1"

        # The old shared fallback is gone
        status = await a.evaluate("fetch('/api/v1/files').then(r => r.status)")
        assert status == 401
        assert not errors_a and not errors_b, errors_a + errors_b
        await api(a, "DELETE", "/files?path=only_a.py")
        await browser.close()


async def test_work_survives_refresh():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx, page, errors = await new_guest(browser)
        await api(page, "POST", "/files/write", {"path": "kept.py", "content": "kept = True"})
        cell = await run_in_new_cell(page, "print('persisted output')\nvalue = 7")
        await expect(cell.get_by_test_id("cell-output-container")).to_contain_text("persisted output")
        await page.keyboard.press("Control+s")
        await page.wait_for_timeout(1500)
        count = await page.get_by_test_id("notebook-cell").count()

        await page.reload(wait_until="networkidle")
        await expect(page.locator('[data-testid="kernel-status"][data-status="idle"]')).to_be_visible(timeout=60000)
        await expect(page.locator('[data-testid="file-tree-item"][data-path="kept.py"]')).to_be_visible()
        await expect(page.get_by_test_id("notebook-cell")).to_have_count(count)
        last = page.get_by_test_id("notebook-cell").nth(count - 1)
        await expect(last.locator('textarea[data-testid="code-cell-editor"]')).to_have_value("print('persisted output')\nvalue = 7")
        await expect(last.get_by_test_id("cell-output-container")).to_contain_text("persisted output")
        # The browser copy has the file and the notebook
        snap = await page.evaluate("""() => new Promise(res => { const r = indexedDB.open('pcs-guest-workspace');
            r.onsuccess = () => { const db = r.result; const t = db.transaction(['files', 'notebooks']);
              const f = t.objectStore('files').getAll(); const n = t.objectStore('notebooks').getAll();
              t.oncomplete = () => res({ files: f.result.map(x => x.path), notebooks: n.result.length }); }; })""")
        assert "kept.py" in snap["files"] and snap["notebooks"] >= 1
        await last.get_by_title("Delete Cell").click()
        await api(page, "DELETE", "/files?path=kept.py")
        assert not errors, errors
        await browser.close()


async def test_server_cleanup_is_restored_from_the_browser():
    guests_root = os.path.join(WORKSPACES, "guests")
    if not os.path.isdir(guests_root):
        pytest.skip(f"server workspaces folder not found at {WORKSPACES} (set PCS_E2E_WORKSPACES)")
    from services.api.guest_workspace import guest_workspace_id

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx, page, errors = await new_guest(browser)
        # Files written on the server (as Python code would) reach the browser copy when listed
        await api(page, "POST", "/files/folder", {"path": "analysis"})
        await api(page, "POST", "/files/write", {"path": "analysis/report.py", "content": "print('restored!')"})
        await page.evaluate("window.dispatchEvent(new CustomEvent('pcs-refresh-files'))")
        await expect(page.locator('[data-testid="file-tree-item"][data-path="analysis"]')).to_be_visible()
        # The open notebook, with a new cell, saved by the app
        cell = await run_in_new_cell(page, "print('kept cell')")
        await page.keyboard.press("Control+s")
        nb_id = await page.evaluate("localStorage.getItem('pcs_active_notebook_id')")
        await wait_in_browser_copy(page, "notebooks", nb_id, "kept cell")
        await wait_in_browser_copy(page, "files", "analysis/report.py", "")

        # The guest leaves; the server stops the kernel and later removes the workspace (as its idle
        # cleanup does: it never removes a workspace whose kernel is still running)
        token = await page.evaluate("localStorage.getItem('pcs_guest_token')")
        ws = guest_workspace_id(token)
        assert ws
        await page.close()
        import httpx
        async with httpx.AsyncClient(base_url=SERVER_URL + "/api/v1", headers={"X-Guest-Token": token}) as http:
            for s in (await http.get("/execution/sessions")).json():
                await http.post("/execution/control", json={"session_id": s["session_id"], "action": "shutdown"})
        for _ in range(50):
            shutil.rmtree(os.path.join(guests_root, ws), ignore_errors=True)
            if not os.path.exists(os.path.join(guests_root, ws)):
                break
            await asyncio.sleep(0.2)
        assert not os.path.exists(os.path.join(guests_root, ws))
        shutil.rmtree(os.path.join(guests_root, f"{ws}.notebooks"), ignore_errors=True)
        os.remove(os.path.join(guests_root, f"{ws}.meta.json"))

        # The guest comes back in the same browser
        page = await ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        await page.goto(SERVER_URL, wait_until="networkidle")
        await expect(page.get_by_test_id("kernel-toast-banner")).to_contain_text("restored from this browser", timeout=20000)
        st, content = await api(page, "GET", "/files/read?path=analysis/report.py")
        assert st == 200 and content["content"] == "print('restored!')"
        st, nb = await api(page, "GET", f"/notebooks/{nb_id}")
        assert st == 200 and "kept cell" in str(nb)
        await expect(page.locator('textarea[data-testid="code-cell-editor"]').last).to_have_value("print('kept cell')")
        # Only the files and cells come back: the Python process itself was not restored
        await expect(page.locator('[data-testid="kernel-status"][data-status="idle"]')).to_be_visible(timeout=60000)
        assert not errors, errors
        await browser.close()


async def test_without_browser_storage_the_app_still_works():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx, page, errors = await new_guest(browser, init_script="Object.defineProperty(window, 'indexedDB', { value: undefined });")
        await expect(page.get_by_test_id("guest-privacy-banner")).to_contain_text("cannot keep a copy")
        await api(page, "POST", "/files/write", {"path": "no_idb.py", "content": "x = 1"})
        cell = await run_in_new_cell(page, "print(6 * 7)")
        await expect(cell.get_by_test_id("cell-output-container")).to_contain_text("42")
        await cell.get_by_title("Delete Cell").click()
        await api(page, "DELETE", "/files?path=no_idb.py")
        assert not errors, errors
        await browser.close()


async def test_invalid_stored_token_is_replaced():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # An old-style token the browser made up itself (earlier versions) or a forged one
        ctx, page, errors = await new_guest(browser, init_script="if (!sessionStorage.getItem('seeded')) { localStorage.setItem('pcs_guest_token', 'gst_madeupbyclient'); sessionStorage.setItem('seeded', '1'); }")
        token = await page.evaluate("localStorage.getItem('pcs_guest_token')")
        assert token != "gst_madeupbyclient" and re.fullmatch(r"gst_[\w-]+\.[0-9a-f]{32}", token)
        await expect(page.get_by_test_id("notebook-cell").first).to_be_visible()
        assert not errors, errors
        await browser.close()
