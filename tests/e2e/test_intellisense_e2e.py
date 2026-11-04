"""
Browser tests for the notebook code editor's IntelliSense and DataFrame display:
  - caret navigation through (), [], {}, '' and "" with auto-pairing; matching brackets get a subtle box
    only around the pair next to the caret; moving the caret closes suggestions (Enter then inserts a
    newline, not a stale suggestion)
  - DataFrame column suggestions from the live kernel: all columns (no cap), several DataFrames,
    df[ / df[' / df[" / df.loc[:, / df.groupby(', special names, updates after columns change,
    case-insensitive filtering, a clear notice for undefined names; no effect on the execution count
  - function documentation: signature, active parameter (positional or keyword), sections, examples;
    a details panel for the selected suggestion; an explicit message when there is no docstring
  - pivot tables: column-axis name in the corner, index names on their own row, index values as
    distinct row headers that stay visible while scrolling sideways

Requires a running server (default http://127.0.0.1:8765, override with PCS_E2E_URL) with pandas.
"""
import os
import re

import pytest
from playwright.async_api import async_playwright, expect

pytestmark = pytest.mark.asyncio

SERVER_URL = os.environ.get("PCS_E2E_URL", "http://127.0.0.1:8765")

FRAMES = """
import pandas as pd, numpy as np
cols = ['OrderID', 'Order Date', 'CustomerName', 'Sub-Category', "Bob's Pick", 'Discount %', 2024] + [f'Extra_{i}' for i in range(70)]
sales_df = pd.DataFrame([[0] * len(cols)], columns=cols)
customer = pd.DataFrame({'id': [1], 'name': ['a'], 'City': ['x']})
lookup = {'not': 'a dataframe'}
"""


async def open_studio(p, width=1440, height=1000, theme=None):
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": width, "height": height})
    if theme:
        # Init scripts also run in the sandboxed output frames, where storage is off limits: top page only
        await context.add_init_script(f"if (window.top === window) localStorage.setItem('pcs_theme', '{theme}')")
    page = await context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    await page.goto(SERVER_URL, wait_until="networkidle")
    await page.locator('textarea[data-testid="code-cell-editor"]').first.wait_for(state="visible", timeout=15000)
    await expect(page.locator('[data-testid="kernel-status"][data-status="idle"]')).to_be_visible(timeout=30000)
    if await page.get_by_test_id("mobile-left-backdrop").count():
        await page.mouse.click(width - 10, height // 2)
    return browser, page, errors


async def add_cell(page, code=""):
    cells = page.get_by_test_id("notebook-cell")
    index = await cells.count()
    await page.get_by_role("button", name="Add Code Cell").click()
    cell = cells.nth(index)
    editor = cell.locator('textarea[data-testid="code-cell-editor"]')
    await editor.wait_for()
    if code:
        await editor.fill(code.strip())
        await page.keyboard.press("Escape")
    return cell, editor


async def run(cell, timeout=60000):
    await cell.get_by_test_id("cell-run-btn").click()
    await expect(cell.locator(".cell-header").first).to_contain_text(re.compile(r"\[\d+\]"), timeout=timeout)
    await expect(cell.get_by_test_id("cell-run-btn")).to_have_attribute("aria-label", "Run cell", timeout=timeout)


async def type_in(page, editor, text):
    await editor.click()
    await editor.evaluate("el => el.setSelectionRange(el.value.length, el.value.length)")
    await page.keyboard.type(text, delay=40)


async def caret(editor):
    return await editor.evaluate("el => el.selectionStart")


# --- 1. Caret navigation in brackets and quotes -------------------------------------------------------


async def test_caret_moves_naturally_through_brackets_and_quotes():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, theme="light")
        cell, editor = await add_cell(page)
        layer = cell.get_by_test_id("code-highlight-layer")
        kb = page.keyboard
        await editor.click()
        for opener, closer in [("(", ")"), ("[", "]"), ("{", "}"), ("'", "'"), ('"', '"')]:
            await editor.fill("x = ")
            await editor.evaluate("el => el.setSelectionRange(4, 4)")
            await kb.type(opener)
            assert await editor.input_value() == f"x = {opener}{closer}", opener
            assert await caret(editor) == 5
            await kb.press("ArrowRight")
            assert await caret(editor) == 6, f"ArrowRight out of {opener}{closer}"
            await kb.press("ArrowLeft")
            await kb.press("ArrowLeft")
            assert await caret(editor) == 4, f"ArrowLeft before {opener}"
            await kb.press("ArrowRight")
            assert await caret(editor) == 5
            await kb.type("a")
            await kb.type(closer)  # typing the closer steps over the auto-inserted one
            assert await editor.input_value() == f"x = {opener}a{closer}"
            assert await caret(editor) == 7
        await page.keyboard.press("Escape")

        # The bracket box follows the caret: around the pair next to it, gone elsewhere
        await editor.fill("f(1, (2))")
        await editor.evaluate("el => { el.focus(); el.setSelectionRange(5, 5); }")  # after the inner "("
        await kb.press("ArrowLeft")
        await kb.press("ArrowRight")
        await expect(layer.locator(".tok-bracket-match")).to_have_count(2)
        positions = await layer.locator(".tok-bracket-match").all_inner_texts()
        assert positions == ["(", ")"]
        await kb.press("ArrowRight")  # between "2" and ")": the inner pair
        await expect(layer.locator(".tok-bracket-match")).to_have_count(2)
        await editor.evaluate("el => el.setSelectionRange(2, 2)")  # after "1": not next to a bracket
        await kb.press("ArrowRight")
        await expect(layer.locator(".tok-bracket-match")).to_have_count(0)
        style = await page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--syn-bracket-match-border').trim()")
        assert style and style.lower() != "#2563eb", "box colour must differ from the caret colour"
        await cell.get_by_title("Delete Cell").click()
        assert not errors, errors
        await browser.close()


