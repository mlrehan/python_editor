import asyncio
import logging
import os
import sys
import uuid
import time
from queue import Empty
from typing import Dict, Any, List, Optional, Callable, Coroutine
from jupyter_client.manager import AsyncKernelManager
from .introspection import SETUP_CODE

logger = logging.getLogger(__name__)
import json
import shutil

# Runs inside a pre-started kernel when it is handed to its owner (in its own globals: nothing is
# added to the user's namespace). Puts the kernel in the owner's workspace with the environment a
# fresh start there would have.
_ADOPT_SCRIPT = """
import os, sys, json
new_env = json.loads(%(env)r)
launch_env = json.loads(%(launch_env)r)
workspace = %(workspace)r
old_ws = os.environ.get("PYTHON_CLOUD_STUDIO_WORKSPACE", "")
old_paths = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p]
# Only what the spare was launched with is replaced; what the kernel set up itself at start-up
# (e.g. MPLBACKEND for inline plots, TERM) is kept, as in a kernel started for this owner
for key in list(os.environ):
    if key in launch_env and key not in new_env and os.environ[key] == launch_env[key]:
        del os.environ[key]
for key, value in new_env.items():
    if key in launch_env and os.environ.get(key) != launch_env[key]:
        continue  # changed by the kernel itself after launch
    os.environ[key] = value
os.chdir(workspace)
new_paths = [p for p in new_env.get("PYTHONPATH", "").split(os.pathsep) if p]
sys.path[:] = [p for p in sys.path if p not in old_paths and not (p and old_ws and os.path.abspath(p).startswith(old_ws))]
at = 1 if sys.path and sys.path[0] == "" else 0
for p in reversed(new_paths):
    if p not in sys.path:
        sys.path.insert(at, p)
guard = sys.modules.get("sitecustomize")
if guard is not None and hasattr(guard, "_canon_ws"):
    guard._canon_ws = os.path.realpath(workspace).rstrip("\\\\/").replace("\\\\", "/")
"""
import weakref

# Kernel start-up is CPU heavy (~1-3 s of CPU each). Starting dozens at once on a few cores makes
# every one of them miss the readiness timeout, so starts are queued to this many at a time.
_start_concurrency = max(2, os.cpu_count() or 2)
_start_semaphores: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore]" = weakref.WeakKeyDictionary()


def set_start_concurrency(limit: int) -> None:
    """Sets how many kernels may start simultaneously (0 or less = one per CPU core, minimum 2)."""
    global _start_concurrency
    _start_concurrency = limit if limit > 0 else max(2, os.cpu_count() or 2)
    _start_semaphores.clear()


def _start_slots() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    sem = _start_semaphores.get(loop)
    if sem is None:
        sem = asyncio.Semaphore(_start_concurrency)
        _start_semaphores[loop] = sem
    return sem





# Marker left in an output list by clear_output(wait=True): the list is cleared when the next output arrives
_CLEAR_PENDING = {"output_type": "clear_output", "wait": True}


def apply_output(outputs: List[Dict[str, Any]], chunk: Dict[str, Any]) -> None:
    """Applies one kernel output to a cell's output list with Jupyter semantics.

    clear_output(wait=False) empties the list; clear_output(wait=True) empties it when the next output
    arrives (so a progress display does not flicker); update_display_data replaces every output that
    was displayed with the same display_id. The browser applies the same rules to the streamed chunks.
    """
    kind = chunk.get("output_type")
    if kind == "clear_output":
        if chunk.get("wait"):
            if not (outputs and outputs[-1] is _CLEAR_PENDING):
                outputs.append(_CLEAR_PENDING)
        else:
            outputs.clear()
        return
    if outputs and outputs[-1] is _CLEAR_PENDING:
        outputs.clear()
    if kind == "update_display_data":
        for i, existing in enumerate(outputs):
            if existing.get("display_id") == chunk.get("display_id") and existing.get("output_type") in ("display_data", "execute_result"):
                outputs[i] = {**existing, "data": chunk.get("data", {}), "metadata": chunk.get("metadata", {})}
        return
    outputs.append(chunk)

