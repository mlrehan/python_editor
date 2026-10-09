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

    def get_public_workspace_path(self) -> str:
        """Computes shared public workspace directory path for unauthenticated guest users."""
        path = os.path.join(self.workspaces_root, "public")
        os.makedirs(path, exist_ok=True)
        self._seed_default_workspace(path)
        return path

    def get_user_workspace_path(self, user_id: str, project_id: Optional[str] = None) -> str:
        """Computes isolated canonical workspace directory path for a user/project."""
        if not user_id or user_id in ("public", "guest", "public_guest") or user_id.startswith("guest_"):
            return self.get_public_workspace_path()
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

    @property
    def sessions(self) -> Dict[str, KernelSession]:
        return self._sessions

    def get_session(self, session_id: str) -> Optional[KernelSession]:
        return self._sessions.get(session_id)

    async def restart_session(self, session_id: str) -> bool:
        """Restarts a running kernel session, clearing its memory."""
        session = self._sessions.get(session_id)
        if session:
            await session.restart()
            return True
        return False

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