async def test_moving_caret_closes_suggestions_so_enter_inserts_newline():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        cell, editor = await add_cell(page)
        await type_in(page, editor, "pri")
        dropdown = page.get_by_test_id("autocomplete-dropdown")
        await expect(dropdown).to_be_visible(timeout=8000)
        await page.keyboard.press("ArrowLeft")
        await expect(dropdown).to_have_count(0)
        await page.keyboard.press("End")
        await page.keyboard.press("Enter")
        assert await editor.input_value() == "pri\n", await editor.input_value()
        await cell.get_by_title("Delete Cell").click()
        assert not errors, errors
        await browser.close()


# --- 2. Runtime DataFrame column suggestions ----------------------------------------------------------


async def test_dataframe_columns_from_live_kernel():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        setup, _ = await add_cell(page, FRAMES)
        await run(setup)
        count_after_setup = await setup.locator(".cell-header").first.inner_text()

        cell, editor = await add_cell(page)
        dropdown = page.get_by_test_id("autocomplete-dropdown")
        options = dropdown.locator('[role="option"]')

        # df[ : every column (77, more than the old 50 cap), quoted keys inserted
        await type_in(page, editor, "sales_df[")
        await expect(options).to_have_count(77, timeout=10000)
        await expect(dropdown).to_contain_text("COLUMNS (77)")
        assert (await options.first.inner_text()).startswith("OrderID")
        await page.keyboard.press("Enter")
        assert await editor.input_value() == "sales_df['OrderID']"
        assert await caret(editor) == len("sales_df['OrderID'")

        # Inside quotes, case-insensitive filtering, special names inserted escaped
        await editor.fill("")
        await type_in(page, editor, "sales_df['bob")
        await expect(options).to_have_count(1, timeout=8000)
        await page.keyboard.press("Enter")
        assert await editor.input_value() == "sales_df['Bob\\'s Pick']"
        await editor.fill("")
        await type_in(page, editor, 'sales_df["disc')
        await expect(options).to_have_count(1, timeout=8000)
        await page.keyboard.press("Tab")
        assert await editor.input_value() == 'sales_df["Discount %"]'

        # A different DataFrame, .loc column position, a column method
        await editor.fill("")
        await type_in(page, editor, "customer.loc[:, '")
        await expect(options).to_have_count(3, timeout=8000)
        assert [o.split("\n")[0] for o in await options.all_inner_texts()] == ["id", "name", "City"]
        await page.keyboard.press("Escape")
        await editor.fill("")
        await type_in(page, editor, "customer.groupby('ci")
        await expect(options).to_have_count(1, timeout=8000)
        # Columns and the signature help together, as in VS Code
        await expect(page.get_by_test_id("signature-help-tooltip")).to_contain_text("groupby(", timeout=8000)
        await page.keyboard.press("Escape")
        await page.keyboard.press("Escape")

        # Not defined: a notice instead of silence; not a DataFrame: no column list
        await editor.fill("")
        await type_in(page, editor, "orders['")
        await expect(page.get_by_test_id("completion-notice")).to_contain_text("orders is not defined yet", timeout=8000)
        await page.keyboard.press("Escape")
        await editor.fill("")
        await type_in(page, editor, "lookup['")
        await page.wait_for_timeout(1200)
        shown = await dropdown.inner_text() if await dropdown.count() else ""
        assert shown == "", f"unexpected suggestions for lookup[': {shown!r} (code {await editor.input_value()!r})"

        # Columns follow the runtime: add one, run, suggestions update
        await editor.fill("customer['Revenue'] = 5")
        await run(cell)
        await editor.fill("")
        await type_in(page, editor, "customer['")
        await expect(options).to_have_count(4, timeout=8000)
        await expect(options.last).to_contain_text("Revenue")
        await page.keyboard.press("Escape")

        # Introspection left no trace: the setup cell's count is unchanged and the next run is +1
        assert await setup.locator(".cell-header").first.inner_text() == count_after_setup
        n = int(re.search(r"\[(\d+)\]", count_after_setup).group(1))
        await expect(cell.locator(".cell-header").first).to_contain_text(f"[{n + 1}]")
        await cell.get_by_title("Delete Cell").click()
        await setup.get_by_title("Delete Cell").click()
        assert not errors, errors
        await browser.close()


