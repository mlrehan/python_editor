from typing import List, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, status
from ..models import User
from ..schemas import CodeExecutionRequest, CodeExecutionResponse, KernelControlRequest
from ..auth import get_current_user_or_guest, GuestUser
from ..kernel_bridge import kernel_pool

router = APIRouter(prefix="/execution", tags=["Execution"])


@router.post("/run", response_model=CodeExecutionResponse)
async def run_code(
    req: CodeExecutionRequest,
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """
    Executes Python code on the user's isolated IPyKernel.
    Guarantees genuine Python execution in public (guest) or private (user) workspace.
    """
    target_user_id = f"guest_{current_user.guest_token}" if getattr(current_user, "is_guest", False) else current_user.id

    # 1. Enforce package installation permissions and system security boundaries
    from ..package_security import validate_code_security
    from ..audit import record_audit_log

    is_allowed, error_msg, final_code = validate_code_security(req.code, current_user)
    if not is_allowed:
        await record_audit_log(
            user_id=target_user_id,
            action="code_execution_blocked",
            resource_type="kernel_session",
            resource_id=req.session_id,
            details={"reason": error_msg, "code_snippet": req.code[:200]},
        )
        error_output = {
            "output_type": "error",
            "ename": "SecurityError",
            "evalue": error_msg,
            "traceback": [f"SecurityError: {error_msg}"],
        }
        return CodeExecutionResponse(
            session_id=req.session_id,
            msg_id="sec-denied",
            status="error",
            execution_count=None,
            outputs=[error_output],
            error=error_output,
            execution_time=0.001,
        )

    if final_code != req.code or "%pip" in req.code or "!pip" in req.code:
        await record_audit_log(
            user_id=target_user_id,
            action="package_install_attempt",
            resource_type="kernel_session",
            resource_id=req.session_id,
            details={"code_snippet": req.code[:200], "status": "authorized"},
        )

    is_admin = getattr(current_user, "role", "") == "super_admin" or target_user_id == "admin_super"
    try:
        session = await kernel_pool.get_or_create_session(
            session_id=req.session_id,
            user_id=target_user_id,
            is_admin=is_admin,
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

    result = await session.execute(final_code, timeout=req.timeout)

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
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """Controls kernel lifecycle: interrupt, restart, shutdown."""
    target_user_id = f"guest_{current_user.guest_token}" if getattr(current_user, "is_guest", False) else current_user.id
    is_admin = getattr(current_user, "role", "") in ("super_admin", "admin") or target_user_id == "admin_super"
    session = kernel_pool.get_session(req.session_id, target_user_id)

    if session:
        is_both_guest = (session.user_id.startswith("guest_") or session.user_id == "public_guest") and \
                        (target_user_id.startswith("guest_") or target_user_id == "public_guest")
        if session.user_id != target_user_id and not is_admin and not is_both_guest:
            session = None

    if not session:
        if req.action == "restart":
            session = await kernel_pool.get_or_create_session(
                session_id=req.session_id,
                user_id=target_user_id,
                is_admin=is_admin,
            )
            return {"status": "ok", "action": "restarted"}
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kernel session not found")

    if req.action == "interrupt":
        await session.interrupt()
        return {"status": "ok", "action": "interrupted"}
    elif req.action == "restart":
        await session.restart()
        return {"status": "ok", "action": "restarted"}
    elif req.action == "shutdown":
        await kernel_pool.shutdown_session(req.session_id, target_user_id)
        return {"status": "ok", "action": "shutdown"}
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown action: {req.action}")


@router.get("/sessions")
async def list_user_sessions(current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest)):
    """Lists currently active kernel sessions for the current user."""
    target_user_id = f"guest_{current_user.guest_token}" if getattr(current_user, "is_guest", False) else current_user.id
    sessions = []
    for s_id, s in kernel_pool._sessions.items():
        if s.user_id == target_user_id or getattr(current_user, "role", "") in ("super_admin", "admin"):
            sessions.append({
                "session_id": s_id,
                "is_running": s.is_running,
                "created_at": s.created_at,
                "last_active_at": s.last_active_at,
                "execution_count": s.execution_count,
                "workspace_dir": s.workspace_dir,
            })
    return sessions
