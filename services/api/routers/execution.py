from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from ..models import User
from ..schemas import CodeExecutionRequest, CodeExecutionResponse, KernelControlRequest
from ..auth import get_current_user
from ..kernel_bridge import kernel_pool

router = APIRouter(prefix="/execution", tags=["Execution"])


@router.post("/run", response_model=CodeExecutionResponse)
async def run_code(
    req: CodeExecutionRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Executes Python code on the user's isolated IPyKernel.
    Guarantees genuine Python execution and returns all MIME-bundle outputs.
    """
    try:
        session = await kernel_pool.get_or_create_session(
            session_id=req.session_id,
            user_id=current_user.id,
        )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot access kernel belonging to another user.",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )

    result = await session.execute(req.code, timeout=req.timeout)

    return CodeExecutionResponse(
        session_id=req.session_id,
        msg_id=result.msg_id,
        status=result.status,
        execution_count=result.execution_count,
        outputs=result.outputs,
        error=result.error,
        execution_time=result.execution_time,
    )


@router.post("/control")
async def control_kernel(
    req: KernelControlRequest,
    current_user: User = Depends(get_current_user),
):
    """Controls kernel lifecycle: interrupt, restart, shutdown."""
    session = kernel_pool.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kernel session not found")

    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized kernel session access")

    if req.action == "interrupt":
        await session.interrupt()
        return {"status": "ok", "action": "interrupted"}
    elif req.action == "restart":
        await session.restart()
        return {"status": "ok", "action": "restarted"}
    elif req.action == "shutdown":
        await kernel_pool.shutdown_session(req.session_id)
        return {"status": "ok", "action": "shutdown"}
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown action: {req.action}")


@router.get("/sessions")
async def list_user_sessions(current_user: User = Depends(get_current_user)):
    """Lists currently active kernel sessions for the authenticated user."""
    sessions = []
    for s_id, s in kernel_pool._sessions.items():
        if s.user_id == current_user.id:
            sessions.append({
                "session_id": s_id,
                "is_running": s.is_running,
                "created_at": s.created_at,
                "last_active_at": s.last_active_at,
                "execution_count": s.execution_count,
                "workspace_dir": s.workspace_dir,
            })
    return sessions

