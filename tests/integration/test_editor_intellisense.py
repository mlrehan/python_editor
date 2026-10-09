import pytest
from httpx import AsyncClient, ASGITransport
from services.api.main import app

@pytest.mark.asyncio
async def test_numpy_autocomplete():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
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
    async with AsyncClient(transport=transport, base_url="http://test") as client:
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
    async with AsyncClient(transport=transport, base_url="http://test") as client:
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
    async with AsyncClient(transport=transport, base_url="http://test") as client:
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
    async with AsyncClient(transport=transport, base_url="http://test") as client:
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
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # The user's exact code that was previously showing red squiggly underlines:
        code = "import numpy as np\nimport pandas as pd\n\ndf = pd.read_csv('sample_data.csv')\nprint(df.head())\n"
        response = await client.post("/api/v1/editor/diagnostics", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert len(data["diagnostics"]) == 0

@pytest.mark.asyncio
async def test_diagnostics_suppress_incomplete_expression():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Incomplete typing: np.
        code = "import numpy as np\nnp."
        response = await client.post("/api/v1/editor/diagnostics", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert len(data["diagnostics"]) == 0

@pytest.mark.asyncio
async def test_diagnostics_real_syntax_error():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        code = "def invalid_func(: pass"
        response = await client.post("/api/v1/editor/diagnostics", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert len(data["diagnostics"]) > 0
        assert data["diagnostics"][0]["severity"] == "error"
        assert "Syntax Error" in data["diagnostics"][0]["message"]

@pytest.mark.asyncio
async def test_diagnostics_missing_module_error():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        code = "import totally_fake_module_that_does_not_exist_404"
        response = await client.post("/api/v1/editor/diagnostics", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert len(data["diagnostics"]) > 0
        assert "Unresolved import" in data["diagnostics"][0]["message"]

