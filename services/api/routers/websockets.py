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

    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON format"})
                continue

            msg_type = data.get("type")
            cell_id = data.get("cell_id")

            if msg_type == "execute":
                code = data.get("code", "")
                await websocket.send_json({
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
                    await websocket.send_json({
                        "type": "output",
                        "cell_id": cell_id,
                        "output_type": "error",
                        "ename": "SecurityError",
                        "evalue": error_msg,
                        "traceback": [f"SecurityError: {error_msg}"],
                    })
                    await websocket.send_json({
                        "type": "execute_reply",
                        "cell_id": cell_id,
                        "status": "error",
                        "execution_count": session.execution_count,
                        "execution_time": 0.001,
                    })
                    await websocket.send_json({
                        "type": "status",
                        "cell_id": cell_id,
                        "execution_state": "idle",
                    })
                    continue

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
                    msg = {
                        "type": "output",
                        "cell_id": cell_id,
                        **chunk,
                    }
                    try:
                        await websocket.send_json(msg)
                    except Exception:
                        pass

                result = await session.execute(final_code, on_output_chunk=stream_callback)

                await websocket.send_json({
                    "type": "execute_reply",
                    "cell_id": cell_id,
                    "status": result.status,
                    "execution_count": result.execution_count,
                    "execution_time": result.execution_time,
                })
                await websocket.send_json({
                    "type": "status",
                    "cell_id": cell_id,
                    "execution_state": "idle",
                })

            elif msg_type == "interrupt":
                await session.interrupt()
                await websocket.send_json({"type": "interrupted", "session_id": session_id})

            elif msg_type == "restart":
                await session.restart()
                await websocket.send_json({
                    "type": "restarted",
                    "session_id": session_id,
                    "execution_count": 0,
                })

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        # Client disconnected cleanly
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass

