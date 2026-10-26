"""Phase 0 stability: kernel quotas, eviction, reaping, memory watchdog, crash detection, ownership."""
import os
import shutil
import sys
import tempfile
import time
import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from services.api.config import Settings, assert_production_secrets
from services.api.main import app
from services.runtime_management.kernel_pool import KernelPoolManager, KernelCapacityError

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def pool():
    root = tempfile.mkdtemp(prefix="test_pool_")
    manager = KernelPoolManager(
        workspaces_root=root,
        max_kernels_per_user=2,
        max_total_kernels=2,
        max_guest_kernels=1,
        idle_timeout_seconds=3600,
        detached_timeout_seconds=600,
        max_kernel_memory_mb=0,
    )
    yield manager
    await manager.shutdown_all()
    shutil.rmtree(root, ignore_errors=True)


async def test_server_cap_evicts_abandoned_kernel_first(pool):
    a = await pool.get_or_create_session("nb", "user_a")
    b = await pool.get_or_create_session("nb", "user_b")
    a.attach_client()
    b.attach_client()

    # Both kernels have a browser attached: no room for a third user
    with pytest.raises(KernelCapacityError):
        await pool.get_or_create_session("nb", "user_c")

    # user_a closes the tab: their kernel is now evictable
    a.detach_client()
    c = await pool.get_or_create_session("nb", "user_c")
    assert c.is_running
    assert a not in pool.sessions.values()
    assert b in pool.sessions.values()


async def test_guest_cap_is_separate_from_users(pool):
    g1 = await pool.get_or_create_session("nb", "guest_one")
    g1.attach_client()
    with pytest.raises(KernelCapacityError, match="guest"):
        await pool.get_or_create_session("nb", "guest_two")
    # A signed-in user is not blocked by the guest cap
    user = await pool.get_or_create_session("nb", "user_a")
    assert user.is_running


async def test_reaper_removes_abandoned_and_idle_but_not_busy(pool):
    pool.max_total_kernels = 5
    pool.max_kernels_per_user = 5
    attached = await pool.get_or_create_session("s1", "user_a")
    attached.attach_client()
    abandoned = await pool.get_or_create_session("s2", "user_a")
    abandoned.attach_client()
    abandoned.detach_client()

    now = time.time()
    # 11 minutes later: only the session without a browser is reaped
    reaped = await pool.reap_idle_sessions(now=now + 660)
    assert reaped == ["s2"]
    assert attached in pool.sessions.values()

    # A busy (executing) kernel is never reaped, even past the idle timeout
    await attached._lock.acquire()
    try:
        assert await pool.reap_idle_sessions(now=now + 7200) == []
    finally:
        attached._lock.release()
    assert await pool.reap_idle_sessions(now=now + 7200) == ["s1"]


async def test_get_session_never_returns_another_users_kernel(pool):
    pool.max_total_kernels = 5
    admin = await pool.get_or_create_session("shared-id", "admin_super", is_admin=True)
    mine = await pool.get_or_create_session("shared-id", "user_a")

    assert pool.get_session("shared-id", "user_a") is mine
    assert pool.get_session("shared-id", "user_b") is None
    assert pool.get_session("shared-id", "admin_super") is admin
    # Shutting down by id only affects the caller's own kernel
    assert await pool.shutdown_session("shared-id", "user_b") is False
    assert admin.is_running and mine.is_running


async def test_crashed_kernel_is_reported_quickly_and_restarts(pool):
    session = await pool.get_or_create_session("nb", "user_a")
    started = time.time()
    result = await session.execute("import os\nos._exit(1)", timeout=60)
    assert time.time() - started < 15
    assert result.status == "error"
    assert result.error["ename"] == "KernelDied"

    assert await session.ensure_running() is True
    follow_up = await session.execute("print('back')")
    assert "back" in "".join(o.get("text", "") for o in follow_up.outputs)


async def test_memory_watchdog_kills_kernel_over_limit(pool):
    session = await pool.get_or_create_session("nb", "user_a")
    pool.max_kernel_memory_mb = 1  # every real kernel is above 1 MB
    killed = await pool.enforce_memory_limits()
    assert killed == ["nb"]
    assert not session.is_running

    result = await session.execute("1", timeout=10) if session.kc and session.is_running else None
    assert result is None  # nothing can run until the kernel is restarted
    assert await session.ensure_running() is True
    assert session.death_reason is None


async def test_completion_does_not_import_user_modules_into_api_process():
    marker_dir = tempfile.mkdtemp(prefix="test_import_guard_")
    module_name = f"pcs_guard_probe_{uuid.uuid4().hex[:8]}"
    marker = os.path.join(marker_dir, "imported.txt")
    with open(os.path.join(marker_dir, f"{module_name}.py"), "w", encoding="utf-8") as f:
        f.write(f"open({marker!r}, 'w').write('imported')\n")
    sys.path.insert(0, marker_dir)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/editor/complete", json={
                "code": f"import {module_name} as p\np.", "line": 2, "column": 2, "notebook_context": [],
            })
        assert response.status_code == 200
        assert not os.path.exists(marker), "completion imported a user-controlled module into the API process"
        assert module_name not in sys.modules
    finally:
        sys.path.remove(marker_dir)
        shutil.rmtree(marker_dir, ignore_errors=True)


async def test_completion_does_not_reveal_other_users_files():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async def register():
            email = f"cap_{uuid.uuid4().hex[:8]}@example.com"
            r = await client.post("/api/v1/auth/register", json={"email": email, "password": "probe-pass-123", "full_name": "Probe"})
            return {"Authorization": f"Bearer {r.json()['access_token']}"}

        alice, bob = await register(), await register()
        secret_module = f"alice_private_{uuid.uuid4().hex[:6]}"
        await client.post("/api/v1/files/write", headers=alice, json={"path": f"{secret_module}.py", "content": "TOKEN = 1\n"})

        response = await client.post("/api/v1/editor/complete", headers=bob, json={
            "code": "import alice_private_", "line": 1, "column": len("import alice_private_"), "notebook_context": [],
        })
        labels = [c["label"] for c in response.json()["completions"]]
        assert secret_module not in labels

        # Alice still gets her own module
        response = await client.post("/api/v1/editor/complete", headers=alice, json={
            "code": "import alice_private_", "line": 1, "column": len("import alice_private_"), "notebook_context": [],
        })
        assert secret_module in [c["label"] for c in response.json()["completions"]]


async def test_production_refuses_default_secrets():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        assert_production_secrets(Settings(APP_ENV="production"))
    assert_production_secrets(Settings(APP_ENV="production", SECRET_KEY="x" * 64, ADMIN_BOOTSTRAP_PASSWORD="a-real-password"))
    assert_production_secrets(Settings(APP_ENV="development"))