class KernelExecutionResult:
    """Encapsulates the outputs, status, and metadata of a cell execution."""
    def __init__(self, msg_id: str):
        self.msg_id = msg_id
        self.status: str = "ok"  # "ok", "error", "abort"
        self.execution_count: Optional[int] = None
        self.outputs: List[Dict[str, Any]] = []
        self.error: Optional[Dict[str, Any]] = None
        self.execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "msg_id": self.msg_id,
            "status": self.status,
            "execution_count": self.execution_count,
            "outputs": self.outputs,
            "error": self.error,
            "execution_time": round(self.execution_time, 4),
        }


class KernelSession:
    """
    Manages an individual genuine IPyKernel process.
    Provides async execution, streaming output callbacks, and lifecycle controls.
    """
    def __init__(
        self,
        session_id: str,
        user_id: str,
        workspace_dir: str,
        kernel_name: str = "python3",
        is_admin: bool = False
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.kernel_name = kernel_name
        self.is_admin = is_admin
        self.km: Optional[AsyncKernelManager] = None
        self.kc = None
        self.created_at = time.time()
        self.last_active_at = time.time()
        self.execution_count = 0
        self.is_running = False
        self._lock = asyncio.Lock()
        # A pre-started kernel this session may take over instead of starting one (see start())
        self.warm_candidate: Optional["KernelSession"] = None
        # Environment the kernel was launched with (replaced when a spare is taken)
        self.launch_env: Dict[str, str] = {}
        # True while an editor introspection (not user code) holds the lock
        self._introspection_active = False
        # stdin state for the current execution: when the pending input_request started,
        # and how long execution has spent waiting on the user (excluded from the timeout)
        self._input_pending_since: Optional[float] = None
        self._input_wait_total: float = 0.0
        # Browser connections currently using this kernel, and when the last one left
        self.attached_clients = 0
        self.detached_at: Optional[float] = None
        # Why the kernel was stopped from outside (e.g. memory limit); reported to the running cell
        self.death_reason: Optional[str] = None
        # Pending "interrupt did not work -> stop child processes" follow-up, if any
        self._escalation: Optional[asyncio.Task] = None
        # Kernel child processes that already existed when the current cell started
        self._cell_start_children: set = set()

        # Ensure workspace directory exists
        os.makedirs(self.workspace_dir, exist_ok=True)

    async def start(self, timeout: float = 25.0) -> None:
        """Starts the kernel process inside the isolated workspace directory with a sanitized environment."""
        async with self._lock:
            if self.is_running:
                return

            # A pre-started kernel (libraries already imported) makes the first run much faster
            warm, self.warm_candidate = self.warm_candidate, None
            if warm is not None and await self._take_over(warm):
                self.is_running = True
                self.death_reason = None
                self.last_active_at = time.time()
                return

            self.km = AsyncKernelManager(kernel_name=self.kernel_name)
            # Build sanitized environment stripping server secrets and injecting user's .env
            try:
                from services.api.package_security import get_sanitized_kernel_env
            except ImportError:
                from ..api.package_security import get_sanitized_kernel_env
            clean_env = get_sanitized_kernel_env(self.workspace_dir, self.user_id, self.is_admin)
            self.launch_env = dict(clean_env)

            # Launch kernel with cwd set to the user's workspace directory and isolated environment
            async with _start_slots():
                await self.km.start_kernel(cwd=self.workspace_dir, env=clean_env)
                self.kc = self.km.client()
                self.kc.start_channels()
                await self.kc.wait_for_ready(timeout=timeout)
            self.is_running = True
            self.death_reason = None
            self.last_active_at = time.time()

    @property
    def is_busy(self) -> bool:
        """True while a cell is executing (or a restart is in progress)."""
        return self._lock.locked()

    def attach_client(self) -> None:
        self.attached_clients += 1
        self.detached_at = None

    def detach_client(self) -> None:
        self.attached_clients = max(0, self.attached_clients - 1)
        if self.attached_clients == 0:
            self.detached_at = time.time()

    def _kernel_pid(self) -> Optional[int]:
        provisioner = getattr(self.km, "provisioner", None) if self.km else None
        pid = getattr(provisioner, "pid", None)
        if pid is None:
            process = getattr(provisioner, "process", None)
            pid = getattr(process, "pid", None)
        return pid

    def memory_usage_bytes(self) -> Optional[int]:
        """Resident memory of the kernel process and its children (e.g. !pip, subprocesses)."""
        pid = self._kernel_pid()
        if not pid or not self.is_running:
            return None
        try:
            import psutil
            proc = psutil.Process(pid)
            total = proc.memory_info().rss
            for child in proc.children(recursive=True):
                try:
                    total += child.memory_info().rss
                except psutil.Error:
                    pass
            return total
        except Exception:
            return None

    async def kill(self, reason: str) -> None:
        """
        Force-stops the kernel from outside (does not wait for a running cell).
        A cell that is executing reports `reason`; the next execution restarts the kernel.
        """
        self.death_reason = reason
        self.is_running = False
        self._input_pending_since = None
        await self.kill_child_processes()
        if self.km:
            try:
                await self.km.shutdown_kernel(now=True)
            except Exception:
                pass

    async def ensure_running(self) -> bool:
        """Restarts a kernel that died or was killed. Returns True if a restart was needed."""
        if self.is_running and self.km and await self.km.is_alive():
            return False
        await self.restart()
        return True

    async def execute(
        self,
        code: str,
        on_output_chunk: Optional[Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]] = None,
        timeout: Optional[float] = 60.0,
        on_input_request: Optional[Callable[[str, bool], Coroutine[Any, Any, None]]] = None,
    ) -> KernelExecutionResult:
        """
        Executes arbitrary Python code within the kernel.
        Streams outputs in real time via on_output_chunk callback and returns full execution result.
        If on_input_request is given, input()/getpass() prompts are forwarded to it and answered
        via send_input(); otherwise stdin is disabled and input() raises StdinNotImplementedError.
        """
        if not self.is_running or not self.kc:
            raise RuntimeError(f"Kernel session {self.session_id} is not running.")

        async with self._lock:
            start_time = time.time()
            self.last_active_at = start_time
            # psutil walks the process tree: run it in a thread so other users' streams keep flowing
            self._cell_start_children = {p.pid for p in await asyncio.to_thread(self._child_processes)}
            allow_stdin = on_input_request is not None
            msg_id = self.kc.execute(code, allow_stdin=allow_stdin)
            result = KernelExecutionResult(msg_id=msg_id)
            self._input_pending_since = None
            self._input_wait_total = 0.0
            next_liveness_check = start_time + 1.0

            while True:
                # A crashed or killed kernel never sends "idle"; detect it instead of waiting for the timeout
                if time.time() >= next_liveness_check:
                    next_liveness_check = time.time() + 1.0
                    if self.death_reason or not self.km or not await self.km.is_alive():
                        self.is_running = False
                        self._input_pending_since = None
                        result.status = "error"
                        died_output = {
                            "output_type": "error",
                            "ename": "KernelDied",
                            "evalue": self.death_reason or (
                                "The Python kernel stopped unexpectedly (it crashed or ran out of memory). "
                                "It will restart on the next run; variables were lost."
                            ),
                            "traceback": [],
                        }
                        result.outputs.append(died_output)
                        result.error = died_output
                        if on_output_chunk:
                            await on_output_chunk(died_output)
                        break

                # Time spent waiting for the user to answer input() does not count toward the timeout
                deadline = (start_time + timeout + self._input_wait_total) if timeout else None
                if deadline and self._input_pending_since is None and time.time() > deadline:
                    # The cell is abandoned: interrupt it and stop anything it started
                    # (e.g. a `!uvicorn ...` server), which would otherwise keep running forever
                    cell_processes = self._current_cell_processes()
                    await self.interrupt(escalate_after=None)
                    await self.kill_child_processes(processes=cell_processes + [
                        p for p in self._current_cell_processes() if p.pid not in {c.pid for c in cell_processes}
                    ])
                    result.status = "error"
                    timeout_output = {
                        "output_type": "error",
                        "ename": "TimeoutError",
                        "evalue": f"Execution exceeded {timeout} seconds limit.",
                        "traceback": [f"TimeoutError: Cell execution exceeded timeout of {timeout}s"],
                    }
                    result.outputs.append(timeout_output)
                    result.error = timeout_output
                    if on_output_chunk:
                        await on_output_chunk(timeout_output)
                    break

                if allow_stdin and self._input_pending_since is None:
                    try:
                        stdin_msg = await self.kc.get_stdin_msg(timeout=0)
                    except Empty:
                        stdin_msg = None
                    if (
                        stdin_msg
                        and stdin_msg.get("header", {}).get("msg_type") == "input_request"
                        and stdin_msg.get("parent_header", {}).get("msg_id") == msg_id
                    ):
                        self._input_pending_since = time.time()
                        content = stdin_msg.get("content", {})
                        await on_input_request(content.get("prompt", ""), bool(content.get("password", False)))

                try:
                    # Short poll so the loop can also service stdin requests and the deadline
                    msg = await self.kc.get_iopub_msg(timeout=0.1)
                except Empty:
                    continue

                # Verify message belongs to our execution request
                parent_header = msg.get("parent_header", {})
                if parent_header.get("msg_id") != msg_id:
                    continue

                msg_type = msg.get("header", {}).get("msg_type")
                content = msg.get("content", {})

                if msg_type == "status":
                    execution_state = content.get("execution_state")
                    if execution_state == "idle":
                        break

                elif msg_type == "execute_input":
                    self.execution_count = content.get("execution_count", self.execution_count)
                    result.execution_count = self.execution_count

                elif msg_type == "stream":
                    chunk = {
                        "output_type": "stream",
                        "name": content.get("name", "stdout"),
                        "text": content.get("text", ""),
                    }
                    apply_output(result.outputs, chunk)
                    if on_output_chunk:
                        await on_output_chunk(chunk)

                elif msg_type in ("display_data", "execute_result"):
                    chunk = {
                        "output_type": msg_type,
                        "data": content.get("data", {}),
                        "metadata": content.get("metadata", {}),
                    }
                    if msg_type == "execute_result":
                        chunk["execution_count"] = content.get("execution_count", self.execution_count)
                        result.execution_count = chunk["execution_count"]
                    # display(..., display_id=...) handles: later update_display_data replaces this output
                    display_id = (content.get("transient") or {}).get("display_id")
                    if display_id:
                        chunk["display_id"] = display_id

                    apply_output(result.outputs, chunk)
                    if on_output_chunk:
                        await on_output_chunk(chunk)

                elif msg_type == "update_display_data":
                    display_id = (content.get("transient") or {}).get("display_id")
                    if display_id:
                        chunk = {
                            "output_type": "update_display_data",
                            "display_id": display_id,
                            "data": content.get("data", {}),
                            "metadata": content.get("metadata", {}),
                        }
                        apply_output(result.outputs, chunk)
                        if on_output_chunk:
                            await on_output_chunk(chunk)

                elif msg_type == "clear_output":
                    # IPython.display.clear_output(wait=...): progress bars, live-updating loops
                    chunk = {"output_type": "clear_output", "wait": bool(content.get("wait", False))}
                    apply_output(result.outputs, chunk)
                    if on_output_chunk:
                        await on_output_chunk(chunk)

                elif msg_type == "error":
                    result.status = "error"
                    chunk = {
                        "output_type": "error",
                        "ename": content.get("ename", "Exception"),
                        "evalue": content.get("evalue", ""),
                        "traceback": content.get("traceback", []),
                    }
                    apply_output(result.outputs, chunk)
                    result.error = chunk
                    if on_output_chunk:
                        await on_output_chunk(chunk)

            self._input_pending_since = None
            if result.outputs and result.outputs[-1] is _CLEAR_PENDING:
                result.outputs.pop()
            result.execution_time = time.time() - start_time
            self.last_active_at = time.time()

            # If a package was installed, refresh kernel runtime paths so new modules import immediately
            if self.is_running and ("%pip" in code or "!pip" in code or "pip install" in code):
                try:
                    refresh_code = (
                        "import sys, os, site, importlib\n"
                        f"_local_dir = {repr(os.path.join(self.workspace_dir, '.local'))}\n"
                        "if os.path.exists(_local_dir):\n"
                        "    for _root, _dirs, _ in os.walk(_local_dir):\n"
                        "        if os.path.basename(_root) == 'site-packages':\n"
                        "            if _root not in sys.path:\n"
                        "                sys.path.insert(0, _root)\n"
                        "            site.addsitedir(_root)\n"
                        "importlib.invalidate_caches()\n"
                    )
                    ref_msg_id = self.kc.execute(refresh_code, silent=True, store_history=False)
                    ref_deadline = time.time() + 5.0
                    while time.time() < ref_deadline:
                        try:
                            ref_msg = await asyncio.wait_for(self.kc.get_iopub_msg(), timeout=0.2)
                            if ref_msg.get("parent_header", {}).get("msg_id") == ref_msg_id:
                                if ref_msg.get("header", {}).get("msg_type") == "status" and ref_msg.get("content", {}).get("execution_state") == "idle":
                                    break
                        except asyncio.TimeoutError:
                            break
                except Exception:
                    pass

            return result

    @property
    def input_pending(self) -> bool:
        return self._input_pending_since is not None

    async def _take_over(self, warm: "KernelSession") -> bool:
        """Takes over a pre-started kernel and moves it into this session's workspace (lock held)."""
        if not warm.is_running or not warm.kc:
            await warm.shutdown()
            return False
        self.km, self.kc = warm.km, warm.kc
        warm.km = warm.kc = None
        warm.is_running = False
        try:
            from services.api.package_security import get_sanitized_kernel_env
        except ImportError:
            from ..api.package_security import get_sanitized_kernel_env
        env = get_sanitized_kernel_env(self.workspace_dir, self.user_id, self.is_admin)
        # Spares run at low CPU priority; the owner's kernel gets normal priority (or a fresh kernel)
        if not await asyncio.to_thread(self.set_cpu_priority, False):
            logger.warning("Could not restore the CPU priority of a spare kernel; starting a fresh one")
            shutil.rmtree(warm.workspace_dir, ignore_errors=True)
            await self._discard_taken_kernel()
            return False
        script = _ADOPT_SCRIPT % {
            "env": json.dumps(env),
            "launch_env": json.dumps(warm.launch_env),
            "workspace": self.workspace_dir,
        }
        content = await self._shell_request_unlocked(
            lambda: self.kc.execute("exec(%r, {})" % script, silent=True, store_history=False, allow_stdin=False),
            timeout=10.0,
        )
        shutil.rmtree(warm.workspace_dir, ignore_errors=True)
        if content is not None and content.get("status") == "ok":
            return True
        # Could not move it: discard it and start a fresh kernel instead
        await self._discard_taken_kernel()
        return False

    async def _discard_taken_kernel(self) -> None:
        try:
            self.kc.stop_channels()
            await self.km.shutdown_kernel(now=True)
        except Exception:
            pass
        self.km = self.kc = None

    def set_cpu_priority(self, low: bool) -> bool:
        """Lowers (spare kernels: they never slow down people's running code) or restores the kernel's
        CPU priority. Returns False if it could not be set."""
        pid = self._kernel_pid()
        if pid is None:
            return False
        try:
            import psutil
            proc = psutil.Process(pid)
            if sys.platform == "win32":
                proc.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if low else psutil.NORMAL_PRIORITY_CLASS)
            else:
                # The API's own priority is "normal" for its kernels
                proc.nice(psutil.Process().nice() + (10 if low else 0))
            return True
        except Exception:
            return False

    async def preload(self, modules: List[str], timeout: float = 120.0) -> None:
        """Imports libraries into sys.modules (not the user's namespace), so `import pandas` is instant."""
        code = "for _m in %r:\n    try:\n        __import__(_m)\n    except Exception:\n        pass\n" % list(modules)
        async with self._lock:
            await self._shell_request_unlocked(
                lambda: self.kc.execute("exec(%r, {})" % code, silent=True, store_history=False, allow_stdin=False),
                timeout,
            )

    async def _shell_request_unlocked(self, send: Callable[[], str], timeout: float) -> Optional[Dict[str, Any]]:
        """Sends one shell request and waits for its reply (caller holds the lock)."""
        msg_id = send()
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            try:
                reply = await self.kc.get_shell_msg(timeout=remaining)
            except Empty:
                return None
            # Skip replies to earlier requests still queued on the shell channel
            if reply.get("parent_header", {}).get("msg_id") == msg_id:
                return reply.get("content", {})

    async def _editor_shell_request(self, send: Callable[[], str], timeout: float) -> Optional[Dict[str, Any]]:
        """Sends one editor request (introspection or completion) and returns its shell reply content.

        Never runs alongside user code: skipped (None) while a cell runs or waits for input(). Editor
        requests are serialized on the session lock, so each one reads only its own shell reply.
        """
        if not self.is_running or not self.kc or self.input_pending:
            return None
        # User code (or a restart) holds the lock: skip. Another editor request holds it: wait our turn.
        if self._lock.locked() and not self._introspection_active:
            return None
        try:
            await asyncio.wait_for(self._lock.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
        self._introspection_active = True
        try:
            if not self.kc:
                return None
            return await self._shell_request_unlocked(send, timeout)
        finally:
            self._introspection_active = False
            self._lock.release()

    async def evaluate_silently(self, expression: str, timeout: float = 1.0) -> Optional[str]:
        """Evaluates one editor-introspection expression (never user code) in the kernel namespace.

        Runs as a silent request: no history, no execution count change, no output. Returns the
        expression's text/plain repr, or None when the kernel is not ready, is running code or
        waiting for input(), or does not answer within `timeout` seconds. A cell started meanwhile
        waits at most `timeout`.
        """
        content = await self._editor_shell_request(
            lambda: self.kc.execute(
                SETUP_CODE,
                silent=True,
                store_history=False,
                user_expressions={"r": expression},
                allow_stdin=False,
            ),
            timeout,
        )
        if content is None:
            return None
        result = (content.get("user_expressions") or {}).get("r") or {}
        if result.get("status") != "ok":
            return None
        return (result.get("data") or {}).get("text/plain")

    async def complete_quietly(self, code: str, cursor_pos: int, timeout: float = 0.5) -> Optional[List[str]]:
        """The kernel's own completer (IPython) for `code` at `cursor_pos`; None if unavailable."""
        content = await self._editor_shell_request(lambda: self.kc.complete(code, cursor_pos), timeout)
        if content is None:
            return None
        return list(content.get("matches") or [])

    def send_input(self, value: str) -> bool:
        """Answers the kernel's pending input_request. Returns False if nothing is waiting for input."""
        if self._input_pending_since is None or not self.kc:
            return False
        self._input_wait_total += time.time() - self._input_pending_since
        self._input_pending_since = None
        self.kc.input(value)
        self.last_active_at = time.time()
        return True

    def _child_processes(self) -> List[Any]:
        """All processes started by the kernel (shell commands, subprocesses, servers), recursively."""
        pid = self._kernel_pid()
        if not pid:
            return []
        try:
            import psutil
            return psutil.Process(pid).children(recursive=True)
        except Exception:
            return []

    def _current_cell_processes(self) -> List[Any]:
        """Kernel child processes started since the current/last cell began."""
        return [c for c in self._child_processes() if c.pid not in self._cell_start_children]

    async def kill_child_processes(
        self,
        grace_seconds: float = 2.0,
        only_current_cell: bool = False,
        processes: Optional[List[Any]] = None,
    ) -> int:
        """
        Terminates processes the kernel started (e.g. `!uvicorn ...`, subprocess.Popen) and
        force-kills those still alive after grace_seconds. Interrupting or restarting a kernel does
        not stop these, so without this they keep running (and holding ports/memory) forever.
        With only_current_cell, processes that already existed when the last cell started (e.g. a
        server deliberately launched by an earlier cell) are left alone. `processes` kills an
        explicit list captured earlier: an interrupt can kill the intermediate shell, after which
        the real worker is orphaned and no longer appears under the kernel.
        Returns the number of processes stopped.
        """
        if processes is not None:
            children = processes
        elif only_current_cell:
            children = self._current_cell_processes()
        else:
            children = self._child_processes()
        if not children:
            return 0

        def _terminate() -> int:
            import psutil
            for child in children:
                try:
                    child.terminate()
                except psutil.Error:
                    pass
            _, alive = psutil.wait_procs(children, timeout=grace_seconds)
            for child in alive:
                try:
                    child.kill()
                except psutil.Error:
                    pass
            psutil.wait_procs(alive, timeout=grace_seconds)
            return len(children)

        return await asyncio.to_thread(_terminate)

    async def interrupt(self, escalate_after: Optional[float] = 3.0) -> None:
        """
        Interrupts the currently executing cell. Once the cell has stopped, or escalate_after
        seconds later if it is still blocked on a shell command or child process that ignores the
        interrupt, the processes started by that cell are terminated. An interrupt alone often
        ends the cell's wait (e.g. `!uvicorn ...`) while leaving the process running.
        """
        # Capture the cell's process tree before interrupting: the interrupt may kill the
        # intermediate shell and orphan the real worker process
        cell_processes = self._current_cell_processes() if escalate_after and self.is_busy else []
        if self.km:
            await self.km.interrupt_kernel()
        if escalate_after and self.is_busy and self._escalation is None:
            self._escalation = asyncio.create_task(self._escalate_interrupt(escalate_after, cell_processes))

    async def _escalate_interrupt(self, delay: float, cell_processes: List[Any]) -> None:
        try:
            deadline = time.time() + delay
            while self.is_busy and time.time() < deadline:
                await asyncio.sleep(0.2)
            # Anything the cell started that is still running (captured earlier, or still attached)
            known = {p.pid for p in cell_processes}
            extra = [p for p in self._current_cell_processes() if p.pid not in known]
            await self.kill_child_processes(processes=cell_processes + extra)
        except Exception:
            pass
        finally:
            self._escalation = None

    async def _stop_running_cell(self, reason: str, wait_seconds: float = 10.0) -> None:
        """
        Makes sure no cell holds the kernel before a restart/shutdown: interrupt it, stop its child
        processes, and if it still has not finished after wait_seconds, force-stop the kernel process
        (the running execute() notices within ~1s, reports `reason` and releases the lock).
        """
        # Capture the whole tree first: interrupting can orphan workers started through a shell
        captured = self._child_processes()
        if self._lock.locked() and self.km:
            try:
                await self.interrupt(escalate_after=None)
            except Exception:
                pass
        known = {p.pid for p in captured}
        await self.kill_child_processes(
            processes=captured + [p for p in self._child_processes() if p.pid not in known]
        )
        deadline = time.time() + wait_seconds
        while self._lock.locked() and time.time() < deadline:
            await asyncio.sleep(0.2)
        if self._lock.locked() and self.km:
            self.death_reason = reason
            try:
                await self.km.shutdown_kernel(now=True)
            except Exception:
                pass

    async def restart(self, timeout: float = 25.0) -> None:
        """Restarts the kernel cleanly, resetting all variable definitions and execution counters."""
        # A running cell (possibly blocked on input() or a child process) holds the lock;
        # interrupt it and stop its child processes so restart can proceed
        await self._stop_running_cell("The kernel was restarted while this cell was running.")
        async with self._lock:
            if self.kc:
                try:
                    self.kc.stop_channels()
                except Exception:
                    pass
                self.kc = None

            if self.km:
                try:
                    await self.km.shutdown_kernel(now=True)
                except Exception:
                    pass
                self.km = None

            self.is_running = False
            self.execution_count = 0

            # Start fresh kernel instance with updated environment
            self.km = AsyncKernelManager(kernel_name=self.kernel_name)
            try:
                from services.api.package_security import get_sanitized_kernel_env
            except ImportError:
                from ..api.package_security import get_sanitized_kernel_env
            clean_env = get_sanitized_kernel_env(self.workspace_dir, self.user_id, self.is_admin)
            self.launch_env = dict(clean_env)

            async with _start_slots():
                await self.km.start_kernel(cwd=self.workspace_dir, env=clean_env)
                self.kc = self.km.client()
                self.kc.start_channels()
                await self.kc.wait_for_ready(timeout=timeout)
            self.is_running = True
            self.death_reason = None
            self.last_active_at = time.time()

    async def shutdown(self) -> None:
        """Gracefully halts the kernel, every process it started, and releases resources."""
        await self._stop_running_cell("The kernel was shut down while this cell was running.")
        async with self._lock:
            if self.kc:
                try:
                    self.kc.stop_channels()
                except Exception:
                    pass
                self.kc = None

            if self.km:
                try:
                    await self.km.shutdown_kernel(now=True)
                except Exception:
                    pass
                self.km = None

            self.is_running = False

    def is_alive(self) -> bool:
        """Probes whether the underlying process is active."""
        if self.km and self.is_running:
            return self.km.has_kernel
        return False
