import asyncio
import os
import sys
import uuid
import time
from queue import Empty
from typing import Dict, Any, List, Optional, Callable, Coroutine
from jupyter_client.manager import AsyncKernelManager
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
        # stdin state for the current execution: when the pending input_request started,
        # and how long execution has spent waiting on the user (excluded from the timeout)
        self._input_pending_since: Optional[float] = None
        self._input_wait_total: float = 0.0
        # Browser connections currently using this kernel, and when the last one left
        self.attached_clients = 0
        self.detached_at: Optional[float] = None
        # Why the kernel was stopped from outside (e.g. memory limit); reported to the running cell
        self.death_reason: Optional[str] = None

        # Ensure workspace directory exists
        os.makedirs(self.workspace_dir, exist_ok=True)

    async def start(self, timeout: float = 25.0) -> None:
        """Starts the kernel process inside the isolated workspace directory with a sanitized environment."""
        async with self._lock:
            if self.is_running:
                return

            self.km = AsyncKernelManager(kernel_name=self.kernel_name)
            # Build sanitized environment stripping server secrets and injecting user's .env
            try:
                from services.api.package_security import get_sanitized_kernel_env
            except ImportError:
                from ..api.package_security import get_sanitized_kernel_env
            clean_env = get_sanitized_kernel_env(self.workspace_dir, self.user_id, self.is_admin)

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
                    await self.interrupt()
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
                    result.outputs.append(chunk)
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

                    result.outputs.append(chunk)
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
                    result.outputs.append(chunk)
                    result.error = chunk
                    if on_output_chunk:
                        await on_output_chunk(chunk)

            self._input_pending_since = None
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

    def send_input(self, value: str) -> bool:
        """Answers the kernel's pending input_request. Returns False if nothing is waiting for input."""
        if self._input_pending_since is None or not self.kc:
            return False
        self._input_wait_total += time.time() - self._input_pending_since
        self._input_pending_since = None
        self.kc.input(value)
        self.last_active_at = time.time()
        return True

    async def interrupt(self) -> None:
        """Interrupts currently executing calculation in the kernel."""
        if self.km:
            await self.km.interrupt_kernel()

    async def restart(self, timeout: float = 25.0) -> None:
        """Restarts the kernel cleanly, resetting all variable definitions and execution counters."""
        # A running cell (possibly blocked on input()) holds the lock; interrupt it so restart can proceed
        if self._lock.locked() and self.km:
            try:
                await self.interrupt()
            except Exception:
                pass
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

            async with _start_slots():
                await self.km.start_kernel(cwd=self.workspace_dir, env=clean_env)
                self.kc = self.km.client()
                self.kc.start_channels()
                await self.kc.wait_for_ready(timeout=timeout)
            self.is_running = True
            self.death_reason = None
            self.last_active_at = time.time()

    async def shutdown(self) -> None:
        """Gracefully halts the kernel and releases resources."""
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
