import asyncio
import time
import os
from typing import Dict, List, Optional
from .kernel_session import KernelSession


class KernelPoolManager:
    """
    Manages multi-tenant kernel instances.
    Enforces user quotas, idle timeouts, and workspace directory routing.
    """
    def __init__(
        self,
        workspaces_root: str = "./storage/workspaces",
        max_kernels_per_user: int = 5,
        idle_timeout_seconds: int = 3600
    ):
        self.workspaces_root = os.path.abspath(workspaces_root)
        self.max_kernels_per_user = max_kernels_per_user
        self.idle_timeout_seconds = idle_timeout_seconds
        self._sessions: Dict[str, KernelSession] = {}
        self._lock = asyncio.Lock()
        os.makedirs(self.workspaces_root, exist_ok=True)

    def get_user_workspace_path(self, user_id: str, project_id: Optional[str] = None) -> str:
        """Computes isolated canonical workspace directory path for a user/project."""
        if project_id:
            path = os.path.join(self.workspaces_root, f"user_{user_id}", f"project_{project_id}")
        else:
            path = os.path.join(self.workspaces_root, f"user_{user_id}", "default")
        os.makedirs(path, exist_ok=True)
        return path

    async def get_or_create_session(
        self,
        session_id: str,
        user_id: str,
        project_id: Optional[str] = None,
        kernel_name: str = "python3"
    ) -> KernelSession:
        """Retrieves an existing session or provisions a new isolated kernel."""
        async with self._lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                if session.user_id != user_id:
                    raise PermissionError("Access to this kernel session is forbidden for this user.")
                if not session.is_running:
                    await session.start()
                return session

            # Check user concurrency limit
            user_sessions = [s for s in self._sessions.values() if s.user_id == user_id]
            if len(user_sessions) >= self.max_kernels_per_user:
                raise ValueError(
                    f"User quota exceeded: Maximum {self.max_kernels_per_user} concurrent kernels reached."
                )

            workspace = self.get_user_workspace_path(user_id, project_id)
            session = KernelSession(
                session_id=session_id,
                user_id=user_id,
                workspace_dir=workspace,
                kernel_name=kernel_name
            )
            await session.start()
            self._sessions[session_id] = session
            return session

    def get_session(self, session_id: str) -> Optional[KernelSession]:
        return self._sessions.get(session_id)

    async def shutdown_session(self, session_id: str) -> bool:
        """Halts and unregisters a kernel session."""
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                await session.shutdown()
                return True
            return False

    async def shutdown_all(self) -> None:
        """Halts all active kernels (used during server shutdown)."""
        async with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
            for session in sessions:
                try:
                    await session.shutdown()
                except Exception:
                    pass

    async def reap_idle_sessions(self) -> List[str]:
        """Terminates kernels that have been idle longer than idle_timeout_seconds."""
        now = time.time()
        reaped: List[str] = []
        async with self._lock:
            to_remove = []
            for s_id, s in self._sessions.items():
                if now - s.last_active_at > self.idle_timeout_seconds:
                    to_remove.append(s_id)

            for s_id in to_remove:
                session = self._sessions.pop(s_id)
                await session.shutdown()
                reaped.append(s_id)
        return reaped
