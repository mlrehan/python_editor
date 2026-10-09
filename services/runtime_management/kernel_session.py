import asyncio
import os
import sys
import uuid
import time
from typing import Dict, Any, List, Optional, Callable, Coroutine
from jupyter_client.manager import AsyncKernelManager




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
        kernel_name: str = "python3"
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.kernel_name = kernel_name
        self.km: Optional[AsyncKernelManager] = None
        self.kc = None
        self.created_at = time.time()
        self.last_active_at = time.time()
        self.execution_count = 0
        self.is_running = False
        self._lock = asyncio.Lock()

        # Ensure workspace directory exists
        os.makedirs(self.workspace_dir, exist_ok=True)

    async def start(self, timeout: float = 25.0) -> None:
        """Starts the kernel process inside the isolated workspace directory."""
        async with self._lock:
            if self.is_running:
                return

            self.km = AsyncKernelManager(kernel_name=self.kernel_name)
            # Launch kernel with cwd set to the user's workspace directory
            await self.km.start_kernel(cwd=self.workspace_dir)
            self.kc = self.km.client()
            self.kc.start_channels()
            await self.kc.wait_for_ready(timeout=timeout)
            self.is_running = True
            self.last_active_at = time.time()

    async def execute(
        self,
        code: str,
        on_output_chunk: Optional[Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]] = None,
        timeout: Optional[float] = 60.0
    ) -> KernelExecutionResult:
        """
        Executes arbitrary Python code within the kernel.
        Streams outputs in real time via on_output_chunk callback and returns full execution result.
        """
        if not self.is_running or not self.kc:
            raise RuntimeError(f"Kernel session {self.session_id} is not running.")

        async with self._lock:
            start_time = time.time()
            self.last_active_at = start_time
            msg_id = self.kc.execute(code)
            result = KernelExecutionResult(msg_id=msg_id)

            loop = asyncio.get_event_loop()
            deadline = (start_time + timeout) if timeout else None

            while True:
                if deadline and time.time() > deadline:
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

                try:
                    # Wait for message with short timeout to allow loop cancellation check
                    msg = await asyncio.wait_for(self.kc.get_iopub_msg(), timeout=0.5)
                except asyncio.TimeoutError:
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

            result.execution_time = time.time() - start_time
            self.last_active_at = time.time()
            return result

    async def interrupt(self) -> None:
        """Interrupts currently executing calculation in the kernel."""
        if self.km:
            await self.km.interrupt_kernel()

    async def restart(self) -> None:
        """Restarts the kernel, resetting all variable definitions and execution counters."""
        async with self._lock:
            if self.km:
                await self.km.restart_kernel()
                self.execution_count = 0
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
