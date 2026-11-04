"""
Browser tests for notebook outputs and syntax highlighting:
  - pandas DataFrames keep their real column names (pivot tables with a named index used to show
    Col_1, Col_2, ...), index names, column-axis names, MultiIndex columns/rows and the true shape
  - Styler, display(HTML(...)) with scripts, Markdown and LaTeX render in a sandboxed frame: scripts
    run there but cannot reach the app (login token, DOM); inline event handlers cannot run in the app
  - matplotlib figures, clear_output(wait=True), display handles (update), ANSI-coloured tracebacks
  - Python syntax colours follow every edit immediately, including Ctrl+/ and undo; bracket matching

Requires a running server (default http://127.0.0.1:8765, override with PCS_E2E_URL) whose kernel has
pandas, numpy and matplotlib. Markdown/LaTeX rendering loads marked/KaTeX from a CDN and is skipped
when the CDN is unreachable.
"""
import os
import re

import pytest
from playwright.async_api import async_playwright, expect

import cm_helpers as cm

pytestmark = pytest.mark.asyncio

SERVER_URL = os.environ.get("PCS_E2E_URL", "http://127.0.0.1:8765")

PIVOT_CODE = """
import pandas as pd, numpy as np
rng = np.random.default_rng(0)
dates = pd.date_range('2020-01-01', '2025-03-31', freq='D')
df = pd.DataFrame({'Order_Date': dates, 'Amount': rng.integers(100, 1000, len(dates))})
df['Year'] = df['Order_Date'].dt.year
month_order = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
df['Month'] = pd.Categorical(df['Order_Date'].dt.strftime('%b'), categories=month_order, ordered=True)
monthly_pivot = pd.pivot_table(df, index='Year', columns='Month', values='Amount', aggfunc='sum', observed=False, fill_value=0)
monthly_pivot.columns = monthly_pivot.columns.astype(str)
monthly_pivot.columns.name = None
display(monthly_pivot)
"""
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


async def open_studio(p, width=1440, height=900):
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": width, "height": height})
    page = await context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    await page.goto(SERVER_URL, wait_until="networkidle")
    await page.locator('textarea[data-testid="code-cell-editor"]').first.wait_for(state="visible", timeout=15000)
    await expect(page.locator('[data-testid="kernel-status"][data-status="idle"]')).to_be_visible(timeout=30000)
    return browser, page, errors


async def run_code(page, code, timeout=60000):
    """Adds a code cell with `code`, runs it and waits until it finishes. Returns the cell."""
    cells = page.get_by_test_id("notebook-cell")
    index = await cells.count()
    await page.get_by_role("button", name="Add Code Cell").click()
    cell = cells.nth(index)
    editor = cell.locator('textarea[data-testid="code-cell-editor"]')
    await editor.fill(code.strip())
    await page.keyboard.press("Escape")
    await cell.get_by_test_id("cell-run-btn").click()
    # Finished: the cell shows its execution count ([N]); fast cells may never be seen running
    await expect(cell.locator(".cell-header").first).to_contain_text(re.compile(r"\[\d+\]"), timeout=timeout)
    await expect(cell.get_by_test_id("cell-run-btn")).to_have_attribute("aria-label", "Run cell", timeout=timeout)
    return cell


async def delete_cell(cell):
    await cell.get_by_title("Delete Cell").click()


async def column_headers(cell):
    return [t.strip() for t in await cell.get_by_test_id("dataframe-column-header").all_inner_texts()]


def output_frame(page, cell, index=0):
    return cell.get_by_test_id("output-frame").nth(index)


async def frame_of(page, cell, index=0):
    handle = await output_frame(page, cell, index).element_handle()
    frame = await handle.content_frame()
    await frame.wait_for_load_state()
    return frame


async def cdn_reachable(page):
    try:
        r = await page.request.get("https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js", timeout=8000)
        return r.ok
    except Exception:
        return False


# --- DataFrames ---------------------------------------------------------------------------------------


async def test_pivot_table_keeps_real_column_names():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        cell = await run_code(page, PIVOT_CODE)
        table = cell.get_by_test_id("interactive-data-table")
        await expect(table).to_be_visible()
        headers = await column_headers(cell)
        # columns.name was cleared, so the corner is empty; the index name has its own row (as in Jupyter)
        assert headers == [""] + MONTHS, headers
        assert not any(h.startswith("Col_") for h in headers)
        await expect(cell.get_by_test_id("dataframe-index-names")).to_contain_text("Year")
        assert await cell.get_by_test_id("dataframe-index-cell").count() == 6
        text = await table.inner_text()
        assert "6 rows × 12 columns" in text.replace("\n", " "), text[:200]
        # Index values and a known value layout: 6 years
        assert "2020" in text and "2025" in text
        await delete_cell(cell)
        assert not errors, errors
        await browser.close()


