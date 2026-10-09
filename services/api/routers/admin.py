import os
import re
import shutil
import asyncio
import subprocess
import importlib.metadata
import psutil
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User, Notebook, Project, Classroom, AuditLog
from ..auth import (
    hash_password,
    verify_password,
    require_super_admin,
    require_admin_or_super_admin,
    get_current_user,
)
from ..schemas import (
    UserResponse,
    AdminUserCreate,
    AdminUserUpdate,
    AdminPasswordReset,
    AdminProfileUpdate,
    PackageInstallRequest,
    PackageUninstallRequest,
    ClearRuntimesRequest,
    AdminDeleteFileRequest,
)
from ..config import settings
from ..kernel_bridge import kernel_pool

router = APIRouter(prefix="/admin", tags=["Super Admin"])

# Protected baseline packages that must never be uninstalled
PROTECTED_PACKAGES = {
    "numpy",
    "pandas",
    "matplotlib",
    "seaborn",
    "scipy",
    "scikit-learn",
    "sklearn",
    "statsmodels",
    "openpyxl",
    "xlsxwriter",
    "pyarrow",
    "pillow",
    "requests",
    "plotly",
    "ipykernel",
    "ipython",
    "ipywidgets",
    "ipympl",
    "fastapi",
    "uvicorn",
    "sqlalchemy",
    "pydantic",
    "jupyter-client",
    "jupyter_client",
}

SAFE_PKG_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.\=\<\>\~\!\@\,]+$")


async def log_admin_action(
    db: AsyncSession,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
):
    """Utility to record administrative actions in the audit log."""
    try:
        import json
        audit = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details_json=json.dumps(details or {}),
        )
        db.add(audit)
        await db.commit()
    except Exception as e:
        print(f"Failed to record audit log: {e}")


# ========================================================
# 1. DASHBOARD OVERVIEW & STATS
# ========================================================
@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves high-level platform statistics for the Admin Dashboard."""
    total_users = (await db.execute(select(func.count(User.id)))).scalar_one() or 0
    active_users = (await db.execute(select(func.count(User.id)).where(User.is_active == True))).scalar_one() or 0
    total_notebooks = (await db.execute(select(func.count(Notebook.id)))).scalar_one() or 0
    total_classrooms = (await db.execute(select(func.count(Classroom.id)))).scalar_one() or 0

    role_counts_res = await db.execute(select(User.role, func.count(User.id)).group_by(User.role))
    role_distribution = {role: count for role, count in role_counts_res.fetchall()}

    # Runtime information
    active_kernels_count = len(kernel_pool.sessions)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(os.path.abspath(settings.WORKSPACES_ROOT) if os.path.exists(settings.WORKSPACES_ROOT) else ".")

    mem_used_gb = round((mem.total - mem.available) / (1024 * 1024 * 1024), 2)
    mem_total_gb = round(mem.total / (1024 * 1024 * 1024), 2)
    mem_avail_gb = round(mem.available / (1024 * 1024 * 1024), 2)

    disk_used_gb = round((disk.total - disk.free) / (1024 * 1024 * 1024), 2)
    disk_total_gb = round(disk.total / (1024 * 1024 * 1024), 2)
    disk_free_gb = round(disk.free / (1024 * 1024 * 1024), 2)

    return {
        # Flat properties expected by web dashboard AdminStats interface
        "total_users": total_users,
        "active_users": active_users,
        "total_notebooks": total_notebooks,
        "total_projects": 0,
        "active_kernels": active_kernels_count,
        "system_memory": {
            "total_gb": mem_total_gb,
            "used_gb": mem_used_gb,
            "available_gb": mem_avail_gb,
            "percent": round(mem.percent, 1),
        },
        "disk_usage": {
            "total_gb": disk_total_gb,
            "used_gb": disk_used_gb,
            "free_gb": disk_free_gb,
            "percent": round(getattr(disk, "percent", 0.0), 1),
        },
        # Legacy/nested properties preserved for API backwards compatibility & integration tests
        "users": {
            "total": total_users,
            "active": active_users,
            "roles": role_distribution,
        },
        "content": {
            "total_notebooks": total_notebooks,
            "total_classrooms": total_classrooms,
        },
        "runtimes": {
            "active_kernels": active_kernels_count,
            "max_per_user": settings.MAX_CONCURRENT_KERNELS_PER_USER,
        },
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_percent": mem.percent,
            "memory_used_mb": round((mem.total - mem.available) / (1024 * 1024), 1),
            "memory_total_mb": round(mem.total / (1024 * 1024), 1),
            "disk_free_gb": disk_free_gb,
            "disk_total_gb": disk_total_gb,
        },
    }


# ========================================================
# 2. USER MANAGEMENT
# ========================================================
@router.get("/users", response_model=List[UserResponse])
async def list_users(
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    current_user: User = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lists all registered platform users with search and role filters."""
    query = select(User)
    if search:
        query = query.where(
            (User.email.ilike(f"%{search}%")) | (User.full_name.ilike(f"%{search}%"))
        )
    if role:
        query = query.where(User.role == role)

    query = query.order_by(desc(User.created_at)).offset(skip).limit(limit)
    res = await db.execute(query)
    return res.scalars().all()


