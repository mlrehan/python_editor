"""Helpers for driving the file editor (CodeMirror 6) from Playwright tests.

The editor exposes its EditorView on its root element as `cmView`, so tests can read the document
and the selection exactly, and place the caret, without depending on CodeMirror's DOM details.
"""

VIEW = "document.querySelector('[data-testid=file-code-editor] .cm-editor').cmView"


async def wait_for_editor(page, timeout=15000):
    await page.get_by_test_id("file-editor-content").wait_for(state="visible", timeout=timeout)


async def doc(page) -> str:
    return await page.evaluate(f"{VIEW}.state.doc.toString()")


async def selection(page):
    """[anchor, head] of the main selection."""
    return await page.evaluate(f"(() => {{ const s = {VIEW}.state.selection.main; return [s.anchor, s.head]; }})()")


async def set_cursor(page, anchor, head=None):
    await page.evaluate(
        f"([a, h]) => {{ const v = {VIEW}; v.focus(); v.dispatch({{ selection: {{ anchor: a, head: h ?? a }}, scrollIntoView: true }}); }}",
        [anchor, head],
    )


async def set_doc(page, text):
    """Replaces the whole document as one user edit."""
    await page.evaluate(
        f"t => {{ const v = {VIEW}; v.dispatch({{ changes: {{ from: 0, to: v.state.doc.length, insert: t }} }}); }}",
        text,
    )
    # A pause, as after a real edit: CodeMirror groups changes made within 500 ms into one undo step
    await page.wait_for_timeout(600)