async def test_column_axis_name_multiindex_and_truncation():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)

        # Column-axis name kept (no index name): shown in the index corner like Jupyter
        cell = await run_code(page, """
import pandas as pd
df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]}, index=['x', 'y'])
df.columns.name = 'Letters'
display(df)
""")
        assert await column_headers(cell) == ["Letters", "a", "b"]
        await delete_cell(cell)

        # MultiIndex columns and rows: upper level as a header band, full labels kept, row index repeated
        cell = await run_code(page, """
import pandas as pd, numpy as np
cols = pd.MultiIndex.from_product([['Sales', 'Cost'], ['Q1', 'Q2']], names=['metric', 'quarter'])
idx = pd.MultiIndex.from_product([['North', 'South'], [2024, 2025]], names=['region', 'year'])
display(pd.DataFrame(np.arange(16).reshape(4, 4), index=idx, columns=cols))
""")
        band = cell.get_by_test_id("dataframe-header-band")
        await expect(band.first).to_be_visible()
        band_text = await band.first.inner_text()
        assert "Sales" in band_text and "Cost" in band_text
        # Corner of the leaf row: the column level name; index names on their own row
        assert await column_headers(cell) == ["", "quarter", "Q1", "Q2", "Q1", "Q2"]
        names = await cell.get_by_test_id("dataframe-index-names").locator("th").all_inner_texts()
        assert [n.strip() for n in names[:2]] == ["region", "year"]
        body = await cell.locator("tbody").inner_text()
        assert body.count("North") == 2 and body.count("South") == 2, body  # rowspan values repeated per row
        await delete_cell(cell)

        # Truncated frame: the real shape from pandas, not the visible row count
        cell = await run_code(page, """
import pandas as pd
pd.set_option('display.max_rows', 10)
display(pd.DataFrame({'n': range(1000), 'sq': [i * i for i in range(1000)]}))
pd.reset_option('display.max_rows')
""")
        text = (await cell.get_by_test_id("interactive-data-table").inner_text()).replace("\n", " ")
        assert "1,000 rows × 2 columns" in text, text[:200]
        assert "showing" in text
        await delete_cell(cell)
        assert not errors, errors
        await browser.close()


async def test_styler_renders_with_its_styles_in_sandbox():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        cell = await run_code(page, """
import pandas as pd
df = pd.DataFrame({'Jan': [1, 5], 'Feb': [3, 2]}, index=pd.Index([2024, 2025], name='Year'))
display(df.style.highlight_max(color='rgb(255, 0, 0)'))
""")
        await expect(output_frame(page, cell)).to_have_attribute("data-mime", "text/html")
        frame = await frame_of(page, cell)
        await expect(frame.locator("table")).to_be_visible()
        headers = await frame.locator("thead th").all_inner_texts()
        assert "Jan" in headers and "Feb" in headers
        # The Styler's CSS applies: the max cell has the red background
        reds = await frame.evaluate("""() => [...document.querySelectorAll('td')]
            .filter(td => getComputedStyle(td).backgroundColor === 'rgb(255, 0, 0)').length""")
        assert reds >= 2
        height = (await output_frame(page, cell).bounding_box())["height"]
        assert height > 40, "frame grows to its content"
        await delete_cell(cell)
        assert not errors, errors
        await browser.close()


# --- Isolation ----------------------------------------------------------------------------------------


