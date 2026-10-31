"""
Language-service tests without a browser:
  - column-key positions (df[ / df[' / df.loc[:, / df.groupby(' ...) are detected, other code is not
  - documentation comes from real introspection (signature defaults/types + parsed docstrings)
  - kernel introspection reads DataFrame columns and the namespace without running user code:
    no history entry, unchanged execution count, no names added, skipped while code runs
"""
import ast
import asyncio
import json
import shutil
import tempfile

import pytest

from services.api.python_docs import build_doc, parse_docstring
from services.api.routers.editor import _column_context, _column_items
from services.runtime_management.introspection import request_expression
from services.runtime_management.kernel_session import KernelSession

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("line,expected", [
    ("df[", {"expr": "df", "quote": "", "prefix": ""}),
    ("df['", {"expr": "df", "quote": "'", "prefix": ""}),
    ('sales_df["Ord', {"expr": "sales_df", "quote": '"', "prefix": "Ord"}),
    ("df[['Amount', '", {"expr": "df", "quote": "'", "prefix": ""}),
    ("df.loc[:, ", {"expr": "df", "quote": "", "prefix": ""}),
    ("df.loc[:, ['", {"expr": "df", "quote": "'", "prefix": ""}),
    ("df.groupby('", {"expr": "df", "quote": "'", "prefix": ""}),
    ("df.sort_values(by=['", {"expr": "df", "quote": "'", "prefix": ""}),
    ("df.filter(items=['", {"expr": "df", "quote": "'", "prefix": ""}),
    ("print(df['A", {"expr": "df", "quote": "'", "prefix": "A"}),
    ("data.frames[", {"expr": "data.frames", "quote": "", "prefix": ""}),
])
def test_column_positions_detected(line, expected):
    assert _column_context(line) == expected


@pytest.mark.parametrize("line", ["df.iloc[", "df.loc['a'", "x = f'", "print('", "# df['", "df.head(", "df[col", "df[df['A'] > 1]["])
def test_non_column_positions_ignored(line):
    assert _column_context(line) is None


def test_column_items_quote_handling():
    info = {"kind": "DataFrame", "shape": [3, 3], "columns": [
        {"label": "Order Date", "key": "'Order Date'", "is_str": True, "dtype": "datetime64[ns]"},
        {"label": "it's", "key": '"it\'s"', "is_str": True, "dtype": "object"},
        {"label": "2024", "key": "2024", "is_str": False, "dtype": "int64"},
    ]}
    unquoted = _column_items("df", info, "")
    assert [i.insert_text for i in unquoted] == ["'Order Date'", '"it\'s"', "2024"]
    quoted = _column_items("df", info, "'")
    assert [i.insert_text for i in quoted] == ["Order Date", "it\\'s"]  # escaped; int key needs no quotes
    assert all(i.type == "column" for i in quoted) and quoted[0].detail == "datetime64[ns]"


def test_docs_from_real_introspection():
    pd = pytest.importorskip("pandas")
    doc = build_doc(pd.DataFrame.reindex, "reindex")
    assert doc["signature"].startswith("reindex(labels=None")  # no implicit self
    assert doc["summary"].startswith("Conform DataFrame to new index")
    fill = next(p for p in doc["parameters"] if p["name"] == "fill_value")
    assert fill["default"] == "nan" and fill["description"]
    assert doc["returns"] and doc["returns"][0]["type"]
    assert doc["examples"] and "see_also" in doc and doc["see_also"]

    np = pytest.importorskip("numpy")
    mean = build_doc(np.mean, "mean")
    assert mean["parameters"][0]["name"] == "a" and mean["parameters"][0]["type"] == "array_like"

    def undocumented(x, y=2):
        return x

    plain = build_doc(undocumented, "undocumented")
    assert plain["has_docstring"] is False and plain["summary"] is None
    assert [p["default"] for p in plain["parameters"]] == [None, "2"]


def test_google_and_rest_docstrings():
    google = parse_docstring("Do it.\n\nArgs:\n    a (int): first.\n\nReturns:\n    str: result.")
    assert google["parameters"][0] == {"name": "a", "type": "int", "description": "first."}
    assert google["returns"][0]["type"] == "str"
    rest = parse_docstring("Do it.\n\n:param x: the x.\n:type x: float\n:returns: y\n:rtype: int")
    assert rest["parameters"][0]["type"] == "float" and rest["returns"][0]["type"] == "int"


@pytest.fixture(scope="function")
async def kernel():
    temp_dir = tempfile.mkdtemp(prefix="test_intel_")
    session = KernelSession(session_id="test-intel", user_id="test-user", workspace_dir=temp_dir)
    await session.start(timeout=30.0)
    yield session
    await session.shutdown()
    shutil.rmtree(temp_dir, ignore_errors=True)


async def _introspect(session, request):
    raw = await session.evaluate_silently(request_expression(request))
    return None if raw is None else json.loads(ast.literal_eval(raw))


async def test_runtime_columns_are_complete_and_read_only(kernel):
    pytest.importorskip("pandas")
    await kernel.execute(
        "import pandas as pd\n"
        "wide = pd.DataFrame([[0] * 150], columns=[f'col {i}' for i in range(149)] + [2024])\n"
        "plain = {'a': 1}"
    )
    count_before = kernel.execution_count
    info = await _introspect(kernel, {"kind": "columns", "expr": "wide"})
    assert info["kind"] == "DataFrame" and len(info["columns"]) == 150  # no cap
    assert info["columns"][0]["label"] == "col 0" and info["columns"][-1]["key"] == "2024"
    assert (await _introspect(kernel, {"kind": "columns", "expr": "plain"}))["error"] == "not_dataframe"
    assert (await _introspect(kernel, {"kind": "columns", "expr": "missing"}))["error"] == "missing"
    ns = await _introspect(kernel, {"kind": "namespace"})
    assert ns["wide"] == "pandas.DataFrame" and ns["pd"] == "module:pandas"

    assert kernel.execution_count == count_before
    check = await kernel.execute("print(len(In), [k for k in globals() if 'pcs' in k])")
    assert check.outputs[0]["text"].strip() == "3 []", check.outputs  # In[0] + 2 user cells; nothing added


async def test_runtime_columns_follow_changes(kernel):
    pytest.importorskip("pandas")
    await kernel.execute("import pandas as pd\ndf = pd.DataFrame({'a': [1]})")
    assert [c["label"] for c in (await _introspect(kernel, {"kind": "columns", "expr": "df"}))["columns"]] == ["a"]
    await kernel.execute("df['b'] = 2\ndf = df.rename(columns={'a': 'A'})")
    assert [c["label"] for c in (await _introspect(kernel, {"kind": "columns", "expr": "df"}))["columns"]] == ["A", "b"]


async def test_introspection_skipped_while_code_runs(kernel):
    running = asyncio.create_task(kernel.execute("import time\ntime.sleep(1.5)"))
    await asyncio.sleep(0.4)
    assert await kernel.evaluate_silently(request_expression({"kind": "namespace"})) is None
    await running
    assert await kernel.evaluate_silently(request_expression({"kind": "namespace"})) is not None


async def test_concurrent_introspections_all_answer(kernel):
    """Fast typing sends overlapping requests: each waits its turn instead of reporting 'busy'."""
    await kernel.execute("x = 1")
    results = await asyncio.gather(*[kernel.evaluate_silently(request_expression({"kind": "namespace"})) for _ in range(5)])
    assert all(r is not None for r in results)
    assert kernel.execution_count == 1
