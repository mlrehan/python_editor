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
    if token and not token.startswith("gst_"):
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub") or "public"
        except Exception:
            user_id = "public"

    await websocket.accept()

    try:
        # 2. Retrieve or provision user kernel session
        session = await kernel_pool.get_or_create_session(
            session_id=session_id,
            user_id=user_id,
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

                result = await session.execute(code, on_output_chunk=stream_callback)

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

