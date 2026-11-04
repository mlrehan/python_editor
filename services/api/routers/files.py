import os
import shutil
from typing import List, Union
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from ..models import User
from ..schemas import FileItemResponse, FileWriteRequest, FolderCreateRequest, FileRenameRequest, WorkspaceEnvUpdateRequest
from ..auth import get_current_user_or_guest, GuestUser, owner_id_of
from ..kernel_bridge import kernel_pool, guest_workspaces

router = APIRouter(prefix="/files", tags=["Files"])


def get_safe_workspace_root(current_user: Union[User, GuestUser]) -> str:
    """Returns the canonical root directory for this user, or this guest's private workspace."""
    return os.path.realpath(kernel_pool.get_user_workspace_path(owner_id_of(current_user)))


def get_safe_user_path(current_user: Union[User, GuestUser], relative_path: str = "") -> str:
    """
    Resolves and verifies that the target path is strictly contained within the user's workspace.
    Every user and every guest has an isolated private workspace.
    Guarantees protection against path traversal (e.g. '../').
    """
    workspace_root = get_safe_workspace_root(current_user)
    clean_rel = relative_path.lstrip("/\\")
    target_path = os.path.realpath(os.path.join(workspace_root, clean_rel))

    # Path traversal check
    if not (target_path == workspace_root or target_path.startswith(workspace_root + os.sep)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access outside authorized workspace directory is strictly forbidden.",
        )
    return target_path


