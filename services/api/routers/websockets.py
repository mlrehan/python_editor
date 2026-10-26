import json
import asyncio
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from ..auth import decode_access_token
from ..kernel_bridge import kernel_pool

router = APIRouter(tags=["WebSockets"])


@router.websocket("/ws/kernels/{session_id}")
async def kernel_websocket(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None),
):
    """
    Bidirectional WebSocket connection bridging interactive frontend execution
    with the genuine IPyKernel process.
    Streams outputs token-by-token and manages execution state.
    """
    # 1. Authenticate WebSocket connection token
    user_id = "public"
    token_str = token if token and token.startswith("gst_") else "guest_default"
    if token and not token.startswith("gst_"):
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub") or "public"
        except Exception:
            user_id = "public"

    user = None
    if user_id != "public":
        from ..database import AsyncSessionLocal
        from ..models import User
        from sqlalchemy import select
        async with AsyncSessionLocal() as db_sess:
            res_user = await db_sess.execute(select(User).where(User.id == user_id))
            user = res_user.scalar_one_or_none()

    if not user:
        from ..auth import GuestUser
        user = GuestUser(guest_token=token_str)
        user_id = f"guest_{token_str}"

    await websocket.accept()

    try:
        # 2. Retrieve or provision user kernel session
        is_admin = getattr(user, "role", "") == "super_admin" or user_id == "admin_super"
        session = await kernel_pool.get_or_create_session(
            session_id=session_id,
            user_id=user_id,
            is_admin=is_admin,
        )
    except Exception as e:
        await websocket.send_json({"type": "error", "message": f"Failed to start kernel: {str(e)}"})
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    # Broadcast initial ready state
    await websocket.send_json({
        "type": "kernel_status",
        "session_id": session_id,
        "status": "ready" if session.is_running else "starting",
        "execution_count": session.execution_count,
    })

    from ..package_security import validate_code_security
    from ..audit import record_audit_log

    async def send_safe(msg: dict) -> None:
        try:
            await websocket.send_json(msg)
        except Exception:
            pass

    async def run_execution(cell_id: Optional[str], code: str) -> None:
        await send_safe({
            "type": "status",
            "cell_id": cell_id,
            "execution_state": "busy",
        })

        # Validate code security (block unauthorized package installs and OS escapes)
        is_allowed, error_msg, final_code = validate_code_security(code, user)
        if not is_allowed:
            await record_audit_log(
                user_id=user_id,
                action="code_execution_blocked",
                resource_type="kernel_session",
                resource_id=session_id,
                details={"reason": error_msg, "code_snippet": code[:200]},
            )
            await send_safe({
                "type": "output",
                "cell_id": cell_id,
                "output_type": "error",
                "ename": "SecurityError",
                "evalue": error_msg,
                "traceback": [f"SecurityError: {error_msg}"],
            })
            await send_safe({
                "type": "execute_reply",
                "cell_id": cell_id,
                "status": "error",
                "execution_count": session.execution_count,
                "execution_time": 0.001,
            })
            await send_safe({
                "type": "status",
                "cell_id": cell_id,
                "execution_state": "idle",
            })
            return

        if final_code != code or "%pip" in code or "!pip" in code:
            await record_audit_log(
                user_id=user_id,
                action="package_install_attempt",
                resource_type="kernel_session",
                resource_id=session_id,
                details={"code_snippet": code[:200], "status": "authorized"},
            )

        # Callback for streaming outputs directly to client as they arrive
        async def stream_callback(chunk: dict):
            await send_safe({
                "type": "output",
                "cell_id": cell_id,
                **chunk,
            })

        # Forward input()/getpass() prompts; the client answers with an "input_reply" message
        async def input_callback(prompt: str, password: bool):
            await send_safe({
                "type": "input_request",
                "cell_id": cell_id,
                "prompt": prompt,
                "password": password,
            })

        try:
            result = await session.execute(
                final_code,
                on_output_chunk=stream_callback,
                on_input_request=input_callback,
            )
            reply_status = result.status
            reply_count = result.execution_count
            reply_time = result.execution_time
        except asyncio.CancelledError:
            raise
        except Exception as e:
            await send_safe({
                "type": "output",
                "cell_id": cell_id,
                "output_type": "error",
                "ename": type(e).__name__,
                "evalue": str(e),
                "traceback": [f"{type(e).__name__}: {e}"],
            })
            reply_status, reply_count, reply_time = "error", session.execution_count, 0.0

        await send_safe({
            "type": "execute_reply",
            "cell_id": cell_id,
            "status": reply_status,
            "execution_count": reply_count,
            "execution_time": reply_time,
        })
        await send_safe({
            "type": "status",
            "cell_id": cell_id,
            "execution_state": "idle",
        })

    # Executions run one at a time in a worker task so this receive loop stays free to handle
    # input replies, interrupts and restarts while a cell is running.
    exec_queue: "asyncio.Queue[tuple]" = asyncio.Queue()

    async def execution_worker():
        while True:
            cell_id, code = await exec_queue.get()
            await run_execution(cell_id, code)

    async def abort_queued() -> None:
        """Drops executions that have not started yet and tells the client they were aborted."""
        while not exec_queue.empty():
            cell_id, _ = exec_queue.get_nowait()
            await send_safe({"type": "execute_reply", "cell_id": cell_id, "status": "abort", "execution_count": None, "execution_time": 0.0})
            await send_safe({"type": "status", "cell_id": cell_id, "execution_state": "idle"})

    async def restart_kernel():
        await abort_queued()
        await session.restart()
        await send_safe({
            "type": "restarted",
            "session_id": session_id,
            "execution_count": 0,
        })

    worker = asyncio.create_task(execution_worker())
    background: set = set()

    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
            except json.JSONDecodeError:
                await send_safe({"type": "error", "message": "Invalid JSON format"})
                continue

            msg_type = data.get("type")

            if msg_type == "execute":
                await exec_queue.put((data.get("cell_id"), data.get("code", "")))

            elif msg_type == "input_reply":
                if not session.send_input(str(data.get("value", ""))):
                    await send_safe({"type": "error", "message": "No input is currently requested by the kernel"})

            elif msg_type == "interrupt":
                await abort_queued()
                await session.interrupt()
                await send_safe({"type": "interrupted", "session_id": session_id})

            elif msg_type == "restart":
                task = asyncio.create_task(restart_kernel())
                background.add(task)
                task.add_done_callback(background.discard)

            elif msg_type == "ping":
                await send_safe({"type": "pong"})

    except WebSocketDisconnect:
        # Client disconnected cleanly
        pass
    except Exception as e:
        await send_safe({"type": "error", "message": str(e)})
    finally:
        worker.cancel()
        # Nobody is left to answer a pending input(); interrupt so the kernel is not stuck waiting
        if session.input_pending:
            try:
                await session.interrupt()
            except Exception:
                pass
