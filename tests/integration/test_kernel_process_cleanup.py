"""Processes started from a kernel (e.g. `!uvicorn ...`) must not outlive the cell/kernel that started them."""
import asyncio
import shutil
import tempfile
import time

import psutil
import pytest

from services.runtime_management.kernel_session import KernelSession

pytestmark = pytest.mark.asyncio

# A long-running shell command, like a web server started from a cell
SHELL_SLEEPER = 'import sys\n!"{sys.executable}" -c "import time; time.sleep(120)"'
# A background child process the cell does not wait for
BACKGROUND_SLEEPER = (
    "import subprocess, sys\n"
    "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
    "print(p.pid)"
)


@pytest.fixture
async def session():
    workspace = tempfile.mkdtemp(prefix="test_proc_cleanup_")
    sess = KernelSession(session_id="cleanup", user_id="user_cleanup", workspace_dir=workspace)
    await sess.start(timeout=30)
    yield sess
    await sess.shutdown()
    shutil.rmtree(workspace, ignore_errors=True)


def _is_gone(pid: int) -> bool:
    try:
        return psutil.Process(pid).status() == psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return True


async def _wait_until_gone(pids, timeout=8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if all(_is_gone(p) for p in pids):
            return True
        await asyncio.sleep(0.2)
    return all(_is_gone(p) for p in pids)


async def _children_once_started(sess: KernelSession, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        pids = [p.pid for p in sess._child_processes()]
        if pids:
            return pids
        await asyncio.sleep(0.2)
    raise AssertionError("the cell never started a child process")


async def test_timeout_stops_processes_started_by_the_cell(session):
    task = asyncio.create_task(session.execute(SHELL_SLEEPER, timeout=4))
    pids = await _children_once_started(session)

    result = await asyncio.wait_for(task, 30)
    assert result.error["ename"] == "TimeoutError"
    assert await _wait_until_gone(pids), "child process survived the cell timeout"


async def test_interrupt_stops_a_cell_blocked_on_a_child_process(session):
    task = asyncio.create_task(session.execute(SHELL_SLEEPER, timeout=60))
    pids = await _children_once_started(session)

    started = time.time()
    await session.interrupt()
    result = await asyncio.wait_for(task, 30)
    assert time.time() - started < 15, "Stop did not end the cell"
    assert await _wait_until_gone(pids)

    follow_up = await session.execute("print('kernel still usable')")
    assert "kernel still usable" in "".join(o.get("text", "") for o in follow_up.outputs)
    assert result.status in ("error", "ok")


async def test_interrupt_keeps_processes_started_by_earlier_cells(session):
    # A server deliberately started in an earlier cell survives pressing Stop on a later cell
    result = await session.execute(BACKGROUND_SLEEPER)
    earlier_pid = int("".join(o.get("text", "") for o in result.outputs).strip())

    task = asyncio.create_task(session.execute(SHELL_SLEEPER, timeout=60))
    deadline = time.time() + 15
    new_pids = []
    while not new_pids and time.time() < deadline:
        new_pids = [p.pid for p in session._child_processes() if p.pid != earlier_pid]
        await asyncio.sleep(0.2)
    assert new_pids

    await session.interrupt()
    await asyncio.wait_for(task, 30)
    assert await _wait_until_gone(new_pids)
    assert not _is_gone(earlier_pid), "Stop killed a process started by an earlier cell"


async def test_restart_stops_background_child_processes(session):
    result = await session.execute(BACKGROUND_SLEEPER)
    pid = int("".join(o.get("text", "") for o in result.outputs).strip())
    assert not _is_gone(pid)

    await session.restart()
    assert await _wait_until_gone([pid]), "background process survived kernel restart"


async def test_shutdown_stops_background_child_processes():
    workspace = tempfile.mkdtemp(prefix="test_proc_cleanup_")
    sess = KernelSession(session_id="cleanup-shutdown", user_id="user_cleanup", workspace_dir=workspace)
    await sess.start(timeout=30)
    try:
        result = await sess.execute(BACKGROUND_SLEEPER)
        pid = int("".join(o.get("text", "") for o in result.outputs).strip())
        await sess.shutdown()
        assert await _wait_until_gone([pid]), "background process survived kernel shutdown"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


async def test_restart_while_server_command_runs_does_not_hang(session):
    task = asyncio.create_task(session.execute(SHELL_SLEEPER, timeout=300))
    pids = await _children_once_started(session)

    started = time.time()
    await asyncio.wait_for(session.restart(), 60)
    assert time.time() - started < 45
    # The cell ends once its child is stopped (status depends on how the shell reports it)
    await asyncio.wait_for(task, 30)
    assert await _wait_until_gone(pids)

    follow_up = await session.execute("print('fresh kernel')")
    assert "fresh kernel" in "".join(o.get("text", "") for o in follow_up.outputs)
