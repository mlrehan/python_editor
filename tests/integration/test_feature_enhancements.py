import pytest
import asyncio
import time
import tempfile
import shutil
from httpx import AsyncClient, ASGITransport

from services.api.main import app
from services.api.database import AsyncSessionLocal, init_db
from services.api.models import User
from services.runtime_management.kernel_session import KernelSession
from services.runtime_management.kernel_pool import KernelPoolManager

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="function")
async def client():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


# ========================================================
# 1. VERIFY PREINSTALLED DATA ANALYSIS LIBRARIES
# ========================================================
async def test_01_preinstalled_libraries_import():
    """Verify that all core enterprise data libraries can be imported in IPyKernel."""
    temp_dir = tempfile.mkdtemp(prefix="test_lib_")
    session = KernelSession(
        session_id="test-lib-session",
        user_id="test-lib-user",
        workspace_dir=temp_dir,
    )
    await session.start(timeout=25.0)
    try:
        code = """
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import scipy
import sklearn
import statsmodels
import openpyxl
import xlsxwriter
import pyarrow
import requests
import plotly
import ipympl

print("ALL_LIBRARIES_LOADED_OK")
"""
        res = await session.execute(code, timeout=30.0)
        assert res.status == "ok", f"Execution failed: {res.error}"
        stream_text = "".join(o.get("text", "") for o in res.outputs if o.get("output_type") == "stream")
        assert "ALL_LIBRARIES_LOADED_OK" in stream_text
    finally:
        await session.shutdown()
        shutil.rmtree(temp_dir, ignore_errors=True)


# ========================================================
# 2. VERIFY MATPLOTLIB MULTI-FIGURE VISUALIZATION
# ========================================================
async def test_02_matplotlib_multi_figure_inline():
    """Verify matplotlib produces inline base64 image outputs and supports multiple figures per cell."""
    temp_dir = tempfile.mkdtemp(prefix="test_plot_")
    session = KernelSession(
        session_id="test-plot-session",
        user_id="test-plot-user",
        workspace_dir=temp_dir,
    )
    await session.start(timeout=25.0)
    try:
        code = """
import matplotlib.pyplot as plt

# Figure 1: Line plot
fig1 = plt.figure()
plt.plot([1, 2, 3], [4, 5, 6])
plt.title("Figure 1")
plt.show()

# Figure 2: Bar plot
fig2 = plt.figure()
plt.bar(['A', 'B', 'C'], [10, 20, 30])
plt.title("Figure 2")
plt.show()
"""
        res = await session.execute(code, timeout=30.0)
        assert res.status == "ok"
        image_outputs = [
            o for o in res.outputs
            if (o.get("output_type") in ("display_data", "execute_result")) and "image/png" in o.get("data", {})
        ]
        # Must have at least 2 inline figures rendered
        assert len(image_outputs) >= 2, f"Expected 2 image outputs, got {len(image_outputs)}"
        for img in image_outputs:
            assert len(img["data"]["image/png"]) > 100
    finally:
        await session.shutdown()
        shutil.rmtree(temp_dir, ignore_errors=True)


