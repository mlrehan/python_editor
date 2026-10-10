"""
Production Load & Concurrency Benchmark Suite: 100+ Concurrent Users
Target: http://127.0.0.1:8765 (Enterprise Python Cloud Studio)

Measures:
  - Throughput (Requests per Second)
  - Error Rate (%)
  - Latency Distribution: min, mean, p50 (median), p95, p99, max
Across:
  1. 100 Concurrent Dashboard & API requests
  2. 100 Concurrent Notebook Read & Save Operations
  3. 100 Concurrent WebSocket Connections & Handshakes
  4. Concurrent Python Kernel Executions
"""

import asyncio
import time
import statistics
import json
import pytest
import httpx
import websockets

BASE_URL = "http://127.0.0.1:8765"
WS_URL = "ws://127.0.0.1:8765"
CONCURRENT_USERS = 100


def calculate_metrics(latencies: list, total_time: float, errors: int):
    if not latencies:
        return {}
    latencies.sort()
    count = len(latencies)
    return {
        "count": count,
        "errors": errors,
        "error_rate": (errors / (count + errors)) * 100 if (count + errors) > 0 else 0,
        "throughput": count / total_time if total_time > 0 else 0,
        "min_ms": round(latencies[0] * 1000, 2),
        "mean_ms": round(statistics.mean(latencies) * 1000, 2),
        "p50_ms": round(statistics.median(latencies) * 1000, 2),
        "p95_ms": round(latencies[int(count * 0.95)] * 1000, 2),
        "p99_ms": round(latencies[min(int(count * 0.99), count - 1)] * 1000, 2),
        "max_ms": round(latencies[-1] * 1000, 2),
    }


def print_metrics_table(title: str, m: dict):
    print(f"\n{'='*75}")
    print(f"  BENCHMARK: {title}")
    print(f"{'='*75}")
    print(f"  Total Requests Completed: {m['count']}")
    print(f"  Errors / Failures:        {m['errors']} ({m['error_rate']:.2f}%)")
    print(f"  Throughput:               {m['throughput']:.2f} req/sec")
    print(f"  Latency (min):            {m['min_ms']:.2f} ms")
    print(f"  Latency (mean):           {m['mean_ms']:.2f} ms")
    print(f"  Latency (p50 / median):   {m['p50_ms']:.2f} ms")
    print(f"  Latency (p95):            {m['p95_ms']:.2f} ms")
    print(f"  Latency (p99):            {m['p99_ms']:.2f} ms")
    print(f"  Latency (max):            {m['max_ms']:.2f} ms")
    print(f"{'='*75}\n")


# =========================================================================
# TEST 1: 100 CONCURRENT DASHBOARD & API REQUESTS
# =========================================================================
@pytest.mark.asyncio
async def test_100_concurrent_dashboard_requests():
    """Verify system handles 100 concurrent dashboard and health requests."""
    latencies = []
    errors = 0

    async def worker(client: httpx.AsyncClient, user_idx: int):
        nonlocal errors
        t0 = time.perf_counter()
        try:
            res = await client.get(f"{BASE_URL}/api/v1/health")
            elapsed = time.perf_counter() - t0
            if res.status_code == 200:
                latencies.append(elapsed)
            else:
                errors += 1
        except Exception:
            errors += 1

    t_start = time.perf_counter()
    async with httpx.AsyncClient(timeout=15.0) as client:
        tasks = [worker(client, i) for i in range(CONCURRENT_USERS)]
        await asyncio.gather(*tasks)
    total_time = time.perf_counter() - t_start

    metrics = calculate_metrics(latencies, total_time, errors)
    print_metrics_table("100 Concurrent Dashboard & Health Checks", metrics)

    assert metrics["errors"] == 0, f"Encountered {metrics['errors']} errors"
    assert metrics["count"] == CONCURRENT_USERS
    assert metrics["p95_ms"] < 2000, f"p95 latency exceeded 2000ms: {metrics['p95_ms']}ms"


# =========================================================================
# TEST 2: 100 CONCURRENT NOTEBOOK READ & SAVE OPERATIONS
# =========================================================================
@pytest.mark.asyncio
async def test_100_concurrent_notebook_operations():
    """Verify system handles 100 concurrent notebook list, fetch, and save operations."""
    latencies = []
    errors = 0

    # Ensure initial guest token or authenticated token
    async def worker(user_idx: int):
        nonlocal errors
        guest_token = f"load_test_guest_{user_idx}_{int(time.time())}"
        headers = {"X-Guest-Token": guest_token}

        async with httpx.AsyncClient(timeout=60.0) as client:
            t0 = time.perf_counter()
            try:
                # 1. List notebooks
                list_res = await client.get(f"{BASE_URL}/api/v1/notebooks", headers=headers)
                if list_res.status_code != 200:
                    errors += 1
                    return

                # 2. Save a notebook state
                save_payload = {
                    "title": f"Load Test Notebook User {user_idx}",
                    "content": {
                        "nbformat": 4,
                        "nbformat_minor": 5,
                        "metadata": {"kernelspec": {"name": "python3"}},
                        "cells": [
                            {
                                "cell_type": "code",
                                "source": f"print('Load test cell from user {user_idx}')",
                                "outputs": [],
                                "execution_count": 1,
                            }
                        ],
                    },
                }

                # Try creating a notebook
                create_res = await client.post(
                    f"{BASE_URL}/api/v1/notebooks",
                    json={"title": f"Load Test {user_idx}", "kernel_name": "python3"},
                    headers=headers,
                )
                if create_res.status_code == 200:
                    nb_id = create_res.json()["id"]
                    # Save / update notebook
                    put_res = await client.put(
                        f"{BASE_URL}/api/v1/notebooks/{nb_id}",
                        json=save_payload,
                        headers=headers,
                    )
                    elapsed = time.perf_counter() - t0
                    if put_res.status_code == 200:
                        latencies.append(elapsed)
                    else:
                        print(f"Worker {user_idx} PUT status {put_res.status_code}: {put_res.text[:100]}")
                        errors += 1
                else:
                    print(f"Worker {user_idx} POST status {create_res.status_code}: {create_res.text[:100]}")
                    errors += 1
            except Exception as e:
                print(f"Worker {user_idx} exception: {type(e).__name__}: {e}")
                errors += 1

    t_start = time.perf_counter()
    tasks = [worker(i) for i in range(CONCURRENT_USERS)]
    await asyncio.gather(*tasks)
    total_time = time.perf_counter() - t_start

    metrics = calculate_metrics(latencies, total_time, errors)
    print_metrics_table("100 Concurrent Notebook List & Save Operations", metrics)

    assert metrics["errors"] == 0, f"Encountered {metrics['errors']} errors"
    assert metrics["count"] == CONCURRENT_USERS
    assert metrics["p95_ms"] < 60000, f"p95 latency exceeded 60000ms: {metrics['p95_ms']}ms"


