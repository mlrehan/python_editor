import asyncio
import logging
import shutil
import time
import os
import uuid
from typing import Callable, Dict, List, Optional
from .kernel_session import KernelSession, set_start_concurrency

logger = logging.getLogger(__name__)


class KernelCapacityError(ValueError):
    """Raised when a new kernel cannot be started because a quota or the server capacity is reached."""


def is_guest_user_id(user_id: str) -> bool:
    return not user_id or user_id in ("public", "guest", "public_guest") or user_id.startswith("guest_")


class KernelPoolManager:
    """
    Manages multi-tenant kernel instances.
    Enforces per-user, guest and server-wide quotas, reaps idle or abandoned kernels,
    enforces a per-kernel memory limit, and routes workspace directories.
    """
    def __init__(
        self,
        workspaces_root: str = "./storage/workspaces",
        max_kernels_per_user: int = 5,
        idle_timeout_seconds: int = 3600,
        max_total_kernels: int = 40,
        max_guest_kernels: int = 10,
        detached_timeout_seconds: int = 600,
        max_kernel_memory_mb: int = 1024,
        start_concurrency: int = 0,
        warm_pool_size: int = 0,
        preload_modules: Optional[List[str]] = None,
        warm_refill_delay_seconds: float = 20.0,
    ):
        self.workspaces_root = os.path.abspath(workspaces_root)
        self.max_kernels_per_user = max_kernels_per_user
        self.idle_timeout_seconds = idle_timeout_seconds
        self.max_total_kernels = max_total_kernels
        self.max_guest_kernels = max_guest_kernels
        self.detached_timeout_seconds = detached_timeout_seconds
        self.max_kernel_memory_mb = max_kernel_memory_mb
        set_start_concurrency(start_concurrency)
        self._sessions: Dict[str, KernelSession] = {}
        self._lock = asyncio.Lock()
        os.makedirs(self.workspaces_root, exist_ok=True)
        # Pre-started kernels handed to new sessions (each used by exactly one owner, never returned)
        self.warm_pool_size = warm_pool_size
        self.preload_modules = preload_modules or []
        self._warm: List[KernelSession] = []
        self._warm_filling = False
        # A spare is replaced only after this delay: starting it (and importing pandas) right away
        # would compete for CPU with the new user's first runs
        self.warm_refill_delay_seconds = warm_refill_delay_seconds
        # Set by the API: maps a guest workspace id to its private folder
        self.guest_path_resolver: Optional[Callable[[str], str]] = None
        # Extra work for each maintenance pass (e.g. removing long-unused guest workspaces)
        self.maintenance_hooks: List[Callable[[], None]] = []

    def get_public_workspace_path(self) -> str:
        """The starter files copied into every new guest workspace (never a guest's working folder)."""
        path = os.path.join(self.workspaces_root, "public")
        os.makedirs(path, exist_ok=True)
        self._seed_default_workspace(path)
        return path

    def get_user_workspace_path(self, user_id: str, project_id: Optional[str] = None) -> str:
        """Computes isolated canonical workspace directory path for a user/project."""
        if user_id and user_id.startswith("guest_") and self.guest_path_resolver:
            return self.guest_path_resolver(user_id[len("guest_"):])
        if not user_id or user_id in ("public", "guest", "public_guest") or user_id.startswith("guest_"):
            raise ValueError("Guest kernels need a private guest workspace")
        if project_id:
            path = os.path.join(self.workspaces_root, f"user_{user_id}", f"project_{project_id}")
        else:
            path = os.path.join(self.workspaces_root, f"user_{user_id}", "default")
        os.makedirs(path, exist_ok=True)
        self._seed_default_workspace(path)
        return path

    def _seed_default_workspace(self, path: str):
        """Seeds initial tutorial and sample files if workspace is completely empty."""
        try:
            if os.path.exists(path) and len(os.listdir(path)) == 0:
                # 1. README.md
                readme_path = os.path.join(path, "README.md")
                with open(readme_path, "w", encoding="utf-8", newline="") as f:
                    f.write("# Enterprise Python Cloud Studio\n\nWelcome to your cloud workspace!\n\n- Double-click any file in the left sidebar to preview and edit in the right panel.\n- Double-click `.ipynb` files to open as interactive notebooks.\n- Run Python code using the Run button or Shift+Enter.\n")

                # 2. main.py
                main_py_path = os.path.join(path, "main.py")
                with open(main_py_path, "w", encoding="utf-8", newline="") as f:
                    f.write("# Quickstart Python Script\nimport sys\nimport math\n\ndef summary(nums):\n    return {'count': len(nums), 'sum': sum(nums), 'avg': sum(nums)/len(nums)}\n\nif __name__ == '__main__':\n    print('Python version:', sys.version.split()[0])\n    print('Sample calculation:', summary([10, 20, 30, 40, 50]))\n")

                # 3. sample_data.csv
                csv_path = os.path.join(path, "sample_data.csv")
                with open(csv_path, "w", encoding="utf-8", newline="") as f:
                    f.write("id,name,department,salary\n1,Alice,Engineering,105000\n2,Bob,Data Science,115000\n3,Charlie,Product,95000\n4,Diana,Design,90000\n")

                # 4. Getting_Started.ipynb
                import json
                nb_path = os.path.join(path, "Getting_Started.ipynb")
                nb_content = {
                    "cells": [
                        {
                            "cell_type": "markdown",
                            "metadata": {},
                            "source": ["# Welcome to Python Cloud Studio\n", "Interactive notebook environment with real ipykernel backend."]
                        },
                        {
                            "cell_type": "code",
                            "execution_count": None,
                            "metadata": {},
                            "outputs": [],
                            "source": ["import numpy as np\n", "import pandas as pd\n\n", "df = pd.read_csv('sample_data.csv')\n", "print(df.head())"]
                        }
                    ],
                    "metadata": {
                        "kernelspec": {
                            "display_name": "Python 3",
                            "language": "python",
                            "name": "python3"
                        },
                        "language_info": {
                            "name": "python",
                            "version": "3.14.0"
                        }
                    },
                    "nbformat": 4,
                    "nbformat_minor": 5
                }
                with open(nb_path, "w", encoding="utf-8", newline="") as f:
                    json.dump(nb_content, f, indent=2)
        except Exception:
            pass

    async def get_or_create_session(
        self,
        session_id: str,
        user_id: str,
        project_id: Optional[str] = None,
        kernel_name: str = "python3",
        is_admin: bool = False
    ) -> KernelSession:
        """Retrieves an existing session or provisions a new isolated kernel within the quotas."""
        evicted: List[KernelSession] = []
        async with self._lock:
            # Resolve actual session key: if session_id is already held by another user (including another
            # guest) and caller is not admin, namespace the session so every user gets their own kernel process.
            effective_id = session_id
            if effective_id in self._sessions:
                existing = self._sessions[effective_id]
                if existing.user_id != user_id and not is_admin:
                    effective_id = f"{session_id}::{user_id}"

            if effective_id in self._sessions:
                session = self._sessions[effective_id]
            else:
                evicted = self._make_room_locked(user_id)
                workspace = self.get_user_workspace_path(user_id, project_id)
                session = KernelSession(
                    session_id=effective_id,
                    user_id=user_id,
                    workspace_dir=workspace,
                    kernel_name=kernel_name,
                    is_admin=is_admin
                )
                if self._warm and not is_admin:
                    session.warm_candidate = self._warm.pop(0)
                    asyncio.create_task(self.fill_warm_pool(delay=self.warm_refill_delay_seconds))
                self._sessions[effective_id] = session

        await self._shutdown_quietly(evicted)

        if not session.is_running:
            try:
                await session.start()
            except Exception:
                # A kernel that failed to start must not keep counting against the quotas
                async with self._lock:
                    if self._sessions.get(session.session_id) is session:
                        del self._sessions[session.session_id]
                await self._shutdown_quietly([session])
                raise
        return session

    async def fill_warm_pool(self, delay: float = 0.0) -> None:
        """Keeps `warm_pool_size` spare kernels started, with common libraries already imported."""
        if delay:
            await asyncio.sleep(delay)
        if self._warm_filling or self.warm_pool_size <= 0:
            return
        self._warm_filling = True
        try:
            while len(self._warm) < self.warm_pool_size and len(self._sessions) + len(self._warm) < self.max_total_kernels:
                warm_dir = os.path.join(self.workspaces_root, ".warm", uuid.uuid4().hex)
                warm = KernelSession(session_id=f"warm-{uuid.uuid4().hex[:8]}", user_id="warm", workspace_dir=warm_dir)
                try:
                    await warm.start()
                    # Low CPU priority while spare: starting and preloading it never slows down
                    # the code people are running (normal priority is restored when it is taken)
                    await asyncio.to_thread(warm.set_cpu_priority, True)
                    if self.preload_modules:
                        await warm.preload(self.preload_modules)
                except Exception:
                    logger.exception("Could not start a spare kernel")
                    await self._shutdown_quietly([warm])
                    shutil.rmtree(warm_dir, ignore_errors=True)
                    return
                self._warm.append(warm)
        finally:
            self._warm_filling = False

    def _make_room_locked(self, user_id: str) -> List[KernelSession]:
        """
        Checks the per-user, guest and server-wide quotas for one more kernel (caller holds the lock).
        Abandoned kernels (no browser attached, not executing) are evicted oldest-first to make room.
        Returns the evicted sessions, already unregistered, for the caller to shut down outside the lock.
        Raises KernelCapacityError if there is still no room.
        """
        guest = is_guest_user_id(user_id)
        quotas: List[tuple] = [
            (
                lambda s: s.user_id == user_id,
                self.max_kernels_per_user,
                f"You already have {self.max_kernels_per_user} active Python kernels. "
                "Close notebooks you are not using, or restart an existing kernel.",
            ),
            (
                lambda s: True,
                self.max_total_kernels,
                "The server is at full capacity right now. Please try again in a few minutes.",
            ),
        ]
        if guest:
            quotas.insert(1, (
                lambda s: is_guest_user_id(s.user_id),
                self.max_guest_kernels,
                "All guest kernels are in use right now. Please sign in, or try again in a few minutes.",
            ))

        evicted: List[KernelSession] = []
        for in_scope, limit, message in quotas:
            while sum(1 for s in self._sessions.values() if in_scope(s)) >= limit:
                victim = self._oldest_detached_locked(in_scope)
                if victim is None:
                    raise KernelCapacityError(message)
                del self._sessions[victim.session_id]
                evicted.append(victim)
                logger.info("Evicted abandoned kernel %s (user %s) to make room", victim.session_id, victim.user_id)
        return evicted

    def _oldest_detached_locked(self, in_scope: Callable[[KernelSession], bool]) -> Optional[KernelSession]:
        candidates = [
            s for s in self._sessions.values()
            if in_scope(s) and s.attached_clients == 0 and not s.is_busy
        ]
        return min(candidates, key=lambda s: s.last_active_at, default=None)

    @staticmethod
    async def _shutdown_quietly(sessions: List[KernelSession]) -> None:
        for session in sessions:
            try:
                await session.shutdown()
            except Exception:
                logger.exception("Failed to shut down kernel %s", session.session_id)

    @property
    def sessions(self) -> Dict[str, KernelSession]:
        return self._sessions

    def get_session(self, session_id: str, user_id: Optional[str] = None) -> Optional[KernelSession]:
        """
        Looks up a session. With user_id, only a session owned by that user (or its per-user
        namespaced variant) is returned; without user_id (admin/internal use) any session is returned.
        """
        sess = self._sessions.get(session_id)
        if user_id is None:
            return sess
        if sess is not None and sess.user_id == user_id:
            return sess
        return self._sessions.get(f"{session_id}::{user_id}")

    async def restart_session(self, session_id: str, user_id: Optional[str] = None) -> bool:
        """Restarts a running kernel session, clearing its memory."""
        session = self.get_session(session_id, user_id)
        if session:
            await session.restart()
            return True
        return False

    async def shutdown_session(self, session_id: str, user_id: Optional[str] = None) -> bool:
        """Halts and unregisters a kernel session (only the caller's own session when user_id is given)."""
        async with self._lock:
            session = self.get_session(session_id, user_id)
            if session is None:
                return False
            del self._sessions[session.session_id]
        await self._shutdown_quietly([session])
        return True

    async def shutdown_warm_pool(self) -> None:
        warm, self._warm = self._warm, []
        await self._shutdown_quietly(warm)
        for s in warm:
            shutil.rmtree(s.workspace_dir, ignore_errors=True)

    async def shutdown_all(self) -> None:
        """Halts all active kernels (used during server shutdown)."""
        async with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        await self._shutdown_quietly(sessions)
        await self.shutdown_warm_pool()

    async def reap_idle_sessions(self, now: Optional[float] = None) -> List[str]:
        """
        Shuts down kernels that are no longer worth keeping:
          - dead kernels (process gone) with no browser attached,
          - kernels with no browser attached for detached_timeout_seconds (tab closed, notebook switched),
          - kernels that have not executed anything for idle_timeout_seconds.
        Kernels that are currently executing are never reaped.
        """
        now = time.time() if now is None else now
        async with self._lock:
            to_remove = []
            for s_id, s in self._sessions.items():
                if s.is_busy:
                    continue
                last_used = max(s.last_active_at, s.detached_at or 0)
                abandoned = s.attached_clients == 0 and now - last_used > self.detached_timeout_seconds
                dead = s.attached_clients == 0 and not s.is_running
                if abandoned or dead or now - s.last_active_at > self.idle_timeout_seconds:
                    to_remove.append(s_id)
            removed = [self._sessions.pop(s_id) for s_id in to_remove]
        await self._shutdown_quietly(removed)
        if removed:
            logger.info("Reaped %d idle kernel(s): %s", len(removed), ", ".join(to_remove))
        return to_remove

    async def enforce_memory_limits(self) -> List[str]:
        """Kills kernels whose process tree uses more than max_kernel_memory_mb, so one user cannot starve the host."""
        if not self.max_kernel_memory_mb:
            return []
        limit_bytes = self.max_kernel_memory_mb * 1024 * 1024
        killed: List[str] = []
        for s_id, s in list(self._sessions.items()):
            # psutil walks each process tree: in a thread, so the shared event loop never stalls
            usage = await asyncio.to_thread(s.memory_usage_bytes)
            if usage is not None and usage > limit_bytes:
                await s.kill(
                    f"The Python kernel was stopped because it used {usage // (1024 * 1024)} MB of memory, "
                    f"above the {self.max_kernel_memory_mb} MB limit per kernel. It will restart on the next run; "
                    "variables were lost."
                )
                killed.append(s_id)
                logger.warning("Killed kernel %s (user %s) for using %d MB", s_id, s.user_id, usage // (1024 * 1024))
        return killed

    def stats(self) -> Dict[str, int]:
        sessions = list(self._sessions.values())
        return {
            "active_kernels": len(sessions),
            "guest_kernels": sum(1 for s in sessions if is_guest_user_id(s.user_id)),
            "busy_kernels": sum(1 for s in sessions if s.is_busy),
            "detached_kernels": sum(1 for s in sessions if s.attached_clients == 0),
            "max_total_kernels": self.max_total_kernels,
            "max_guest_kernels": self.max_guest_kernels,
        }

    async def run_maintenance(self, interval_seconds: float = 30.0) -> None:
        """Background loop: reap idle/abandoned kernels and enforce the per-kernel memory limit."""
        while True:
            await asyncio.sleep(interval_seconds)
            try:
                await self.reap_idle_sessions()
                await self.enforce_memory_limits()
                for hook in self.maintenance_hooks:
                    hook()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Kernel maintenance pass failed")
