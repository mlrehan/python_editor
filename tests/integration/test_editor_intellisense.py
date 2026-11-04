import pytest
from httpx import AsyncClient, ASGITransport
from services.api.main import app
from services.api.guest_workspace import issue_guest_token

# A server-issued guest session (requests without one are refused)
GUEST = {"X-Guest-Token": issue_guest_token()}

@pytest.mark.asyncio
async def test_numpy_autocomplete():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=GUEST) as client:
        # np.
        response = await client.post("/api/v1/editor/complete", json={
            "code": "import numpy as np\nnp.",
            "line": 2,
            "column": 3
        })
        assert response.status_code == 200
        data = response.json()
        assert "completions" in data
        labels = [c["label"] for c in data["completions"]]
        assert len(labels) > 50
        assert "array" in labels
        assert "arange" in labels
        assert "mean" in labels

@pytest.mark.asyncio
async def test_pandas_autocomplete():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=GUEST) as client:
        # pd.
        response = await client.post("/api/v1/editor/complete", json={
            "code": "import pandas as pd\npd.",
            "line": 2,
            "column": 3
        })
        assert response.status_code == 200
        data = response.json()
        labels = [c["label"] for c in data["completions"]]
        assert "DataFrame" in labels
        assert "Series" in labels
        assert "read_csv" in labels

@pytest.mark.asyncio
async def test_cross_cell_context_dataframe_autocomplete():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=GUEST) as client:
        # Cell 2 accessing df defined in Cell 1
        response = await client.post("/api/v1/editor/complete", json={
            "code": "df.",
            "line": 1,
            "column": 3,
            "notebook_context": ["import pandas as pd\ndf = pd.DataFrame({'a': [1, 2]})"]
        })
        assert response.status_code == 200
        data = response.json()
        labels = [c["label"] for c in data["completions"]]
        assert "head" in labels
        assert "tail" in labels
        assert "describe" in labels

@pytest.mark.asyncio
async def test_prefix_filtering():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=GUEST) as client:
        # np.ar
        response = await client.post("/api/v1/editor/complete", json={
            "code": "import numpy as np\nnp.ar",
            "line": 2,
            "column": 5
        })
        assert response.status_code == 200
        data = response.json()
        labels = [c["label"] for c in data["completions"]]
        assert "arange" in labels
        assert "array" in labels
        # Non-ar completions should be filtered out
        for label in labels:
            assert label.lower().startswith("ar")

@pytest.mark.asyncio
async def test_signature_help():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=GUEST) as client:
        # np.linspace(
        response = await client.post("/api/v1/editor/signatures", json={
            "code": "import numpy as np\nnp.linspace(",
            "line": 2,
            "column": 12
        })
        assert response.status_code == 200
        data = response.json()
        signatures = data.get("signatures", [])
        assert len(signatures) > 0
        assert "start" in signatures[0]["signature"]
        assert "stop" in signatures[0]["signature"]

@pytest.mark.asyncio
async def test_diagnostics_clean_on_valid_code():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=GUEST) as client:
        # The user's exact code that was previously showing red squiggly underlines:
        code = "import numpy as np\nimport pandas as pd\n\ndf = pd.read_csv('sample_data.csv')\nprint(df.head())\n"
        response = await client.post("/api/v1/editor/diagnostics", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert len(data["diagnostics"]) == 0

@pytest.mark.asyncio
async def test_diagnostics_suppress_incomplete_expression():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=GUEST) as client:
        # Incomplete typing: np.
        code = "import numpy as np\nnp."
        response = await client.post("/api/v1/editor/diagnostics", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert len(data["diagnostics"]) == 0

@pytest.mark.asyncio
async def test_diagnostics_real_syntax_error():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=GUEST) as client:
        code = "def invalid_func(: pass"
        response = await client.post("/api/v1/editor/diagnostics", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert len(data["diagnostics"]) > 0
        assert data["diagnostics"][0]["severity"] == "error"
        assert data["diagnostics"][0]["message"].startswith("SyntaxError: ")
        assert data["diagnostics"][0]["error_type"] == "SyntaxError"

@pytest.mark.asyncio
async def test_diagnostics_missing_module_error():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=GUEST) as client:
        code = "import totally_fake_module_that_does_not_exist_404"
        response = await client.post("/api/v1/editor/diagnostics", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert len(data["diagnostics"]) > 0
        assert data["diagnostics"][0]["message"].startswith("ModuleNotFoundError: No module named")
        assert data["diagnostics"][0]["error_type"] == "ModuleNotFoundError"

@pytest.mark.asyncio
@pytest.mark.parametrize("code", [
    "!python main.py",
    "%run main.py",
    "!pip list",
    "files = !ls",
    "%timeit sum(range(10))",
    "import os\nfor i in range(2):\n    !echo {i}\nprint(os.getcwd())",
    "len?",
    "?len",
    "%%bash\necho this is not python (",
])
async def test_diagnostics_ignore_ipython_magics_and_shell_escapes(code):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=GUEST) as client:
        response = await client.post("/api/v1/editor/diagnostics", json={"code": code})
        assert response.status_code == 200
        assert response.json()["diagnostics"] == []

@pytest.mark.asyncio
async def test_diagnostics_real_error_next_to_magic_keeps_line_number():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=GUEST) as client:
        code = "!python main.py\nx = (1, \nprint('after')"
        response = await client.post("/api/v1/editor/diagnostics", json={"code": code})
        diagnostics = response.json()["diagnostics"]
        assert len(diagnostics) == 1
        assert diagnostics[0]["message"].startswith("SyntaxError: ")
        assert diagnostics[0]["from_line"] >= 2



@pytest.mark.asyncio
@pytest.mark.parametrize("code,error_type,message,line", [
    ("if True:\nprint(1)", "IndentationError", "expected an indented block after 'if' statement on line 1", 2),
    ("x = 1\n    y = 2", "IndentationError", "unexpected indent", 2),
    ("def f(:\n    pass", "SyntaxError", "invalid syntax", 1),
    ("print('a'", "SyntaxError", "'(' was never closed", 1),
    ("x = 1\nreturn x", "SyntaxError", "'return' outside function", 2),
    ("for i in range(3):\n    pass\nbreak", "SyntaxError", "'break' outside loop", 3),
])
async def test_diagnostics_report_pythons_exact_error(code, error_type, message, line):
    """The exception class, Python's own message and the line, as Python itself reports them."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=GUEST) as client:
        res = await client.post("/api/v1/editor/diagnostics", json={"code": code})
    d = res.json()["diagnostics"]
    assert len(d) == 1, d
    assert d[0]["error_type"] == error_type
    assert d[0]["message"] == f"{error_type}: {message}"
    assert d[0]["from_line"] == line


@pytest.mark.asyncio
async def test_diagnostics_allow_top_level_await():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=GUEST) as client:
        res = await client.post("/api/v1/editor/diagnostics", json={"code": "import asyncio\nawait asyncio.sleep(0)"})
    assert res.json()["diagnostics"] == []
