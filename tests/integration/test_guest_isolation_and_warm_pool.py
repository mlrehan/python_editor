"""
Guest isolation and the warm kernel pool, without a browser:
  - guest tokens: only server-issued (signed) tokens are accepted; each maps to its own workspace
  - API: guests are refused without a valid token; two guests never see or change each other's
    files, notebooks or kernels
  - guest workspaces: starter files, restore flag, idle cleanup
  - warm pool: a pre-started kernel handed to a session runs in that session's workspace with that
    session's environment (cwd, sys.path, env, runtime guard), keeps preloaded libraries out of the
    user's namespace, and restarts in the right workspace; admin sessions never take one
"""
import asyncio
import os
import shutil
import sys
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

from services.api.guest_workspace import GuestWorkspaces, guest_workspace_id, issue_guest_token
from services.runtime_management.kernel_pool import KernelPoolManager

pytestmark = pytest.mark.asyncio



def _stdout(result) -> str:
    """All printed text of a run (the kernel may send it in several chunks)."""
    return "".join(o.get("text", "") for o in result.outputs if o.get("output_type") == "stream")


# --- tokens and workspaces -----------------------------------------------------------------------------


async def test_only_signed_guest_tokens_are_accepted():
    token = issue_guest_token()
    ws = guest_workspace_id(token)
    assert ws and len(ws) == 32 and ws not in token
    assert guest_workspace_id(issue_guest_token()) != ws
    raw, _, sig = token.rpartition(".")
    for forged in ["", "gst_guest_session", "gst_abc", raw + ".", raw + "." + "0" * 32, token[:-1] + ("a" if token[-1] != "a" else "b")]:
        assert guest_workspace_id(forged) is None, forged


async def test_guest_workspaces_are_private_and_restorable():
    root = tempfile.mkdtemp()
    template = os.path.join(root, "template")
    os.makedirs(template)
    with open(os.path.join(template, "main.py"), "w") as f:
        f.write("print('starter')")
    gw = GuestWorkspaces(root, template)
    a, b = guest_workspace_id(issue_guest_token()), guest_workspace_id(issue_guest_token())
    pa, pb = gw.path(a), gw.path(b)
    assert pa != pb and os.path.isfile(os.path.join(pa, "main.py"))
    assert gw.info(a)["restore_pending"] is True
    gw.mark_restored(a)
    assert gw.info(a)["restore_pending"] is False

    nb = gw.save_notebook(a, None, "Mine", {"cells": []})
    assert [n["id"] for n in gw.list_notebooks(a)] == [nb["id"]]
    assert gw.list_notebooks(b) == [] and gw.get_notebook(b, nb["id"]) is None
    with pytest.raises(ValueError):
        gw.path("../escape")

    # Unused for longer than the limit: removed, except workspaces with a live kernel
    os.utime(os.path.join(gw.root, f"{a}.meta.json"), (0, 0))
    os.utime(os.path.join(gw.root, f"{b}.meta.json"), (0, 0))
    assert gw.remove_idle(3600, active_ids={b}) == [a]
    assert not os.path.exists(pa) and os.path.exists(pb)
    assert gw.info(a)["restore_pending"] is True  # comes back new: the browser restores it
    shutil.rmtree(root, ignore_errors=True)


# --- API -----------------------------------------------------------------------------------------------


@pytest.fixture
async def client():
    from services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _guest(client):
    res = await client.post("/api/v1/auth/guest-session")
    return {"X-Guest-Token": res.json()["guest_token"]}


async def test_api_isolates_guests(client):
    a, b = await _guest(client), await _guest(client)
    assert (await client.post("/api/v1/files/write", json={"path": "a_only.py", "content": "A = 1"}, headers=a)).status_code == 200
    nb = (await client.post("/api/v1/notebooks", json={"title": "A notebook"}, headers=a)).json()

    files_b = (await client.get("/api/v1/files", headers=b)).json()
    assert "a_only.py" not in [f["name"] for f in files_b]
    assert (await client.get("/api/v1/files/read?path=a_only.py", headers=b)).status_code == 404
    assert all(n["id"] != nb["id"] for n in (await client.get("/api/v1/notebooks", headers=b)).json())
    assert (await client.get(f"/api/v1/notebooks/{nb['id']}", headers=b)).status_code == 404
    assert (await client.delete(f"/api/v1/notebooks/{nb['id']}", headers=b)).status_code == 404
    await client.put(f"/api/v1/notebooks/{nb['id']}", json={"title": "B's"}, headers=b)  # B's own copy
    assert (await client.get(f"/api/v1/notebooks/{nb['id']}", headers=a)).json()["title"] == "A notebook"
    assert (await client.post("/api/v1/files/write", json={"path": "../x.py", "content": ""}, headers=b)).status_code == 403

    # No token, a made-up token, the old shared token: refused
    for headers in [{}, {"X-Guest-Token": "gst_madeup"}, {"X-Guest-Token": "gst_guest_session"}]:
        res = await client.get("/api/v1/files", headers=headers)
        assert res.status_code == 401 and res.json()["detail"] == "guest_session_required"

    # Downloads take the token in the link
    token_a = a["X-Guest-Token"]
    assert (await client.get(f"/api/v1/files/download?path=a_only.py&x_guest_token={token_a}")).status_code == 200
    assert (await client.get("/api/v1/files/download?path=a_only.py")).status_code == 401
    await client.delete("/api/v1/files?path=a_only.py", headers=a)
    await client.delete(f"/api/v1/notebooks/{nb['id']}", headers=a)