# =========================================================================
# TEST 3: 100 CONCURRENT WEBSOCKET CONNECTIONS
# =========================================================================
@pytest.mark.asyncio
async def test_100_concurrent_websocket_connections():
    """Verify server sustains 100 concurrent WebSocket connections simultaneously."""
    latencies = []
    errors = 0
    active_connections = []

    async def ws_worker(idx: int):
        nonlocal errors
        session_id = f"load-ws-session-{idx}-{int(time.time())}"
        guest_token = f"load_gst_ws_{idx}"
        url = f"{WS_URL}/ws/kernels/{session_id}?token={guest_token}"

        t0 = time.perf_counter()
        try:
            ws = await websockets.connect(url, close_timeout=5.0)
            elapsed = time.perf_counter() - t0
            latencies.append(elapsed)
            active_connections.append(ws)

            # Send a ping/status check
            msg = {"msg_type": "status_request"}
            await ws.send(json.dumps(msg))
            await asyncio.sleep(0.5)
        except Exception:
            errors += 1

    t_start = time.perf_counter()
    tasks = [ws_worker(i) for i in range(CONCURRENT_USERS)]
    await asyncio.gather(*tasks)
    total_time = time.perf_counter() - t_start

    metrics = calculate_metrics(latencies, total_time, errors)
    print_metrics_table("100 Concurrent WebSocket Connections & Handshakes", metrics)

    # Cleanly close all connections
    for ws in active_connections:
        try:
            await ws.close()
        except Exception:
            pass

    assert metrics["errors"] == 0, f"WebSocket errors: {metrics['errors']}"
    assert len(active_connections) == CONCURRENT_USERS
    assert metrics["p95_ms"] < 2500, f"WebSocket p95 exceeded 2500ms: {metrics['p95_ms']}ms"


# =========================================================================
# TEST 4: CONCURRENT KERNEL EXECUTIONS
# =========================================================================
@pytest.mark.asyncio
async def test_concurrent_kernel_executions():
    """Verify concurrent Python code executions across distinct isolated sessions."""
    latencies = []
    errors = 0
    NUM_EXECUTIONS = 20

    async def exec_worker(idx: int):
        nonlocal errors
        session_id = f"load-exec-session-{idx}-{int(time.time())}"
        guest_token = f"exec_gst_{idx}"
        code = f"x = {idx} * 2\nprint(f'COMPUTED_{idx}_RESULT:{{x}}')"

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(
                    f"{BASE_URL}/api/v1/execution/run",
                    json={"session_id": session_id, "code": code},
                    headers={"X-Guest-Token": guest_token},
                )
                elapsed = time.perf_counter() - t0
                if res.status_code == 200:
                    data = res.json()
                    outputs = data.get("outputs", [])
                    stream_text = "".join(o.get("text", "") for o in outputs if o.get("output_type") == "stream")
                    if f"COMPUTED_{idx}_RESULT:{idx * 2}" in stream_text:
                        latencies.append(elapsed)
                    else:
                        errors += 1
                        print(f"[DEBUG EXEC {idx}] Output mismatch: outputs={outputs}, err={data.get('error')}")
                else:
                    errors += 1
                    print(f"[DEBUG EXEC {idx}] HTTP {res.status_code}: {res.text}")
        except Exception as e:
            errors += 1
            print(f"[DEBUG EXEC {idx}] Exception: {e}")

    t_start = time.perf_counter()
    sem = asyncio.Semaphore(10)

    async def bounded_worker(idx: int):
        async with sem:
            await exec_worker(idx)

    tasks = [bounded_worker(i) for i in range(NUM_EXECUTIONS)]
    await asyncio.gather(*tasks)
    total_time = time.perf_counter() - t_start

    metrics = calculate_metrics(latencies, total_time, errors)
    print_metrics_table("Concurrent Kernel Code Executions", metrics)

    assert metrics["errors"] == 0, f"Kernel execution errors: {metrics['errors']}"
    assert metrics["count"] == NUM_EXECUTIONS


if __name__ == "__main__":
    asyncio.run(test_100_concurrent_dashboard_requests())
    asyncio.run(test_100_concurrent_notebook_operations())
    asyncio.run(test_100_concurrent_websocket_connections())
    asyncio.run(test_concurrent_kernel_executions())
