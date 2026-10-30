"""
Kernel-level tests for Jupyter output semantics (what is stored with the notebook and streamed):
clear_output, clear_output(wait=True), display handles (update_display_data), DataFrame MIME bundles.
"""
import shutil
import tempfile

import pytest

from services.runtime_management.kernel_session import KernelSession, apply_output

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="function")
async def kernel():
    temp_dir = tempfile.mkdtemp(prefix="test_kernel_rich_")
    session = KernelSession(session_id="test-rich", user_id="test-user", workspace_dir=temp_dir)
    await session.start(timeout=30.0)
    yield session
    await session.shutdown()
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_apply_output_rules():
    outputs = []
    apply_output(outputs, {"output_type": "stream", "name": "stdout", "text": "a"})
    apply_output(outputs, {"output_type": "clear_output", "wait": False})
    assert outputs == []

    apply_output(outputs, {"output_type": "stream", "name": "stdout", "text": "b"})
    apply_output(outputs, {"output_type": "clear_output", "wait": True})
    assert outputs[0]["text"] == "b"  # still shown until the next output arrives
    apply_output(outputs, {"output_type": "clear_output", "wait": True})
    apply_output(outputs, {"output_type": "stream", "name": "stdout", "text": "c"})
    assert [o["text"] for o in outputs] == ["c"]

    apply_output(outputs, {"output_type": "display_data", "display_id": "d1", "data": {"text/plain": "'old'"}, "metadata": {}})
    apply_output(outputs, {"output_type": "update_display_data", "display_id": "d1", "data": {"text/plain": "'new'"}, "metadata": {}})
    assert outputs[-1]["data"]["text/plain"] == "'new'"
    assert len(outputs) == 2


async def test_clear_output_wait_keeps_only_last(kernel):
    result = await kernel.execute(
        "from IPython.display import clear_output\n"
        "for i in range(4):\n"
        "    clear_output(wait=True)\n"
        "    print('step', i)\n"
    )
    assert result.status == "ok"
    assert [o.get("text", "").strip() for o in result.outputs] == ["step 3"]


async def test_display_handle_update_replaces_output(kernel):
    result = await kernel.execute("h = display('first', display_id=True)\nprint('mid')\nh.update('second')")
    assert result.status == "ok"
    displays = [o for o in result.outputs if o["output_type"] == "display_data"]
    assert len(displays) == 1
    assert displays[0]["data"]["text/plain"] == "'second'"
    assert displays[0]["display_id"]


async def test_dataframe_html_bundle_has_named_index_row(kernel):
    pytest.importorskip("pandas")
    result = await kernel.execute(
        "import pandas as pd\n"
        "df = pd.DataFrame({'Jan': [1], 'Feb': [2]}, index=pd.Index([2024], name='Year'))\n"
        "display(df)"
    )
    html = next(o for o in result.outputs if o["output_type"] == "display_data")["data"]["text/html"]
    # The layout the browser parser handles: column names first, the index-name row last
    assert "<th>Jan</th>" in html and "<th>Year</th>" in html
    assert html.index("<th>Jan</th>") < html.index("<th>Year</th>")
    assert 'class="dataframe"' in html