@router.post("/users", response_model=UserResponse)
async def create_user(
    req: AdminUserCreate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Super Admin creates a new user with designated role and package permission."""
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    allowed_roles = ["super_admin", "admin", "instructor", "student"]
    role = req.role if req.role in allowed_roles else "student"

    new_user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role=role,
        can_manage_packages=req.can_manage_packages or (role in ("super_admin", "admin")),
        organization_id=req.organization_id,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    await log_admin_action(
        db,
        current_user.id,
        "CREATE_USER",
        "user",
        new_user.id,
        {"email": new_user.email, "role": new_user.role, "can_manage_packages": new_user.can_manage_packages},
    )
    return new_user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    req: AdminUserUpdate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Super Admin updates user details, role, status, or package installation permissions."""
    res = await db.execute(select(User).where(User.id == user_id))
    target_user = res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent demoting the last active super_admin
    if target_user.id == current_user.id and req.role and req.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot demote yourself from Super Admin")

    if req.email is not None and req.email != target_user.email:
        existing = await db.execute(select(User).where(User.email == req.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already taken")
        target_user.email = req.email

    if req.full_name is not None:
        target_user.full_name = req.full_name
    if req.role is not None:
        target_user.role = req.role
        if req.role in ("super_admin", "admin"):
            target_user.can_manage_packages = True
    if req.is_active is not None:
        target_user.is_active = req.is_active
    if req.can_manage_packages is not None:
        target_user.can_manage_packages = req.can_manage_packages

    target_user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(target_user)

    await log_admin_action(
        db,
        current_user.id,
        "UPDATE_USER",
        "user",
        target_user.id,
        {"email": target_user.email, "role": target_user.role, "can_manage_packages": target_user.can_manage_packages},
    )
    return target_user


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    req: AdminPasswordReset,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Super Admin resets a user's password."""
    res = await db.execute(select(User).where(User.id == user_id))
    target_user = res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    target_user.hashed_password = hash_password(req.new_password)
    target_user.updated_at = datetime.utcnow()
    await db.commit()

    await log_admin_action(
        db,
        current_user.id,
        "RESET_PASSWORD",
        "user",
        target_user.id,
        {"email": target_user.email},
    )
    return {"status": "ok", "message": f"Password for {target_user.email} successfully reset."}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Super Admin deletes a user account (or deactivates if cannot hard-delete)."""
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account.")

    res = await db.execute(select(User).where(User.id == user_id))
    target_user = res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    email = target_user.email
    await db.delete(target_user)
    await db.commit()

    await log_admin_action(
        db,
        current_user.id,
        "DELETE_USER",
        "user",
        user_id,
        {"email": email},
    )
    return {"status": "ok", "message": f"User {email} deleted successfully."}


# ========================================================
# 3. ROLES AND PERMISSIONS MATRIX
# ========================================================
@router.get("/roles")
async def get_roles_matrix(current_user: User = Depends(require_admin_or_super_admin)):
    """Returns the system roles and their permission matrix."""
    return [
        {
            "role": "super_admin",
            "name": "Super Administrator",
            "description": "Full unconstrained administrative privileges across all workspaces, users, packages, runtimes, and platform settings.",
            "permissions": [
                "all:access",
                "admin:manage_users",
                "admin:manage_packages",
                "admin:manage_runtimes",
                "admin:global_files",
                "admin:audit_logs",
            ],
        },
        {
            "role": "admin",
            "name": "Administrator",
            "description": "Can view system status, manage students and instructors, and monitor runtimes.",
            "permissions": [
                "admin:view_users",
                "admin:manage_packages",
                "admin:view_runtimes",
                "classrooms:manage",
            ],
        },
        {
            "role": "instructor",
            "name": "Instructor",
            "description": "Can create classrooms, distribute assignments, review submissions, and manage notebooks.",
            "permissions": [
                "classrooms:create",
                "assignments:create",
                "submissions:grade",
                "notebooks:create",
            ],
        },
        {
            "role": "student",
            "name": "Student",
            "description": "Can create private notebooks, join classrooms, submit assignments, and run code.",
            "permissions": [
                "notebooks:create",
                "classrooms:join",
                "submissions:create",
            ],
        },
    ]


# ========================================================
# 4. PYTHON PACKAGE MANAGEMENT
# ========================================================
@router.get("/packages")
async def list_packages(
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_admin_or_super_admin),
):
    """Lists installed Python packages and versions, marking baseline packages as protected."""
    packages = []
    seen = set()
    for dist in importlib.metadata.distributions():
        name = dist.metadata["Name"]
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        version = dist.version
        is_protected = name.lower() in PROTECTED_PACKAGES

        if search:
            if search.lower() not in name.lower():
                continue

        packages.append({
            "name": name,
            "version": version,
            "is_protected": is_protected,
            "environment": "Default Python Runtime",
        })

    packages.sort(key=lambda x: (not x["is_protected"], x["name"].lower()))
    return packages


@router.post("/packages/install")
async def install_package(
    req: PackageInstallRequest,
    current_user: User = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Installs or upgrades a Python package in the shared runtime environment."""
    pkg = req.package_name.strip()
    if not SAFE_PKG_REGEX.match(pkg):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid package name. Characters must match standard package naming.",
        )

    spec = pkg
    if req.version:
        v = req.version.strip()
        if not re.match(r"^[a-zA-Z0-9_\-\.\=\<\>\~]+$", v):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid version specifier.")
        spec = f"{pkg}=={v}" if not v.startswith(("=", "<", ">", "~")) else f"{pkg}{v}"

    try:
        proc = subprocess.run(
            ["python", "-m", "pip", "install", "--no-input", spec],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            return {
                "status": "error",
                "message": f"Installation failed: {proc.stderr or proc.stdout}",
            }

        await log_admin_action(
            db,
            current_user.id,
            "INSTALL_PACKAGE",
            "package",
            pkg,
            {"spec": spec, "output": proc.stdout[-500:] if proc.stdout else ""},
        )
        return {
            "status": "ok",
            "message": f"Package '{spec}' successfully installed.",
            "output": proc.stdout[-1000:],
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Package installation timed out.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/packages/uninstall")
async def uninstall_package(
    req: PackageUninstallRequest,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Uninstalls an optional Python package (protects baseline packages)."""
    pkg = req.package_name.strip().lower()
    if pkg in PROTECTED_PACKAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot uninstall '{pkg}': It is a protected core runtime baseline package required by notebooks.",
        )

    if not SAFE_PKG_REGEX.match(pkg):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid package name.")

    try:
        proc = subprocess.run(
            ["python", "-m", "pip", "uninstall", "-y", pkg],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            return {
                "status": "error",
                "message": f"Uninstall failed: {proc.stderr or proc.stdout}",
            }

        await log_admin_action(
            db,
            current_user.id,
            "UNINSTALL_PACKAGE",
            "package",
            pkg,
            {"output": proc.stdout[-300:] if proc.stdout else ""},
        )
        return {
            "status": "ok",
            "message": f"Package '{pkg}' successfully uninstalled.",
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ========================================================
# 5. RUNTIME & MEMORY MANAGEMENT
# ========================================================
@router.get("/runtimes")
async def list_active_runtimes(current_user: User = Depends(require_admin_or_super_admin)):
    """Lists currently active Python kernel sessions and their memory footprint."""
    import time
    active_list = []
    for s_id, session in list(kernel_pool.sessions.items()):
        mem_mb = 0.0
        pid = None
        try:
            km = getattr(session, "km", None) or getattr(session, "kernel_manager", None)
            if km and hasattr(km, "kernel") and km.kernel:
                pid = getattr(km.kernel, "pid", None)
            elif km and hasattr(km, "has_kernel") and km.has_kernel:
                pid = getattr(km, "pid", None)
            if pid:
                p = psutil.Process(pid)
                mem_mb = round(p.memory_info().rss / (1024 * 1024), 2)
        except Exception:
            pass

        last_active = getattr(session, "last_active_at", None) or getattr(session, "created_at", time.time())
        idle_seconds = max(0.0, round(time.time() - last_active, 1))

        active_list.append({
            "session_id": s_id,
            "user_id": session.user_id,
            "user_email": session.user_id,
            "is_running": session.is_running,
            "execution_count": session.execution_count,
            "pid": pid,
            "memory_mb": mem_mb,
            "cpu_percent": 0.0,
            "idle_seconds": idle_seconds,
            "workspace_dir": getattr(session, "workspace_dir", ""),
            "kernel_name": session.kernel_name,
        })
    return active_list


@router.post("/runtimes/{session_id}/clear")
async def clear_specific_runtime(
    session_id: str,
    current_user: User = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Restarts a specific active kernel to release its memory and runtime resources."""
    session = kernel_pool.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or already terminated.")

    user_id = session.user_id
    await kernel_pool.restart_session(session_id)

    await log_admin_action(
        db,
        current_user.id,
        "CLEAR_RUNTIME_MEMORY",
        "runtime_session",
        session_id,
        {"affected_user": user_id},
    )
    return {"status": "ok", "message": f"Runtime session '{session_id}' cleared and restarted."}


@router.post("/runtimes/clear")
async def clear_runtimes_unified(
    req: Dict[str, Any],
    current_user: User = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Unified endpoint to clear a single runtime or all runtimes."""
    session_id = req.get("session_id")
    clear_all = req.get("clear_all", False)
    if clear_all:
        count = len(kernel_pool.sessions)
        for s_id in list(kernel_pool.sessions.keys()):
            try:
                await kernel_pool.restart_session(s_id)
            except Exception:
                pass
        await log_admin_action(
            db,
            current_user.id,
            "CLEAR_ALL_RUNTIMES",
            "system_runtimes",
            None,
            {"cleared_sessions_count": count},
        )
        return {"status": "ok", "message": f"Successfully cleared all {count} active runtime kernels."}
    elif session_id:
        session = kernel_pool.sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        await kernel_pool.restart_session(session_id)
        return {"status": "ok", "message": f"Runtime session '{session_id}' cleared and restarted."}
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="session_id or clear_all=True required.")


@router.post("/runtimes/clear-all")
async def clear_all_runtimes(
    req: ClearRuntimesRequest,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Super Admin explicitly restarts all active Python kernels to release memory system-wide."""
    if not req.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required: clearing all active runtimes will interrupt active user computations.",
        )

    count = len(kernel_pool.sessions)
    for s_id in list(kernel_pool.sessions.keys()):
        try:
            await kernel_pool.restart_session(s_id)
        except Exception:
            pass

    await log_admin_action(
        db,
        current_user.id,
        "CLEAR_ALL_RUNTIMES",
        "system_runtimes",
        None,
        {"cleared_sessions_count": count},
    )
    return {"status": "ok", "message": f"Successfully cleared all {count} active runtime kernels."}


@router.post("/runtimes/clear-cache")
async def clear_system_caches(
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Clears safe temporary application caches without deleting persistent user data."""
    cleaned_items = 0
    workspaces_root = os.path.abspath(settings.WORKSPACES_ROOT)
    if os.path.exists(workspaces_root):
        for root, dirs, files in os.walk(workspaces_root):
            for d in list(dirs):
                if d in ("__pycache__", ".pytest_cache", ".ipynb_checkpoints"):
                    try:
                        shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                        cleaned_items += 1
                    except Exception:
                        pass

    await log_admin_action(
        db,
        current_user.id,
        "CLEAR_SYSTEM_CACHE",
        "cache",
        None,
        {"cleaned_directories": cleaned_items},
    )
    return {"status": "ok", "message": f"Cleaned {cleaned_items} temporary cache directories."}


# ========================================================
# 6. WORKSPACE & GLOBAL FILE MANAGEMENT
# ========================================================
@router.get("/workspaces")
async def list_all_workspaces(current_user: User = Depends(require_admin_or_super_admin)):
    """Lists all user and public workspaces, file counts, and metadata."""
    workspaces = []
    root = os.path.abspath(settings.WORKSPACES_ROOT)
    if os.path.exists(root):
        for entry in os.scandir(root):
            if entry.is_dir():
                ws_name = entry.name
                files_list = []
                total_size = 0
                for froot, _, fnames in os.walk(entry.path):
                    for fn in fnames:
                        fp = os.path.join(froot, fn)
                        try:
                            st = os.stat(fp)
                            rel = os.path.relpath(fp, entry.path).replace("\\", "/")
                            total_size += st.st_size
                            files_list.append({
                                "name": fn,
                                "path": rel,
                                "size": st.st_size,
                                "modified_at": st.st_mtime,
                            })
                        except Exception:
                            pass

                owner_label = "Public Workspace" if ws_name == "public" else ws_name.replace("user_", "User ")
                workspaces.append({
                    "id": ws_name,
                    "target": ws_name,
                    "name": owner_label,
                    "owner": owner_label,
                    "type": "public" if ws_name == "public" else "user",
                    "is_public": ws_name == "public",
                    "path": entry.path.replace("\\", "/"),
                    "item_count": len(files_list),
                    "file_count": len(files_list),
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "total_size_kb": round(total_size / 1024, 2),
                    "files": files_list[:100],
                })
    return workspaces


@router.post("/workspaces/delete-file")
async def admin_delete_workspace_file_post(
    req: Dict[str, Any],
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Deletes a file across workspaces via POST /admin/workspaces/delete-file."""
    target_path = req.get("target_path") or req.get("path")
    if not target_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_path required.")

    ws_root = os.path.abspath(settings.WORKSPACES_ROOT)
    full_path = None
    direct_try = os.path.realpath(os.path.join(ws_root, target_path.lstrip("/\\")))
    if direct_try.startswith(ws_root) and os.path.exists(direct_try):
        full_path = direct_try
    else:
        for root, _, files in os.walk(ws_root):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), ws_root).replace("\\", "/")
                if rel.endswith(target_path.replace("\\", "/")) or f == target_path:
                    full_path = os.path.join(root, f)
                    break
            if full_path:
                break

    if not full_path or not os.path.exists(full_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target file not found.")

    is_dir = os.path.isdir(full_path)
    if is_dir:
        shutil.rmtree(full_path, ignore_errors=True)
    else:
        os.remove(full_path)

    await log_admin_action(
        db,
        current_user.id,
        "GLOBAL_FILE_DELETE",
        "file_or_folder",
        target_path,
        {"resolved_path": full_path, "is_directory": is_dir},
    )
    return {"status": "ok", "message": f"Successfully deleted '{target_path}'."}


@router.delete("/files")
async def admin_delete_file(
    req: AdminDeleteFileRequest,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Super Admin deletes any file or folder across public or private workspaces."""
    if not req.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Explicit confirmation required.")

    ws_root = os.path.abspath(settings.WORKSPACES_ROOT)
    target_dir = os.path.realpath(os.path.join(ws_root, req.workspace_target))
    if not (target_dir == ws_root or target_dir.startswith(ws_root + os.sep)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access outside workspaces forbidden.")

    target_path = os.path.realpath(os.path.join(target_dir, req.path.lstrip("/\\")))
    if not (target_path == target_dir or target_path.startswith(target_dir + os.sep)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Path traversal attempt blocked.")

    if not os.path.exists(target_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target file or directory does not exist.")

    is_dir = os.path.isdir(target_path)
    if is_dir:
        shutil.rmtree(target_path, ignore_errors=True)
    else:
        os.remove(target_path)

    await log_admin_action(
        db,
        current_user.id,
        "GLOBAL_FILE_DELETE",
        "file_or_folder",
        req.path,
        {"workspace": req.workspace_target, "is_directory": is_dir},
    )
    return {"status": "ok", "message": f"Successfully deleted {'folder' if is_dir else 'file'} '{req.path}'."}


# ========================================================
# 7. AUDIT LOGS
# ========================================================
@router.get("/audit-logs")
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    current_user: User = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lists recorded administrative audit log entries."""
    import json
    res = await db.execute(
        select(AuditLog).order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
    )
    logs = res.scalars().all()
    formatted = []
    for log in logs:
        details = {}
        if log.details_json:
            try:
                details = json.loads(log.details_json) if isinstance(log.details_json, str) else log.details_json
            except Exception:
                details = {"raw": log.details_json}
        formatted.append({
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "timestamp": log.created_at.isoformat() if log.created_at else "",
            "created_at": log.created_at.isoformat() if log.created_at else "",
            "details": details,
            "details_json": log.details_json,
        })
    return formatted


# ========================================================
# 8. ADMIN SETTINGS & CREDENTIALS UPDATE
# ========================================================
@router.put("/profile", response_model=UserResponse)
@router.put("/settings/profile", response_model=UserResponse)
async def update_super_admin_credentials(
    req: AdminProfileUpdate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Super Admin updates their administrative email, name, or password.
    Updates the database permanently, which remains authoritative across restarts.
    """
    if req.new_password:
        if not req.current_password or not verify_password(req.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password verification failed.",
            )
        current_user.hashed_password = hash_password(req.new_password)

    if req.email and req.email != current_user.email:
        existing = await db.execute(select(User).where(User.email == req.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already taken")
        current_user.email = req.email

    if req.full_name:
        current_user.full_name = req.full_name

    current_user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(current_user)

    await log_admin_action(
        db,
        current_user.id,
        "UPDATE_SUPER_ADMIN_SETTINGS",
        "super_admin_account",
        current_user.id,
        {"email": current_user.email},
    )
    return current_user
