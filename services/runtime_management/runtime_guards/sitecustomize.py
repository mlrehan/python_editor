"""
Runtime Security Guard for Python Cloud Studio
Automatically loaded by Python IPyKernel processes via sitecustomize.py.
Enforces strict workspace isolation and prevents cross-tenant path traversal
into other users' private workspaces at the Python runtime level.
"""

import os
import sys
import builtins
import io

_is_admin = os.environ.get("PYTHON_CLOUD_STUDIO_IS_ADMIN") == "1"
_current_ws = os.environ.get("PYTHON_CLOUD_STUDIO_WORKSPACE")

if not _is_admin and _current_ws:
    _canon_ws = os.path.realpath(_current_ws).rstrip("\\/").replace("\\", "/")

    def _is_cross_workspace_path(path):
        """
        Returns True if the target path resolves to another user's private workspace directory.
        Allows access to:
          - Current user's workspace files
          - Shared public workspace files
          - Standard library, virtualenv, and system packages
        Blocks:
          - Access to /workspaces/user_<other_id>/
        """
        try:
            if not isinstance(path, (str, bytes, os.PathLike)):
                return False
            path_str = os.fspath(path) if hasattr(os, "fspath") else str(path)
            # Fast check
            if "user_" not in path_str and "workspaces" not in path_str:
                return False
            real = os.path.realpath(path_str).rstrip("\\/").replace("\\", "/")
            if "/workspaces/user_" in real:
                if not (real == _canon_ws or real.startswith(_canon_ws + "/")):
                    return True
        except Exception:
            pass
        return False

    _orig_open = builtins.open
    _orig_io_open = io.open

    def _guarded_open(file, *args, **kwargs):
        if _is_cross_workspace_path(file):
            raise PermissionError("Permission Denied: Cross-workspace file access to other users' private directories is prohibited.")
        return _orig_io_open(file, *args, **kwargs)

    builtins.open = _guarded_open
    io.open = _guarded_open

    # Also wrap IPython if already loaded or on import
    try:
        import IPython.core.interactiveshell as _ish
        _ish.io_open = _guarded_open
        _ish._modified_open = _guarded_open
    except Exception:
        pass

    _orig_listdir = os.listdir
    def _guarded_listdir(path=None):
        target = path if path is not None else "."
        if _is_cross_workspace_path(target):
            raise PermissionError("Permission Denied: Cross-workspace access to other users' private directories is prohibited.")
        return _orig_listdir(path) if path is not None else _orig_listdir()
    os.listdir = _guarded_listdir

    _orig_scandir = os.scandir
    def _guarded_scandir(path=None):
        target = path if path is not None else "."
        if _is_cross_workspace_path(target):
            raise PermissionError("Permission Denied: Cross-workspace access to other users' private directories is prohibited.")
        return _orig_scandir(path) if path is not None else _orig_scandir()
    os.scandir = _guarded_scandir

    _orig_stat = os.stat
    def _guarded_stat(path, *args, **kwargs):
        if _is_cross_workspace_path(path):
            raise PermissionError("Permission Denied: Cross-workspace access to other users' private directories is prohibited.")
        return _orig_stat(path, *args, **kwargs)
    os.stat = _guarded_stat

