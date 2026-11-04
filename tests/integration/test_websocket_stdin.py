"""WebSocket execution: input() round-trip and interrupting a running cell."""
import time
import uuid

from starlette.testclient import TestClient

from services.api.main import app
from services.api.guest_workspace import guest_workspace_id, issue_guest_token


def _receive_until(ws, msg_type, cell_id=None, limit=200):
    """Collects messages until one of msg_type (for cell_id, if given) arrives."""
    seen = []
    for _ in range(limit):
        msg = ws.receive_json()
        seen.append(msg)
        if msg.get("type") == msg_type and (cell_id is None or msg.get("cell_id") == cell_id):
            return msg, seen
    raise AssertionError(f"{msg_type} not received; got {[m.get('type') for m in seen]}")


def _ws_url():
    return f"/ws/kernels/test-stdin-{uuid.uuid4().hex[:8]}?token={issue_guest_token()}"


def test_input_round_trip_over_websocket():
    with TestClient(app) as client:
        with client.websocket_connect(_ws_url()) as ws:
            _receive_until(ws, "kernel_status")
            ws.send_json({"type": "execute", "cell_id": "c1", "code": 'name = input("Enter your name: ")\nprint("Hello", name)'})

            request, _ = _receive_until(ws, "input_request", "c1")
            assert request["prompt"] == "Enter your name: "
            assert request["password"] is False

            ws.send_json({"type": "input_reply", "value": "Ada"})
            reply, seen = _receive_until(ws, "execute_reply", "c1")
            assert reply["status"] == "ok"
            output_text = "".join(m.get("text") or "" for m in seen if m.get("type") == "output")
            assert "Hello Ada" in output_text


def test_interrupt_reaches_running_cell():
    with TestClient(app) as client:
        with client.websocket_connect(_ws_url()) as ws:
            _receive_until(ws, "kernel_status")
            # A pure-Python loop: on Windows, ipykernel's interrupt cannot wake a blocking time.sleep()
            ws.send_json({"type": "execute", "cell_id": "slow", "code": "import time\nend = time.time() + 30\nwhile time.time() < end:\n    pass\nprint('finished')"})
            _receive_until(ws, "status", "slow")  # busy
            time.sleep(2)

            started = time.time()
            ws.send_json({"type": "interrupt"})
            reply, seen = _receive_until(ws, "execute_reply", "slow")
            assert time.time() - started < 15
            assert reply["status"] == "error"
            errors = [m for m in seen if m.get("type") == "output" and m.get("output_type") == "error"]
            assert errors and errors[0]["ename"] == "KeyboardInterrupt"


def test_closed_connections_never_leave_a_kernel_marked_attached():
    from services.api.kernel_bridge import kernel_pool

    with TestClient(app) as client:
        url = _ws_url()
        session_id = url.split("/ws/kernels/")[1].split("?")[0]
        token = url.split("token=")[1]
        # Connect and drop immediately, several times, including before reading the first message
        for read_first in (False, True, False):
            with client.websocket_connect(url) as ws:
                if read_first:
                    # "starting" comes first; wait for the kernel to be ready
                    while _receive_until(ws, "kernel_status")[0].get("status") != "ready":
                        pass
        deadline = time.time() + 10
        session = None
        while time.time() < deadline:
            session = kernel_pool.get_session(session_id, f"guest_{guest_workspace_id(token)}")
            if session is not None and session.attached_clients == 0:
                break
            time.sleep(0.2)
        assert session is not None
        assert session.attached_clients == 0, "a closed connection left the kernel marked as in use"
        assert session.detached_at is not None


def test_interrupt_while_waiting_for_input_keeps_kernel_usable():
    with TestClient(app) as client:
        with client.websocket_connect(_ws_url()) as ws:
            _receive_until(ws, "kernel_status")
            ws.send_json({"type": "execute", "cell_id": "ask", "code": 'input("never answered: ")'})
            _receive_until(ws, "input_request", "ask")

            ws.send_json({"type": "interrupt"})
            reply, _ = _receive_until(ws, "execute_reply", "ask")
            assert reply["status"] == "error"

            ws.send_json({"type": "execute", "cell_id": "next", "code": "print('still alive')"})
            reply, seen = _receive_until(ws, "execute_reply", "next")
            assert reply["status"] == "ok"
            assert "still alive" in "".join(m.get("text") or "" for m in seen if m.get("type") == "output")