async def test_html_output_scripts_run_sandboxed_and_cannot_reach_app():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        token_before = await page.evaluate("localStorage.getItem('pcs_token') || localStorage.getItem('pcs_guest_token')")
        cell = await run_code(page, """
from IPython.display import HTML, display
display(HTML('''<div id="probe">waiting</div>
<script>
var r = [];
try { r.push(parent.localStorage.getItem('pcs_token') === null ? 'storage:null' : 'storage:LEAK'); } catch (e) { r.push('storage:blocked'); }
try { parent.document.body.setAttribute('data-pwned', '1'); r.push('dom:LEAK'); } catch (e) { r.push('dom:blocked'); }
try { r.push(document.cookie === '' ? 'cookie:none' : 'cookie:readable'); } catch (e) { r.push('cookie:blocked'); }
try { localStorage.setItem('k', 'v'); r.push(localStorage.getItem('k') === 'v' ? 'own-storage:ok' : 'own-storage:broken'); } catch (e) { r.push('own-storage:throws'); }
document.getElementById('probe').textContent = 'ran ' + r.join(' ');
</script>'''))
display(HTML('<img src="x" onerror="window.top.__pwned = 1"><b>inline handler</b>'))
""")
        frame = await frame_of(page, cell, 0)
        await expect(frame.locator("#probe")).to_contain_text("ran", timeout=10000)
        probe = await frame.locator("#probe").inner_text()
        assert "storage:blocked" in probe and "dom:blocked" in probe, probe
        assert "own-storage:ok" in probe, probe  # libraries can use storage inside the sandbox
        assert "cookie:blocked" in probe or "cookie:none" in probe, probe  # never the app's cookies
        assert await page.evaluate("document.body.getAttribute('data-pwned')") is None
        await page.wait_for_timeout(500)
        assert await page.evaluate("window.__pwned === undefined"), "inline event handler must not run in the app"
        assert await page.evaluate("localStorage.getItem('pcs_token') || localStorage.getItem('pcs_guest_token')") == token_before
        # The inline handler did run, inside the sandboxed frame, where the browser blocked it
        assert any("origin \"null\"" in e and "cross-origin" in e for e in errors), errors
        await delete_cell(cell)
        await browser.close()


# --- Other rich outputs -------------------------------------------------------------------------------


async def test_markdown_and_latex_outputs():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        if not await cdn_reachable(page):
            await browser.close()
            pytest.skip("marked/KaTeX CDN not reachable from this machine")
        cell = await run_code(page, r"""
from IPython.display import Markdown, Latex, display
display(Markdown('# Report\n\n**bold** and a list:\n\n- one\n- two\n\nInline math $x^2 + 1$'))
display(Latex(r'$$\frac{a}{b} = \sqrt{c}$$'))
""")
        md = await frame_of(page, cell, 0)
        await expect(md.locator("h1")).to_have_text("Report", timeout=15000)
        await expect(md.locator("strong")).to_have_text("bold")
        await expect(md.locator("li")).to_have_count(2)
        await expect(md.locator(".katex").first).to_be_visible(timeout=15000)
        latex = await frame_of(page, cell, 1)
        await expect(latex.locator(".katex-display")).to_be_visible(timeout=15000)
        await delete_cell(cell)
        assert not errors, errors
        await browser.close()


async def test_plotly_figure_renders_interactively():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        if not await cdn_reachable(page):
            await browser.close()
            pytest.skip("Plotly CDN not reachable from this machine")
        cell = await run_code(page, """
import plotly.express as px
px.bar(x=['a', 'b', 'c'], y=[3, 1, 2], title='plotly bar').show()
""")
        await expect(output_frame(page, cell)).to_have_attribute("data-mime", "application/vnd.plotly.v1+json")
        frame = await frame_of(page, cell)
        await expect(frame.locator(".plot-container .main-svg").first).to_be_visible(timeout=20000)
        await expect(frame.locator(".modebar")).to_have_count(1)  # Plotly's interactive toolbar
        await delete_cell(cell)
        assert not errors, errors
        await browser.close()


async def test_matplotlib_clear_output_display_update_and_ansi_traceback():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)

        cell = await run_code(page, """
import matplotlib.pyplot as plt
plt.plot([1, 3, 2]); plt.title('chart'); plt.show()
""")
        await expect(cell.get_by_test_id("plot-output-container").locator("img")).to_be_visible()
        await delete_cell(cell)

        # clear_output(wait=True): only the last value remains (progress-style loops)
        cell = await run_code(page, """
from IPython.display import clear_output
import time
for i in range(5):
    clear_output(wait=True)
    print('step', i)
    time.sleep(0.05)
""")
        out = cell.get_by_test_id("cell-output-container")
        await expect(out).to_have_text("step 4")
        await delete_cell(cell)

        # Display handles: update() replaces the earlier output in place
        cell = await run_code(page, """
h = display('first', display_id=True)
print('between')
h.update('second')
""")
        text = await cell.get_by_test_id("cell-output-container").inner_text()
        assert "second" in text and "first" not in text and "between" in text, text
        await delete_cell(cell)

        # Tracebacks: ANSI colours rendered, no raw escape codes
        cell = await run_code(page, "def f():\n    return 1 / 0\nf()")
        tb = await cell.get_by_test_id("cell-output-container").inner_text()
        assert "ZeroDivisionError" in tb
        assert "\x1b[" not in tb and "[0;31m" not in tb and "[1;31m" not in tb, tb[:300]
        colored = await cell.get_by_test_id("cell-output-container").locator("pre span[style*='color']").count()
        assert colored > 0
        await delete_cell(cell)
        assert not errors, errors
        await browser.close()