# ========================================================
# 3. VERIFY CONCURRENT MULTI-USER EXECUTION
# ========================================================
async def test_03_concurrent_multi_user_execution():
    """
    Verify that multiple users can execute code simultaneously without
    global serial blocking locks.
    User 1 runs a 2-second sleep.
    User 2 runs an instant calculation and finishes before User 1.
    """
    temp_dir_1 = tempfile.mkdtemp(prefix="test_concurrent_u1_")
    temp_dir_2 = tempfile.mkdtemp(prefix="test_concurrent_u2_")

    s1 = KernelSession("session-u1", "user-1", temp_dir_1)
    s2 = KernelSession("session-u2", "user-2", temp_dir_2)

    await s1.start(timeout=25.0)
    await s2.start(timeout=25.0)

    try:
        completion_order = []

        async def run_slow():
            code = "import time\ntime.sleep(1.8)\nprint('USER_1_COMPLETE')"
            res = await s1.execute(code, timeout=10.0)
            completion_order.append(("u1", time.time()))
            return res

        async def run_fast():
            # Small delay to ensure slow has already started executing
            await asyncio.sleep(0.3)
            code = "print('USER_2_COMPLETE:', 123 * 456)"
            res = await s2.execute(code, timeout=10.0)
            completion_order.append(("u2", time.time()))
            return res

        start_time = time.time()
        res1, res2 = await asyncio.gather(run_slow(), run_fast())
        total_time = time.time() - start_time

        assert res1.status == "ok"
        assert res2.status == "ok"
        assert len(completion_order) == 2

        # u2 must complete BEFORE u1!
        first_to_finish = completion_order[0][0]
        assert first_to_finish == "u2", f"User 2 did not finish first! Order: {completion_order}"

        # Total time should be roughly ~1.8-2.5s, NOT serial sum (~2.2s + overhead)
        assert total_time < 3.5, f"Execution took too long: {total_time}s"
    finally:
        await s1.shutdown()
        await s2.shutdown()
        shutil.rmtree(temp_dir_1, ignore_errors=True)
        shutil.rmtree(temp_dir_2, ignore_errors=True)


# ========================================================
# 4. VERIFY SUPER ADMIN BOOTSTRAP, AUTH & ENDPOINTS
# ========================================================
async def test_04_super_admin_bootstrap_and_apis(client: AsyncClient):
    """Verify Super Admin authentication and management endpoints."""
    # 1. Login with bootstrap super admin credentials
    login_res = await client.post("/api/v1/auth/login", json={
        "email": "admin@example.com",
        "password": "AdminSecurePassword2026!"
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get admin statistics
    stats_res = await client.get("/api/v1/admin/stats", headers=headers)
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert "users" in stats_data
    assert "total" in stats_data["users"]
    assert "content" in stats_data
    assert "system" in stats_data

    # 3. List installed Python packages
    pkg_res = await client.get("/api/v1/admin/packages", headers=headers)
    assert pkg_res.status_code == 200
    pkg_data = pkg_res.json()
    assert isinstance(pkg_data, list)
    pkg_names = [p["name"].lower() for p in pkg_data]
    assert "numpy" in pkg_names
    assert "pandas" in pkg_names

    # 4. View kernel runtimes
    rt_res = await client.get("/api/v1/admin/runtimes", headers=headers)
    assert rt_res.status_code == 200
    rt_data = rt_res.json()
    assert isinstance(rt_data, list)

    # 5. Clear runtimes (free memory)
    clear_res = await client.post("/api/v1/admin/runtimes/clear", json={"clear_all": True}, headers=headers)
    assert clear_res.status_code == 200

    # 6. View workspaces
    ws_res = await client.get("/api/v1/admin/workspaces", headers=headers)
    assert ws_res.status_code == 200
    ws_data = ws_res.json()
    assert isinstance(ws_data, list)
    assert len(ws_data) > 0
    owners = [w.get("id") or w.get("owner") for w in ws_data]
    assert "public" in owners or any("Public" in str(o) for o in owners)


# ========================================================
# 5. VERIFY THEME PREFERENCE PERSISTENCE
# ========================================================
async def test_05_theme_preference_persistence(client: AsyncClient):
    """Verify theme preference endpoint updates user profile in database."""
    login_res = await client.post("/api/v1/auth/login", json={
        "email": "admin@example.com",
        "password": "AdminSecurePassword2026!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Update theme to light
    t_res = await client.put("/api/v1/auth/theme", json={"theme_preference": "light"}, headers=headers)
    assert t_res.status_code == 200
    assert t_res.json()["theme_preference"] == "light"

    # Verify via /auth/me
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["theme_preference"] == "light"

    # Reset back to dark
    await client.put("/api/v1/auth/theme", json={"theme_preference": "dark"}, headers=headers)
