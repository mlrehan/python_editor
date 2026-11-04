"""
Guest identities and private guest workspaces.

Every guest receives a server-issued token `gst_<random>.<signature>` (HMAC-SHA256 with SECRET_KEY).
The server accepts only tokens it signed, so a client cannot pick or guess an identity. A valid token
maps to a workspace id (a one-way hash of the token), which names the guest's private folder
`storage/workspaces/guests/<id>` and its kernels (`guest_<id>`). Nothing is shared between guests.

Guest notebooks are kept per guest in `storage/workspaces/guests/<id>.notebooks/` (next to the
workspace, not inside it, so they do not appear in the file explorer), with the same API responses
as registered users' notebooks. The browser keeps its own copy (IndexedDB) and restores a workspace
that the server has cleaned up; `<id>.meta.json` records when such a restore is needed.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import settings

GUEST_TOKEN_PREFIX = "gst_"
_WORKSPACE_ID = re.compile(r"^[0-9a-f]{32}$")
_NOTEBOOK_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _signature(raw: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"pcs-guest:{raw}".encode(), hashlib.sha256).hexdigest()[:32]


def issue_guest_token() -> str:
    raw = secrets.token_urlsafe(24)
    return f"{GUEST_TOKEN_PREFIX}{raw}.{_signature(raw)}"


def guest_workspace_id(token: Optional[str]) -> Optional[str]:
    """The workspace id for a token this server issued, or None (unsigned, forged or malformed)."""
    if not token or not token.startswith(GUEST_TOKEN_PREFIX) or "." not in token:
        return None
    raw, _, sig = token[len(GUEST_TOKEN_PREFIX):].rpartition(".")
    if not raw or not hmac.compare_digest(sig, _signature(raw)):
        return None
    return hashlib.sha256(f"pcs-guest-workspace:{raw}".encode()).hexdigest()[:32]


def is_guest_workspace_id(value: str) -> bool:
    return bool(_WORKSPACE_ID.match(value or ""))


class GuestWorkspaces:
    """Private folders, notebooks and restore state of guests."""

    def __init__(self, workspaces_root: str, template_dir: str):
        self.root = os.path.join(os.path.abspath(workspaces_root), "guests")
        self.template_dir = template_dir
        os.makedirs(self.root, exist_ok=True)

    # --- folders ---------------------------------------------------------------------------------------

    def path(self, workspace_id: str) -> str:
        """The guest's private folder, created (with the starter files) on first use."""
        if not is_guest_workspace_id(workspace_id):
            raise ValueError("Invalid guest workspace id")
        path = os.path.join(self.root, workspace_id)
        if not os.path.isdir(path):
            os.makedirs(path, exist_ok=True)
            self._copy_starter_files(path)
            # A new folder: the browser may hold this guest's earlier work and should restore it
            self._write_meta(workspace_id, {"created_at": time.time(), "restore_pending": True})
        self.touch(workspace_id)
        return path

    def _copy_starter_files(self, path: str) -> None:
        if not os.path.isdir(self.template_dir):
            return
        for name in os.listdir(self.template_dir):
            if name.startswith("."):
                continue
            src = os.path.join(self.template_dir, name)
            try:
                if os.path.isfile(src):
                    shutil.copy2(src, os.path.join(path, name))
            except OSError:
                pass

    def touch(self, workspace_id: str) -> None:
        try:
            os.utime(self._meta_path(workspace_id), None)
        except OSError:
            pass

    # --- restore state -----------------------------------------------------------------------------------

    def _meta_path(self, workspace_id: str) -> str:
        return os.path.join(self.root, f"{workspace_id}.meta.json")

    def _read_meta(self, workspace_id: str) -> Dict[str, Any]:
        try:
            with open(self._meta_path(workspace_id), "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _write_meta(self, workspace_id: str, meta: Dict[str, Any]) -> None:
        with open(self._meta_path(workspace_id), "w", encoding="utf-8") as f:
            json.dump(meta, f)

    def info(self, workspace_id: str) -> Dict[str, Any]:
        self.path(workspace_id)
        meta = self._read_meta(workspace_id)
        return {"restore_pending": bool(meta.get("restore_pending")), "created_at": meta.get("created_at")}

    def mark_restored(self, workspace_id: str) -> None:
        self.path(workspace_id)
        meta = self._read_meta(workspace_id)
        meta["restore_pending"] = False
        self._write_meta(workspace_id, meta)

    # --- notebooks ---------------------------------------------------------------------------------------

    def _notebooks_dir(self, workspace_id: str) -> str:
        self.path(workspace_id)
        d = os.path.join(self.root, f"{workspace_id}.notebooks")
        os.makedirs(d, exist_ok=True)
        return d

    def _notebook_file(self, workspace_id: str, notebook_id: str) -> str:
        if not _NOTEBOOK_ID.match(notebook_id or ""):
            raise ValueError("Invalid notebook id")
        return os.path.join(self._notebooks_dir(workspace_id), f"{notebook_id}.json")

    def list_notebooks(self, workspace_id: str) -> List[Dict[str, Any]]:
        d = self._notebooks_dir(workspace_id)
        items = []
        for name in os.listdir(d):
            if not name.endswith(".json"):
                continue
            nb = self.get_notebook(workspace_id, name[:-5])
            if nb:
                items.append(nb)
        items.sort(key=lambda n: n["updated_at"], reverse=True)
        return items

    def get_notebook(self, workspace_id: str, notebook_id: str) -> Optional[Dict[str, Any]]:
        try:
            with open(self._notebook_file(workspace_id, notebook_id), "r", encoding="utf-8") as f:
                nb = json.load(f)
        except (OSError, ValueError):
            return None
        nb["created_at"] = datetime.fromisoformat(nb["created_at"])
        nb["updated_at"] = datetime.fromisoformat(nb["updated_at"])
        return nb

    def save_notebook(
        self,
        workspace_id: str,
        notebook_id: Optional[str],
        title: str,
        content: Dict[str, Any],
        kernel_name: str = "python3",
    ) -> Dict[str, Any]:
        notebook_id = notebook_id or str(uuid.uuid4())
        existing = self.get_notebook(workspace_id, notebook_id)
        now = datetime.utcnow()
        record = {
            "id": notebook_id,
            "user_id": f"guest_{workspace_id}",
            "project_id": None,
            "title": title,
            "kernel_name": kernel_name,
            "created_at": (existing["created_at"] if existing else now).isoformat(),
            "updated_at": now.isoformat(),
            "content": content,
        }
        path = self._notebook_file(workspace_id, notebook_id)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(record, f)
        os.replace(tmp, path)  # atomic: a crash never leaves a half-written notebook
        return self.get_notebook(workspace_id, notebook_id)

    def delete_notebook(self, workspace_id: str, notebook_id: str) -> bool:
        try:
            os.remove(self._notebook_file(workspace_id, notebook_id))
            return True
        except OSError:
            return False

    # --- cleanup -----------------------------------------------------------------------------------------

    def remove_idle(self, max_idle_seconds: float, active_ids: set) -> List[str]:
        """Deletes guest workspaces unused for `max_idle_seconds` (the browser copy restores them)."""
        removed = []
        now = time.time()
        for name in os.listdir(self.root):
            if not name.endswith(".meta.json"):
                continue
            ws_id = name[: -len(".meta.json")]
            if not is_guest_workspace_id(ws_id) or ws_id in active_ids:
                continue
            try:
                idle = now - os.path.getmtime(os.path.join(self.root, name))
            except OSError:
                continue
            if idle < max_idle_seconds:
                continue
            shutil.rmtree(os.path.join(self.root, ws_id), ignore_errors=True)
            shutil.rmtree(os.path.join(self.root, f"{ws_id}.notebooks"), ignore_errors=True)
            try:
                os.remove(os.path.join(self.root, name))
            except OSError:
                pass
            removed.append(ws_id)
        return removed
