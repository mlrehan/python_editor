"""
Concurrent-user load test for kernel execution over WebSockets.

Each virtual user registers (or runs as a guest), opens a kernel WebSocket, executes a small pandas
workload a few times, then disconnects. Reports successful executions, graceful capacity rejections
(the server refusing with a clear message), hard errors, and latency percentiles, then checks that
the server is still healthy.

Usage (not collected by pytest):
    python tests/load/capacity_load_test.py --base-url http://127.0.0.1:8765 --users 100
    python tests/load/capacity_load_test.py --base-url https://studio.example.com --users 100 --guests
"""
import argparse
import asyncio
import json
import statistics
import time
import uuid

import httpx
import websockets

WORKLOAD = (
    "import pandas as pd, numpy as np\n"
    "df = pd.DataFrame(np.random.rand(20000, 8))\n"
    "print(round(float(df.mean().mean()), 3))"
)


async def run_user(idx: int, args, results: dict) -> None:
    async with httpx.AsyncClient(base_url=args.base_url, timeout=60) as client:
        if args.guests:
            token = (await client.post("/api/v1/auth/guest-session")).json()["guest_token"]
        else:
            email = f"load_{uuid.uuid4().hex[:10]}@example.com"
            r = await client.post("/api/v1/auth/register", json={
                "email": email, "password": "load-test-pass-123", "full_name": f"Load User {idx}",
            })
            if r.status_code != 200:
                results["errors"].append(f"user {idx}: register HTTP {r.status_code}")
                return
            token = r.json()["access_token"]

    ws_base = args.base_url.replace("https://", "wss://").replace("http://", "ws://")
    session_id = f"load-{idx}-{uuid.uuid4().hex[:6]}"
    try:
        async with websockets.connect(f"{ws_base}/ws/kernels/{session_id}?token={token}", open_timeout=60) as ws:
            first = json.loads(await asyncio.wait_for(ws.recv(), 60))
            if first.get("type") == "error":
                key = "rejected" if first.get("code") == "capacity" else "errors"
                results[key].append(f"user {idx}: {first.get('message')}")
                return
            for run in range(args.runs):
                started = time.perf_counter()
                await ws.send(json.dumps({"type": "execute", "cell_id": f"c{run}", "code": WORKLOAD}))
                ok = False
                while True:
                    msg = json.loads(await asyncio.wait_for(ws.recv(), args.cell_timeout))
                    if msg.get("type") == "output" and msg.get("output_type") == "error":
                        results["errors"].append(f"user {idx}: {msg.get('ename')}: {msg.get('evalue')}")
                    if msg.get("type") == "execute_reply" and msg.get("cell_id") == f"c{run}":
                        ok = msg.get("status") == "ok"
                        break
                if ok:
                    results["latencies"].append(time.perf_counter() - started)
                await asyncio.sleep(args.think_time)
    except Exception as e:  # connection refused, timeouts, abrupt closes
        results["errors"].append(f"user {idx}: {type(e).__name__}: {e}")


def pct(values, p):
    if not values:
        return 0.0
    values = sorted(values)
    return values[min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))]


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--runs", type=int, default=3, help="executions per user")
    parser.add_argument("--ramp-seconds", type=float, default=20.0, help="spread user arrivals over this window")
    parser.add_argument("--think-time", type=float, default=1.0)
    parser.add_argument("--cell-timeout", type=float, default=120.0)
    parser.add_argument("--guests", action="store_true", help="use guest sessions instead of registered users")
    args = parser.parse_args()

    results = {"latencies": [], "errors": [], "rejected": []}

    async def delayed(i):
        await asyncio.sleep(args.ramp_seconds * i / max(1, args.users))
        await run_user(i, args, results)

    started = time.time()
    await asyncio.gather(*(delayed(i) for i in range(args.users)))
    elapsed = time.time() - started

    async with httpx.AsyncClient(base_url=args.base_url, timeout=30) as client:
        health = (await client.get("/api/v1/health")).json()

    lat = results["latencies"]
    print(f"users={args.users} runs/user={args.runs} elapsed={elapsed:.1f}s")
    print(f"successful executions={len(lat)} / attempted={args.users * args.runs}")
    print(f"graceful capacity rejections={len(results['rejected'])}  hard errors={len(results['errors'])}")
    if lat:
        print(f"latency p50={pct(lat, 50):.2f}s p95={pct(lat, 95):.2f}s p99={pct(lat, 99):.2f}s max={max(lat):.2f}s "
              f"mean={statistics.mean(lat):.2f}s")
    print(f"server health after test: {health.get('status')} kernels={health.get('kernels')}")
    for line in (results["rejected"][:3] + results["errors"][:10]):
        print("  -", line)
    return 1 if results["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