@router.get("", response_model=List[FileItemResponse])
async def list_files(
    directory: str = Query("", description="Relative directory path"),
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """Lists files and folders inside the user's workspace (public for guests, private for users)."""
    target_dir = get_safe_user_path(current_user, directory)
    if not os.path.exists(target_dir):
        return []

    workspace_root = get_safe_workspace_root(current_user)
    items = []
    for entry in os.scandir(target_dir):
        rel_path = os.path.relpath(entry.path, workspace_root)
        stat = entry.stat()
        items.append(
            FileItemResponse(
                name=entry.name,
                path=rel_path.replace("\\", "/"),
                is_dir=entry.is_dir(),
                size=stat.st_size if entry.is_file() else 0,
                modified_at=stat.st_mtime,
            )
        )
    # Sort folders first, then files alphabetically
    items.sort(key=lambda x: (not x.is_dir, x.name.lower()))
    return items


@router.get("/read")
async def read_file(
    path: str = Query(..., description="Relative file path"),
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """Reads a text or notebook file from the workspace."""
    target_file = get_safe_user_path(current_user, path)
    if not os.path.isfile(target_file):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()
        return {"path": path, "content": content}
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Binary file preview not supported via text endpoint",
        )


@router.post("/write")
async def write_file(
    req: FileWriteRequest,
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """Writes content to a file in the caller's private workspace."""
    target_file = get_safe_user_path(current_user, req.path)
    os.makedirs(os.path.dirname(target_file), exist_ok=True)
    with open(target_file, "w", encoding="utf-8", newline="") as f:
        f.write(req.content)

    return {"status": "ok", "path": req.path}


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    directory: str = Query("", description="Target subdirectory"),
    folder: str = Query("", description="Target subdirectory (alias)"),
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """Uploads a file to the workspace."""
    subpath = folder or directory
    target_dir = get_safe_user_path(current_user, subpath)
    os.makedirs(target_dir, exist_ok=True)
    filename = os.path.basename(file.filename or "upload.dat")
    destination = os.path.join(target_dir, filename)

    workspace_root = get_safe_workspace_root(current_user)
    if not destination.startswith(workspace_root):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid destination path")

    rel_dest = os.path.relpath(destination, workspace_root).replace("\\", "/")

    with open(destination, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "status": "ok",
        "filename": filename,
        "path": rel_dest,
        "size": os.path.getsize(destination),
    }


@router.delete("")
async def delete_file(
    path: str = Query(..., description="Relative path of file or folder to delete"),
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """Deletes a file or directory within the workspace."""

    target_path = get_safe_user_path(current_user, path)
    if not os.path.exists(target_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    if os.path.isdir(target_path):
        shutil.rmtree(target_path)
    else:
        os.remove(target_path)

    return {"status": "ok", "deleted": path}


@router.post("/folder")
async def create_folder(
    req: FolderCreateRequest,
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """Creates a new folder within the workspace."""
    target_dir = get_safe_user_path(current_user, req.path)
    os.makedirs(target_dir, exist_ok=True)
    return {"status": "ok", "path": req.path}


@router.post("/rename")
async def rename_file(
    req: FileRenameRequest,
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """Renames or moves a file or folder within the workspace."""

    old_target = get_safe_user_path(current_user, req.old_path)
    new_target = get_safe_user_path(current_user, req.new_path)

    if not os.path.exists(old_target):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source file not found")

    if os.path.exists(new_target):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Target name already exists")

    os.makedirs(os.path.dirname(new_target), exist_ok=True)
    shutil.move(old_target, new_target)

    return {"status": "ok", "old_path": req.old_path, "new_path": req.new_path}


@router.get("/workspace-info")
async def workspace_info(current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest)):
    """Guest workspaces: whether the server folder is new, so the browser should restore its copy."""
    if not getattr(current_user, "is_guest", False):
        return {"kind": "user", "restore_pending": False}
    return {"kind": "guest", **guest_workspaces.info(current_user.workspace_id)}


@router.post("/workspace-info/restored")
async def workspace_restored(current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest)):
    """The browser finished restoring (or had nothing to restore)."""
    if getattr(current_user, "is_guest", False):
        guest_workspaces.mark_restored(current_user.workspace_id)
    return {"status": "ok"}


@router.get("/download")
async def download_file(
    path: str = Query(..., description="Relative file path"),
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """Downloads a file directly from the workspace."""
    target_file = get_safe_user_path(current_user, path)
    if not os.path.isfile(target_file):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    from fastapi.responses import FileResponse
    filename = os.path.basename(target_file)
    return FileResponse(
        target_file,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/env")
async def get_workspace_env(
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """
    Returns user-specific environment variables defined in their private workspace .env.
    Shields all server-level secrets. Guests cannot access or persist private secrets.
    """
    if getattr(current_user, "is_guest", False):
        return {"env": {}}

    ws_dir = get_safe_workspace_root(current_user)
    env_file = os.path.join(ws_dir, ".env")
    if not os.path.exists(env_file):
        return {"env": {}}

    from dotenv import dotenv_values
    from ..package_security import SENSITIVE_SERVER_KEYS
    vars_dict = {}
    try:
        raw = dotenv_values(env_file)
        for k, v in raw.items():
            if k and v and k not in SENSITIVE_SERVER_KEYS:
                vars_dict[k] = v
    except Exception:
        pass
    return {"env": vars_dict}


@router.put("/env")
async def update_workspace_env(
    req: WorkspaceEnvUpdateRequest,
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """
    Saves user-specific environment variables and API keys to their private workspace .env.
    Prevents injecting reserved server keys.
    """
    if getattr(current_user, "is_guest", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Guests cannot persist private environment variables. Please sign in.",
        )

    from ..package_security import SENSITIVE_SERVER_KEYS
    ws_dir = get_safe_workspace_root(current_user)
    env_file = os.path.join(ws_dir, ".env")

    # Support either req.env or extra fields on req
    env_dict = req.env if req.env else req.model_dump(exclude={"env"})
    clean_entries = []
    saved_keys = []
    for k, v in env_dict.items():
        clean_k = str(k).strip()
        if not clean_k or clean_k in SENSITIVE_SERVER_KEYS:
            continue
        clean_entries.append(f"{clean_k}={str(v).strip()}")
        saved_keys.append(clean_k)

    with open(env_file, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(clean_entries) + "\n")

    return {"status": "ok", "keys": saved_keys, "message": "Workspace environment updated successfully."}