# --- Syntax highlighting ------------------------------------------------------------------------------


async def test_syntax_colors_follow_edits_ctrl_slash_and_undo():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        cells = page.get_by_test_id("notebook-cell")
        index = await cells.count()
        await page.get_by_role("button", name="Add Code Cell").click()
        cell = cells.nth(index)
        editor = cell.locator('textarea[data-testid="code-cell-editor"]')
        await editor.fill("def total(xs):\n    return sum(xs)  # add up\nprint('hi', 42)")
        await page.keyboard.press("Escape")
        layer = cell.get_by_test_id("code-highlight-layer")
        await expect(layer.locator(".tok-keyword", has_text="def")).to_be_visible()
        await expect(layer.locator(".tok-function", has_text="total")).to_be_visible()
        await expect(layer.locator(".tok-builtin", has_text="sum")).to_be_visible()
        await expect(layer.locator(".tok-comment")).to_have_text("# add up")
        await expect(layer.locator(".tok-string")).to_have_text("'hi'")
        await expect(layer.locator(".tok-number")).to_have_text("42")
        # The textarea's own text is invisible; the layer draws it with the same metrics
        assert await editor.evaluate("el => getComputedStyle(el).color") == "rgba(0, 0, 0, 0)"
        line_tops = await layer.evaluate("l => [...l.children].map(d => d.offsetTop)")
        line_h = await editor.evaluate("el => parseFloat(getComputedStyle(el).lineHeight)")
        assert line_tops[:3] == [10, 10 + line_h, 10 + 2 * line_h], (line_tops, line_h)

        # Ctrl+/ comments line 3: it is coloured as a comment immediately, and undo restores the colours
        await editor.evaluate("el => { el.focus(); const p = el.value.lastIndexOf('print'); el.setSelectionRange(p, p); }")
        await page.keyboard.press("Control+/")
        await expect(layer.locator(".tok-comment", has_text="# print('hi', 42)")).to_be_visible()
        await expect(layer.locator(".tok-string")).to_have_count(0)
        await page.keyboard.press("Control+z")
        await expect(layer.locator(".tok-string")).to_have_text("'hi'")
        await expect(layer.locator(".tok-comment")).to_have_text("# add up")

        # Bracket matching: caret after "(" outlines both brackets of that pair
        await editor.evaluate("el => { el.focus(); const p = el.value.indexOf('('); el.setSelectionRange(p, p); }")
        await page.keyboard.press("ArrowRight")  # caret just after "(" (a real caret move)
        await expect(layer.locator(".tok-bracket-match")).to_have_count(2)
        await expect(layer.locator(".tok-bracket-match").first).to_have_text("(")

        # Horizontal scrolling keeps the colours aligned with the text
        await editor.fill("x = '" + "a" * 400 + "'")
        await editor.evaluate("el => { el.scrollLeft = 200; el.dispatchEvent(new Event('scroll')); }")
        assert await layer.evaluate("l => l.scrollLeft") == await editor.evaluate("el => el.scrollLeft")
        await delete_cell(cell)
        assert not errors, errors
        await browser.close()


async def test_file_editor_highlights_python_files():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        if await page.get_by_test_id("left-resizer").count() == 0:
            await page.get_by_test_id("left-sidebar-toggle").click()
        await page.locator('[data-testid="file-tree-item"][data-path$="main.py"]').first.dblclick()
        await cm.wait_for_editor(page)
        original = await cm.doc(page)
        await cm.set_doc(page, "import sys\nvalue = 1  # note\n")
        color = lambda text: page.locator(".cm-line span", has_text=text).first.evaluate("e => getComputedStyle(e).color")
        keyword, number, comment = await color("import"), await color("1"), await color("# note")
        assert len({keyword, number, comment}) == 3, (keyword, number, comment)
        # Ctrl+/ on "import sys": the line is coloured as a comment immediately
        await cm.set_cursor(page, 0)
        await page.keyboard.press("Control+/")
        assert (await cm.doc(page)).startswith("# import sys")
        assert await color("# import sys") == comment
        await page.keyboard.press("Control+z")
        assert await color("import") == keyword
        # Leave the file as it was (nothing saved)
        await cm.set_doc(page, original)
        assert not errors, errors
        await browser.close()
