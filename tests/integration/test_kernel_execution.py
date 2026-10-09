import pytest
import asyncio
import os
import shutil
import tempfile
from services.runtime_management.kernel_session import KernelSession

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="function")
async def temp_kernel():
    temp_dir = tempfile.mkdtemp(prefix="test_kernel_ws_")
    session = KernelSession(
        session_id="test-session-123",
        user_id="test-user-001",
        workspace_dir=temp_dir,
    )
    await session.start(timeout=20.0)
    yield session, temp_dir
    await session.shutdown()
    shutil.rmtree(temp_dir, ignore_errors=True)


async def test_01_execute_hello_world(temp_kernel):
    """TEST 01: Execute Hello World."""
    session, _ = temp_kernel
    result = await session.execute('print("Hello World")')
    assert result.status == "ok"
    assert len(result.outputs) > 0
    stream_text = "".join(o["text"] for o in result.outputs if o["output_type"] == "stream")
    assert "Hello World" in stream_text


async def test_02_perform_arithmetic(temp_kernel):
    """TEST 02: Perform arithmetic calculation."""
    session, _ = temp_kernel
    result = await session.execute("result = 250 * 4\nprint(result)")
    assert result.status == "ok"
    stream_text = "".join(o["text"] for o in result.outputs if o["output_type"] == "stream")
    assert "1000" in stream_text


async def test_03_persist_variables_across_cells(temp_kernel):
    """TEST 03: Persist variables across notebook cells."""
    session, _ = temp_kernel
    # Cell 1: define variable
    res1 = await session.execute("x = 100")
    assert res1.status == "ok"

    # Cell 2: use variable from previous cell
    res2 = await session.execute("print(x * 5)")
    assert res2.status == "ok"
    stream_text = "".join(o["text"] for o in res2.outputs if o["output_type"] == "stream")
    assert "500" in stream_text


async def test_04_execute_functions(temp_kernel):
    """TEST 04: Execute Python functions."""
    session, _ = temp_kernel
    code = """
def calculate_total(price, quantity):
    total = price * quantity
    return total

res = calculate_total(15, 6)
print(f"Total: {res}")
"""
    result = await session.execute(code)
    assert result.status == "ok"
    stream_text = "".join(o["text"] for o in result.outputs if o["output_type"] == "stream")
    assert "Total: 90" in stream_text


async def test_05_execute_python_classes(temp_kernel):
    """TEST 05: Execute Python classes and object-oriented code."""
    session, _ = temp_kernel
    code = """
class StudentAccount:
    def __init__(self, username: str, credits: int):
        self.username = username
        self.credits = credits

    def consume(self, amount: int) -> int:
        self.credits -= amount
        return self.credits

acc = StudentAccount("alice", 50)
print(f"Remaining: {acc.consume(15)}")
"""
    result = await session.execute(code)
    assert result.status == "ok"
    stream_text = "".join(o["text"] for o in result.outputs if o["output_type"] == "stream")
    assert "Remaining: 35" in stream_text


async def test_06_import_numpy(temp_kernel):
    """TEST 06: Import NumPy and perform array operations."""
    session, _ = temp_kernel
    code = """
import numpy as np
arr = np.array([1, 2, 3, 4, 5])
print("Mean:", float(arr.mean()))
"""
    result = await session.execute(code)
    assert result.status == "ok"
    stream_text = "".join(o["text"] for o in result.outputs if o["output_type"] == "stream")
    assert "Mean: 3.0" in stream_text


async def test_07_create_pandas_dataframe(temp_kernel):
    """TEST 07: Create a Pandas DataFrame and compute aggregations."""
    session, _ = temp_kernel
    code = """
import pandas as pd
df = pd.DataFrame({
    'name': ['Python', 'SQL', 'FastAPI'],
    'stars': [100, 85, 95]
})
print("Sum:", int(df['stars'].sum()))
"""
    result = await session.execute(code)
    assert result.status == "ok"
    stream_text = "".join(o["text"] for o in result.outputs if o["output_type"] == "stream")
    assert "Sum: 280" in stream_text


async def test_08_read_csv_with_pandas(temp_kernel):
    """TEST 08: Write a CSV in the workspace and read it back with Pandas."""
    session, ws_dir = temp_kernel
    # Write a test CSV inside the workspace
    csv_path = os.path.join(ws_dir, "dataset.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("item,price\napple,2.5\norange,3.0\n")

    code = """
import pandas as pd
df = pd.read_csv("dataset.csv")
print("Total rows:", len(df))
"""
    result = await session.execute(code)
    assert result.status == "ok"
    stream_text = "".join(o["text"] for o in result.outputs if o["output_type"] == "stream")
    assert "Total rows: 2" in stream_text


async def test_09_generate_matplotlib_chart(temp_kernel):
    """TEST 09: Generate a Matplotlib chart and verify display_data MIME bundle."""
    session, _ = temp_kernel
    code = """
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [4, 5, 6])
plt.show()
"""
    result = await session.execute(code)
    assert result.status == "ok"
    # Verify display_data output contains image/png MIME bundle
    image_outputs = [
        o for o in result.outputs
        if o["output_type"] in ("display_data", "execute_result") and "image/png" in o.get("data", {})
    ]
    assert len(image_outputs) > 0
    png_base64 = image_outputs[0]["data"]["image/png"]
    assert len(png_base64) > 100


async def test_11_handle_python_exception(temp_kernel):
    """TEST 11: Handle Python exception and verify traceback generation."""
    session, _ = temp_kernel
    result = await session.execute("1 / 0")
    assert result.status == "error"
    assert result.error is not None
    assert result.error["ename"] == "ZeroDivisionError"
    assert any("ZeroDivisionError" in line for line in result.error["traceback"])


async def test_13_and_14_restart_kernel_and_variable_reset(temp_kernel):
    """TEST 13 & 14: Restart kernel and verify variable state is cleared."""
    session, _ = temp_kernel
    # 1. Set variable
    await session.execute("persisted_var = 9999")
    check1 = await session.execute("print(persisted_var)")
    assert "9999" in "".join(o["text"] for o in check1.outputs if o["output_type"] == "stream")

    # 2. Restart kernel
    await session.restart()

    # 3. Accessing variable should now raise NameError
    check2 = await session.execute("print(persisted_var)")
    assert check2.status == "error"
    assert check2.error["ename"] == "NameError"


async def test_15_stdout_and_stderr_behavior(temp_kernel):
    """TEST 15: Verify separate stdout and stderr capture."""
    session, _ = temp_kernel
    code = """
import sys
sys.stdout.write("standard output message\\n")
sys.stderr.write("standard error warning\\n")
"""
    result = await session.execute(code)
    assert result.status == "ok"
    stdout_chunks = [o["text"] for o in result.outputs if o.get("name") == "stdout"]
    stderr_chunks = [o["text"] for o in result.outputs if o.get("name") == "stderr"]

    assert any("standard output message" in c for c in stdout_chunks)
    assert any("standard error warning" in c for c in stderr_chunks)

