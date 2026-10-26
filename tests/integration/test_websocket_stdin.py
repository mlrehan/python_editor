"""WebSocket execution: input() round-trip and interrupting a running cell."""
import time
import uuid

from starlette.testclient import TestClient

from services.api.main import app


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
    return f"/ws/kernels/test-stdin-{uuid.uuid4().hex[:8]}?token=gst_test_{uuid.uuid4().hex[:8]}"


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
