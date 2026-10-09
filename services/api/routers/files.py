import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from ..models import User
from ..schemas import FileItemResponse, FileWriteRequest
from ..auth import get_current_user
from ..kernel_bridge import kernel_pool

router = APIRouter(prefix="/files", tags=["Files"])


def get_safe_user_path(user_id: str, relative_path: str = "") -> str:
    """
    Resolves and verifies that the target path is strictly contained within the user's workspace.
    Guarantees protection against path traversal (e.g. '../').
    """
    workspace_root = os.path.realpath(kernel_pool.get_user_workspace_path(user_id))
    # Clean relative path
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
    current_user: User = Depends(get_current_user),
):
    """Lists files and folders inside the user's sandboxed workspace."""
    target_dir = get_safe_user_path(current_user.id, directory)
    if not os.path.exists(target_dir):
        return []

    items = []
    for entry in os.scandir(target_dir):
        rel_path = os.path.relpath(entry.path, kernel_pool.get_user_workspace_path(current_user.id))
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
    current_user: User = Depends(get_current_user),
):
    """Reads a text or notebook file from the user's workspace."""
    target_file = get_safe_user_path(current_user.id, path)
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
    current_user: User = Depends(get_current_user),
):
    """Writes content to a file in the user's workspace."""
    target_file = get_safe_user_path(current_user.id, req.path)
    os.makedirs(os.path.dirname(target_file), exist_ok=True)
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(req.content)
    return {"status": "ok", "path": req.path}


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    directory: str = Query("", description="Target subdirectory"),
    current_user: User = Depends(get_current_user),
):
    """Uploads a file (CSV, XLSX, IPYNB, etc.) to the user's workspace."""
    target_dir = get_safe_user_path(current_user.id, directory)
    os.makedirs(target_dir, exist_ok=True)
    destination = os.path.join(target_dir, os.path.basename(file.filename or "upload.dat"))

    # Verify destination is still inside workspace
    workspace_root = os.path.realpath(kernel_pool.get_user_workspace_path(current_user.id))
    if not destination.startswith(workspace_root):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid destination path")

    with open(destination, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "status": "ok",
        "filename": os.path.basename(destination),
        "size": os.path.getsize(destination),
    }


@router.delete("")
async def delete_file(
    path: str = Query(..., description="Relative path of file or folder to delete"),
    current_user: User = Depends(get_current_user),
):
    """Deletes a file or directory within the workspace."""
    target_path = get_safe_user_path(current_user.id, path)
    if not os.path.exists(target_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    if os.path.isdir(target_path):
        shutil.rmtree(target_path)
    else:
        os.remove(target_path)
    return {"status": "ok", "deleted": path}

