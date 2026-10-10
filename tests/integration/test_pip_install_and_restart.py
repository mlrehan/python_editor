import pytest
import httpx
import asyncio

BASE_URL = "http://127.0.0.1:8765"

@pytest.mark.asyncio
async def test_pip_install_and_kernel_restart_integration():
    async with httpx.AsyncClient(timeout=45.0) as client:
        # 1. Login as super_admin who has can_manage_packages permission
        login_res = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "AdminSecurePassword2026!"},
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        session_id = f"test-pip-session-{asyncio.get_event_loop().time()}"

        # 2. Run %pip install rich
        print("\n[STEP 1] Executing %pip install rich...")
        res_pip = await client.post(
            f"{BASE_URL}/api/v1/execution/run",
            json={"session_id": session_id, "code": "%pip install rich"},
            headers=headers,
        )
        assert res_pip.status_code == 200, f"Pip install request failed: {res_pip.text}"
        data_pip = res_pip.json()
        assert data_pip["status"] == "ok"
        print("[STEP 1 SUCCESS] %pip install completed successfully")

        # 3. Test running `from rich import print` right after install
        print("[STEP 2] Executing `from rich import print` in the active kernel...")
        test_code_1 = (
            "from rich import print as rprint\n"
            "rprint('[bold green]Hello from rich[/bold green]')\n"
            "x = 'KERNEL_STATE_SAVED_12345'\n"
            "print('RICH_IMPORT_SUCCESS')"
        )
        res_exec_1 = await client.post(
            f"{BASE_URL}/api/v1/execution/run",
            json={"session_id": session_id, "code": test_code_1},
            headers=headers,
        )
        assert res_exec_1.status_code == 200, f"Exec 1 failed: {res_exec_1.text}"
        data_1 = res_exec_1.json()
        out_text_1 = "".join(o.get("text", "") for o in data_1.get("outputs", []) if o.get("output_type") == "stream")
        assert "RICH_IMPORT_SUCCESS" in out_text_1, f"Expected RICH_IMPORT_SUCCESS but got: {data_1}"
        print("[STEP 2 SUCCESS] `from rich import print` worked in active kernel!")

        # 4. Trigger kernel restart via /execution/control
        print("[STEP 3] Triggering kernel restart via POST /api/v1/execution/control...")
        res_restart = await client.post(
            f"{BASE_URL}/api/v1/execution/control",
            json={"session_id": session_id, "action": "restart"},
            headers=headers,
        )
        assert res_restart.status_code == 200, f"Restart failed: {res_restart.text}"
        assert res_restart.json()["action"] == "restarted"
        print("[STEP 3 SUCCESS] Kernel restart returned HTTP 200 restarted")

        # 5. Verify that in the restarted kernel:
        # - Variable x is reset (NameError)
        # - rich is still importable without ModuleNotFoundError!
        print("[STEP 4] Verifying state reset and rich persistence in restarted kernel...")
        test_code_2 = (
            "try:\n"
            "    print(x)\n"
            "except NameError:\n"
            "    print('VARIABLE_X_IS_RESET')\n"
            "from rich import print as rprint\n"
            "rprint('[bold blue]Rich after restart[/bold blue]')\n"
            "print('RICH_WORKING_AFTER_RESTART')"
        )
        res_exec_2 = await client.post(
            f"{BASE_URL}/api/v1/execution/run",
            json={"session_id": session_id, "code": test_code_2},
            headers=headers,
        )
        assert res_exec_2.status_code == 200, f"Exec 2 failed: {res_exec_2.text}"
        data_2 = res_exec_2.json()
        out_text_2 = "".join(o.get("text", "") for o in data_2.get("outputs", []) if o.get("output_type") == "stream")
        assert "VARIABLE_X_IS_RESET" in out_text_2, f"Variable x was not reset: {data_2}"
        assert "RICH_WORKING_AFTER_RESTART" in out_text_2, f"Rich failed after restart: {data_2}"
        print("[STEP 4 SUCCESS] Variable x was reset, and rich worked flawlessly after restart!")

        # Clean up session
        await client.post(
            f"{BASE_URL}/api/v1/execution/control",
            json={"session_id": session_id, "action": "shutdown"},
            headers=headers,
        )
        print("[ALL STEPS PASSED] Full integration test verified 100%!")
