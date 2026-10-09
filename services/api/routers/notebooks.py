import os
import json
from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import nbformat as nbf

from ..database import get_db
from ..models import User, Notebook
from ..schemas import (
    NotebookCreate,
    NotebookUpdate,
    NotebookResponse,
    NotebookDetailResponse,
)
from ..auth import get_current_user_or_guest, GuestUser
from ..kernel_bridge import kernel_pool

router = APIRouter(prefix="/notebooks", tags=["Notebooks"])


def create_default_notebook_dict() -> Dict[str, Any]:
    """Creates a standard nbformat v4 empty notebook structure."""
    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell("# Welcome to Enterprise Python Cloud Studio\n\nRun your code cells below."),
        nbf.v4.new_code_cell("print('Hello World from Python Cloud Studio!')")
    ]
    return json.loads(nbf.writes(nb))


@router.post("", response_model=NotebookDetailResponse)
async def create_notebook(
    req: NotebookCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """Creates a new notebook with standard Jupyter v4 format in public or private workspace."""
    content = req.initial_content if req.initial_content else create_default_notebook_dict()
    owner_id = "public_guest" if getattr(current_user, "is_guest", False) else current_user.id

    notebook = Notebook(
        user_id=owner_id,
        project_id=req.project_id if not getattr(current_user, "is_guest", False) else None,
        title=req.title,
        content_json=json.dumps(content),
        kernel_name=req.kernel_name,
    )
    db.add(notebook)
    await db.commit()
    await db.refresh(notebook)

    try:
        if getattr(current_user, "is_guest", False):
            ws_dir = kernel_pool.get_public_workspace_path()
        else:
            ws_dir = kernel_pool.get_user_workspace_path(current_user.id)
        fname = notebook.title if notebook.title.endswith(".ipynb") else f"{notebook.title}.ipynb"
        with open(os.path.join(ws_dir, fname), "w", encoding="utf-8") as f:
            f.write(notebook.content_json)
    except Exception:
        pass

    return NotebookDetailResponse(
        id=notebook.id,
        user_id=notebook.user_id,
        project_id=notebook.project_id,
        title=notebook.title,
        kernel_name=notebook.kernel_name,
        created_at=notebook.created_at,
        updated_at=notebook.updated_at,
        content=content,
    )


@router.get("", response_model=List[NotebookResponse])
async def list_notebooks(
    project_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """Lists notebooks belonging to the current user (public for guests, strictly private for users)."""
    owner_id = "public_guest" if getattr(current_user, "is_guest", False) else current_user.id
    query = select(Notebook).where(Notebook.user_id == owner_id)
    if project_id and not getattr(current_user, "is_guest", False):
        query = query.where(Notebook.project_id == project_id)
    query = query.order_by(Notebook.updated_at.desc())

    result = await db.execute(query)
    notebooks = result.scalars().all()
    return notebooks


@router.get("/{notebook_id}", response_model=NotebookDetailResponse)
async def get_notebook(
    notebook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """Retrieves full notebook content with server-side ownership isolation."""
    owner_id = "public_guest" if getattr(current_user, "is_guest", False) else current_user.id
    result = await db.execute(
        select(Notebook).where(Notebook.id == notebook_id, Notebook.user_id == owner_id)
    )
    notebook = result.scalar_one_or_none()
    if not notebook:
        # Check if notebook exists under a registered user
        check_other = await db.execute(select(Notebook).where(Notebook.id == notebook_id))
        other_nb = check_other.scalar_one_or_none()
        if other_nb and getattr(current_user, "is_guest", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to access private notebook",
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")

    try:
        content = json.loads(notebook.content_json)
    except Exception:
        content = create_default_notebook_dict()

    return NotebookDetailResponse(
        id=notebook.id,
        user_id=notebook.user_id,
        project_id=notebook.project_id,
        title=notebook.title,
        kernel_name=notebook.kernel_name,
        created_at=notebook.created_at,
        updated_at=notebook.updated_at,
        content=content,
    )


@router.get("/{notebook_id}/export")
async def export_notebook(
    notebook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """Exports notebook as a downloadable .ipynb file."""
    owner_id = "public_guest" if getattr(current_user, "is_guest", False) else current_user.id
    result = await db.execute(
        select(Notebook).where(Notebook.id == notebook_id, Notebook.user_id == owner_id)
    )
    notebook = result.scalar_one_or_none()
    if not notebook:
        check_other = await db.execute(select(Notebook).where(Notebook.id == notebook_id))
        other_nb = check_other.scalar_one_or_none()
        if other_nb and getattr(current_user, "is_guest", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to export private notebook",
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")

    fname = notebook.title if notebook.title.endswith(".ipynb") else f"{notebook.title}.ipynb"
    return Response(
        content=notebook.content_json,
        media_type="application/x-ipynb+json",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.put("/{notebook_id}", response_model=NotebookDetailResponse)
async def update_notebook(
    notebook_id: str,
    req: NotebookUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """Saves notebook modifications with server-side ownership verification."""
    owner_id = "public_guest" if getattr(current_user, "is_guest", False) else current_user.id
    result = await db.execute(
        select(Notebook).where(Notebook.id == notebook_id, Notebook.user_id == owner_id)
    )
    notebook = result.scalar_one_or_none()
    if not notebook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")

    if req.title:
        notebook.title = req.title
    if req.content is not None:
        notebook.content_json = json.dumps(req.content)

    await db.commit()
    await db.refresh(notebook)

    try:
        if getattr(current_user, "is_guest", False):
            ws_dir = kernel_pool.get_public_workspace_path()
        else:
            ws_dir = kernel_pool.get_user_workspace_path(current_user.id)
        fname = notebook.title if notebook.title.endswith(".ipynb") else f"{notebook.title}.ipynb"
        with open(os.path.join(ws_dir, fname), "w", encoding="utf-8") as f:
            f.write(notebook.content_json)
    except Exception:
        pass

    content = json.loads(notebook.content_json)
    return NotebookDetailResponse(
        id=notebook.id,
        user_id=notebook.user_id,
        project_id=notebook.project_id,
        title=notebook.title,
        kernel_name=notebook.kernel_name,
        created_at=notebook.created_at,
        updated_at=notebook.updated_at,
        content=content,
    )


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notebook(
    notebook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """Deletes an authorized notebook."""
    owner_id = "public_guest" if getattr(current_user, "is_guest", False) else current_user.id
    result = await db.execute(
        select(Notebook).where(Notebook.id == notebook_id, Notebook.user_id == owner_id)
    )
    notebook = result.scalar_one_or_none()
    if not notebook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")

    title = notebook.title
    await db.delete(notebook)
    await db.commit()

    try:
        if getattr(current_user, "is_guest", False):
            ws_dir = kernel_pool.get_public_workspace_path()
        else:
            ws_dir = kernel_pool.get_user_workspace_path(current_user.id)
        fname = title if title.endswith(".ipynb") else f"{title}.ipynb"
        nb_file = os.path.join(ws_dir, fname)
        if os.path.exists(nb_file):
            os.remove(nb_file)
    except Exception:
        pass

    return Response(status_code=status.HTTP_204_NO_CONTENT)