# --- 3. Documentation ---------------------------------------------------------------------------------


async def test_signature_documentation_and_details_panel():
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p)
        setup, _ = await add_cell(page, "import pandas as pd\npv = pd.DataFrame({'a': [1]})\ndef mine(x, y=2):\n    return x")
        await run(setup)
        cell, editor = await add_cell(page)
        await type_in(page, editor, "pv.reindex(")
        tip = page.get_by_test_id("signature-help-tooltip")
        await expect(tip).to_be_visible(timeout=8000)
        await expect(tip.locator(".doc-heading", has_text="Parameters")).to_be_visible()
        await expect(tip.locator(".doc-heading", has_text="Returns")).to_be_visible()
        await expect(tip.locator(".doc-heading", has_text="Examples")).to_be_visible()
        await expect(tip).to_contain_text("Conform DataFrame to new index")
        assert "self" not in (await tip.locator("div").first.inner_text()).split(")")[0]
        # Positional parameter, then a keyword argument being typed
        await expect(tip.get_by_test_id("doc-active-param")).to_contain_text("labels")
        await page.keyboard.type("fill_value=", delay=40)
        await expect(tip.get_by_test_id("doc-active-param")).to_contain_text("fill_value")
        await expect(tip.get_by_test_id("doc-active-param")).to_contain_text("= nan")
        # Long documentation scrolls inside the tooltip
        scrolls = await tip.evaluate("t => t.scrollHeight > t.clientHeight && getComputedStyle(t).overflowY === 'auto'")
        assert scrolls
        await page.keyboard.press("Escape")

        # Details panel for the selected suggestion
        await editor.fill("")
        await type_in(page, editor, "pd.read_cs")
        details = page.get_by_test_id("completion-details")
        await expect(details).to_contain_text("read_csv(", timeout=8000)
        await expect(details.locator(".doc-heading", has_text="Parameters")).to_be_visible()
        await page.keyboard.press("Escape")

        # A function without a docstring says so (nothing invented)
        await editor.fill("")
        await type_in(page, editor, "mine(")
        await expect(tip).to_be_visible(timeout=8000)
        await expect(tip).to_contain_text("mine(x, y=2)")
        await page.keyboard.press("Escape")
        await cell.get_by_title("Delete Cell").click()
        await setup.get_by_title("Delete Cell").click()
        assert not errors, errors
        await browser.close()


