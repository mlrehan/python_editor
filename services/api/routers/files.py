import os
import shutil
from typing import List, Union
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from ..models import User
from ..schemas import FileItemResponse, FileWriteRequest, FolderCreateRequest, FileRenameRequest
from ..auth import get_current_user_or_guest, GuestUser
from ..kernel_bridge import kernel_pool
from ..guest_ownership import guest_ownership

router = APIRouter(prefix="/files", tags=["Files"])


def get_safe_workspace_root(current_user: Union[User, GuestUser]) -> str:
    """Returns the canonical root directory for this user/guest session."""
    if getattr(current_user, "is_guest", False):
        return os.path.realpath(kernel_pool.get_public_workspace_path())
    return os.path.realpath(kernel_pool.get_user_workspace_path(current_user.id))


def get_safe_user_path(current_user: Union[User, GuestUser], relative_path: str = "") -> str:
    """
    Resolves and verifies that the target path is strictly contained within the user's workspace.
    For guests: resolves to shared public workspace.
    For authenticated users: resolves to isolated private workspace.
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
    """Writes content to a file in the workspace, enforcing guest capability authorization if public."""
    if getattr(current_user, "is_guest", False):
        if not guest_ownership.can_modify(req.path, getattr(current_user, "guest_token", None)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Cannot modify public file owned by another guest session.",
            )

    target_file = get_safe_user_path(current_user, req.path)
    os.makedirs(os.path.dirname(target_file), exist_ok=True)
    with open(target_file, "w", encoding="utf-8", newline="") as f:
        f.write(req.content)

    if getattr(current_user, "is_guest", False):
        guest_ownership.record_ownership(req.path, getattr(current_user, "guest_token", ""))

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

    if getattr(current_user, "is_guest", False):
        if os.path.exists(destination) and not guest_ownership.can_modify(rel_dest, getattr(current_user, "guest_token", None)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Cannot overwrite public file owned by another guest session.",
            )

    with open(destination, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    if getattr(current_user, "is_guest", False):
        guest_ownership.record_ownership(rel_dest, getattr(current_user, "guest_token", ""))

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
    if getattr(current_user, "is_guest", False):
        if not guest_ownership.can_modify(path, getattr(current_user, "guest_token", None)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Cannot delete public file owned by another guest session.",
            )

    target_path = get_safe_user_path(current_user, path)
    if not os.path.exists(target_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    if os.path.isdir(target_path):
        shutil.rmtree(target_path)
    else:
        os.remove(target_path)

    if getattr(current_user, "is_guest", False):
        guest_ownership.remove_ownership(path)

    return {"status": "ok", "deleted": path}


@router.post("/folder")
async def create_folder(
    req: FolderCreateRequest,
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """Creates a new folder within the workspace."""
    target_dir = get_safe_user_path(current_user, req.path)
    os.makedirs(target_dir, exist_ok=True)
    if getattr(current_user, "is_guest", False):
        guest_ownership.record_ownership(req.path, getattr(current_user, "guest_token", ""))
    return {"status": "ok", "path": req.path}


@router.post("/rename")
async def rename_file(
    req: FileRenameRequest,
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """Renames or moves a file or folder within the workspace."""
    if getattr(current_user, "is_guest", False):
        if not guest_ownership.can_modify(req.old_path, getattr(current_user, "guest_token", None)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Cannot rename public file owned by another guest session.",
            )

    old_target = get_safe_user_path(current_user, req.old_path)
    new_target = get_safe_user_path(current_user, req.new_path)

    if not os.path.exists(old_target):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source file not found")

    if os.path.exists(new_target):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Target name already exists")

    os.makedirs(os.path.dirname(new_target), exist_ok=True)
    shutil.move(old_target, new_target)

    if getattr(current_user, "is_guest", False):
        guest_ownership.rename_ownership(req.old_path, req.new_path, getattr(current_user, "guest_token", ""))

    return {"status": "ok", "old_path": req.old_path, "new_path": req.new_path}


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
