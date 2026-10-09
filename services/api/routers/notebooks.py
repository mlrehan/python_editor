import os
import json
from typing import List, Optional, Dict, Any
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
from ..auth import get_current_user
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
    current_user: User = Depends(get_current_user),
):
    """Creates a new notebook with standard Jupyter v4 format."""
    content = req.initial_content if req.initial_content else create_default_notebook_dict()

    notebook = Notebook(
        user_id=current_user.id,
        project_id=req.project_id,
        title=req.title,
        content_json=json.dumps(content),
        kernel_name=req.kernel_name,
    )
    db.add(notebook)
    await db.commit()
    await db.refresh(notebook)

    try:
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
    current_user: User = Depends(get_current_user),
):
    """Lists notebooks belonging to the authenticated user."""
    query = select(Notebook).where(Notebook.user_id == current_user.id)
    if project_id:
        query = query.where(Notebook.project_id == project_id)
    query = query.order_by(Notebook.updated_at.desc())

    result = await db.execute(query)
    notebooks = result.scalars().all()
    return notebooks


@router.get("/{notebook_id}", response_model=NotebookDetailResponse)
async def get_notebook(
    notebook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves full notebook content."""
    result = await db.execute(
        select(Notebook).where(Notebook.id == notebook_id, Notebook.user_id == current_user.id)
    )
    notebook = result.scalar_one_or_none()
    if not notebook:
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


@router.put("/{notebook_id}", response_model=NotebookDetailResponse)
async def update_notebook(
    notebook_id: str,
    req: NotebookUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Saves notebook modifications and title updates."""
    result = await db.execute(
        select(Notebook).where(Notebook.id == notebook_id, Notebook.user_id == current_user.id)
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
    current_user: User = Depends(get_current_user),
):
    """Deletes an authorized notebook."""
    result = await db.execute(
        select(Notebook).where(Notebook.id == notebook_id, Notebook.user_id == current_user.id)
    )
    notebook = result.scalar_one_or_none()
    if not notebook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")

    title = notebook.title
    await db.delete(notebook)
    await db.commit()

    try:
        ws_dir = kernel_pool.get_user_workspace_path(current_user.id)
        fname = title if title.endswith(".ipynb") else f"{title}.ipynb"
        fpath = os.path.join(ws_dir, fname)
        if os.path.exists(fpath):
            os.remove(fpath)
    except Exception:
        pass
    return None


@router.get("/{notebook_id}/export")
async def export_ipynb(
    notebook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Downloads the notebook as standard .ipynb format."""
    result = await db.execute(
        select(Notebook).where(Notebook.id == notebook_id, Notebook.user_id == current_user.id)
    )
    notebook = result.scalar_one_or_none()
    if not notebook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")

    filename = f"{notebook.title.replace(' ', '_')}.ipynb"
    return Response(
        content=notebook.content_json,
        media_type="application/x-ipynb+json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