# --- 4. Pivot table presentation ----------------------------------------------------------------------

PIVOT = """
import pandas as pd, numpy as np
df = pd.DataFrame({'OrderDate': pd.date_range('2020-01-01', periods=1900, freq='D'), 'Amount': np.arange(1900)})
df['OrderYear'] = df['OrderDate'].dt.year
df['OrderMonth'] = pd.Categorical(df['OrderDate'].dt.strftime('%b'), categories=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'], ordered=True)
pd.pivot_table(df, values='Amount', index='OrderYear', columns='OrderMonth', aggfunc='sum', fill_value=0, observed=False)
"""


@pytest.mark.parametrize("theme,width", [("light", 1440), ("dark", 1440), ("light", 390)])
async def test_pivot_table_index_is_distinct_like_colab(theme, width):
    async with async_playwright() as p:
        browser, page, errors = await open_studio(p, width=width, theme=theme)
        cell, _ = await add_cell(page, PIVOT)
        await run(cell)
        table = cell.get_by_test_id("interactive-data-table")
        await expect(table).to_be_visible()
        headers = [h.strip() for h in await cell.get_by_test_id("dataframe-column-header").all_inner_texts()]
        assert headers[0] == "OrderMonth" and headers[1:4] == ["Jan", "Feb", "Mar"], headers
        await expect(cell.get_by_test_id("dataframe-index-names")).to_contain_text("OrderYear")
        index_cells = cell.get_by_test_id("dataframe-index-cell")
        await expect(index_cells).to_have_count(6)
        assert await index_cells.first.get_attribute("scope") == "row"
        # Distinct from data cells
        idx_bg = await index_cells.first.evaluate("e => getComputedStyle(e).backgroundColor")
        data_bg = await cell.locator("tbody td").first.evaluate("e => getComputedStyle(e).backgroundColor")
        assert idx_bg != data_bg
        assert await index_cells.first.evaluate("e => getComputedStyle(e).fontWeight") in ("700", "bold")
        # Sideways scrolling keeps the index visible
        scroller = table.locator("table").locator("xpath=..")
        await scroller.evaluate("s => { s.scrollLeft = 400; }")
        await page.wait_for_timeout(100)
        sbox, ibox = await scroller.bounding_box(), await index_cells.first.bounding_box()
        assert abs(ibox["x"] - sbox["x"]) < 2, "index column stays pinned at the left edge"
        # Sorting by the index, filtering and the true shape still work
        await expect(table).to_contain_text("6 rows × 12 columns")
        await cell.get_by_test_id("dataframe-column-header").first.click()
        await cell.get_by_test_id("dataframe-column-header").first.click()
        assert (await index_cells.first.inner_text()).strip() == "2025"
        await table.get_by_placeholder("Filter table...").fill("2021")
        await expect(index_cells).to_have_count(1)
        assert await page.evaluate("document.documentElement.scrollWidth - innerWidth") == 0
        await cell.get_by_title("Delete Cell").click()
        assert not errors, errors
        await browser.close()