async def test_guest_kernels_are_separate(client):
    a, b = await _guest(client), await _guest(client)
    res_a = await client.post("/api/v1/execution/run", json={"session_id": "same-id", "code": "secret = 42\nimport os\nprint(os.getcwd())"}, headers=a)
    res_b = await client.post("/api/v1/execution/run", json={"session_id": "same-id", "code": "print(secret)"}, headers=b)
    assert res_a.json()["status"] == "ok"
    assert res_b.json()["status"] == "error" and "NameError" in str(res_b.json()["outputs"])
    cwd_a = res_a.json()["outputs"][0]["text"].strip().replace("\\", "/")
    assert "/workspaces/guests/" in cwd_a


# --- warm pool -----------------------------------------------------------------------------------------


@pytest.fixture
async def warm_pool():
    base = tempfile.mkdtemp(prefix="pcs_warm_")
    root = os.path.join(base, "workspaces")  # the production layout the runtime guard recognises
    pool = KernelPoolManager(workspaces_root=root, warm_pool_size=1, preload_modules=["json", "decimal"], warm_refill_delay_seconds=0)
    await pool.fill_warm_pool()
    yield pool
    await pool.shutdown_all()
    shutil.rmtree(base, ignore_errors=True)


async def test_warm_kernel_adopts_owner_workspace(warm_pool):
    assert len(warm_pool._warm) == 1
    spare_pid = warm_pool._warm[0]._kernel_pid()
    import psutil
    low = psutil.BELOW_NORMAL_PRIORITY_CLASS if sys.platform == "win32" else psutil.Process().nice() + 10
    assert psutil.Process(spare_pid).nice() == low, "spare kernels run at low CPU priority"
    session = await warm_pool.get_or_create_session("s1", user_id="u1")
    assert session._kernel_pid() == spare_pid, "the spare kernel was used"
    import psutil
    normal = psutil.NORMAL_PRIORITY_CLASS if sys.platform == "win32" else psutil.Process().nice()
    assert psutil.Process(spare_pid).nice() == normal, "the user's kernel runs at normal CPU priority"
    ws = os.path.realpath(session.workspace_dir).replace("\\", "/")
    res = await session.execute(
        "import os, sys\n"
        "print(os.getcwd())\n"
        "print(os.environ['PYTHON_CLOUD_STUDIO_WORKSPACE'])\n"
        "print(any('.warm' in p for p in sys.path))\n"
        "print('decimal' in sys.modules, 'decimal' in globals())\n"
        "print(sys.modules['sitecustomize']._canon_ws)\n"
    )
    lines = [l.strip().replace("\\", "/") for l in _stdout(res).splitlines()]
    assert os.path.realpath(lines[0]).replace("\\", "/") == ws
    assert os.path.realpath(lines[1]).replace("\\", "/") == ws
    assert lines[2] == "False", "no trace of the spare's folder on sys.path"
    assert lines[3] == "True False", "preloaded, but not in the user's namespace"
    assert lines[4] == ws, "the runtime guard protects this workspace"

    # Another user's workspace stays blocked by the guard
    other = warm_pool.get_user_workspace_path("u2")
    res = await session.execute(f"try:\n    open({os.path.join(other, 'main.py')!r}).read()\nexcept PermissionError:\n    print('blocked')")
    assert _stdout(res).strip() == "blocked"

    # A restart starts a fresh kernel in the same workspace
    await session.restart()
    res = await session.execute("import os\nprint(os.getcwd())")
    assert os.path.realpath(_stdout(res).strip()).replace("\\", "/") == ws

    # The pool refills itself in the background
    for _ in range(100):
        if len(warm_pool._warm) == 1:
            break
        await asyncio.sleep(0.3)
    assert len(warm_pool._warm) == 1


async def test_admin_sessions_never_take_a_spare(warm_pool):
    spare = warm_pool._warm[0]
    await warm_pool.get_or_create_session("admin1", user_id="admin_super", is_admin=True)
    assert warm_pool._warm and warm_pool._warm[0] is spare


async def test_warm_kernel_matches_a_fresh_kernel(warm_pool):
    """A spare kernel, once taken, has the same environment as one started for its owner (including
    what the kernel sets up itself, such as the inline plot backend)."""
    probe = (
        "import os, json, matplotlib\n"
        "print(json.dumps({'env': dict(os.environ), 'backend': matplotlib.get_backend()}))\n"
    )
    warm = await warm_pool.get_or_create_session("w", user_id="same_user")
    warm_pool.warm_pool_size = 0  # the next session starts a kernel the normal way
    cold = await warm_pool.get_or_create_session("c", user_id="same_user")
    assert warm.warm_candidate is None and cold._kernel_pid() != warm._kernel_pid()
    import json
    got = {}
    for name, s in (("warm", warm), ("cold", cold)):
        out = json.loads(_stdout(await s.execute(probe)))
        # Set per kernel process by its launcher: always differ between two kernels
        for key in ("JPY_PARENT_PID", "IPY_INTERRUPT_EVENT", "JPY_INTERRUPT_EVENT"):
            out["env"].pop(key, None)
        got[name] = out
    assert got["warm"]["backend"] == got["cold"]["backend"] and "inline" in got["warm"]["backend"]
    assert got["warm"]["env"] == got["cold"]["env"], {
        k: (got["warm"]["env"].get(k), got["cold"]["env"].get(k))
        for k in set(got["warm"]["env"]) | set(got["cold"]["env"])
        if got["warm"]["env"].get(k) != got["cold"]["env"].get(k)
    }
    res = await warm.execute("import matplotlib.pyplot as plt\nplt.plot([1, 2]); plt.show()")
    assert any("image/png" in (o.get("data") or {}) for o in res.outputs), "inline plots work"
