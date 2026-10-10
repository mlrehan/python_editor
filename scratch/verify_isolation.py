import asyncio
import httpx
import os
import sys

BASE_URL = "http://127.0.0.1:8765/api/v1"

async def test_backend_isolation():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        print("=== 1. TEST GUEST MODE FILE ISOLATION ===")
        # Guest session
        guest_res = await client.post("/auth/guest-session")
        guest_token = guest_res.json().get("guest_token")
        guest_headers = {"X-Guest-Token": guest_token}

        # List files as guest
        files_res = await client.get("/files", headers=guest_headers)
        guest_files = [f["name"] for f in files_res.json()]
        print("Guest files visible:", guest_files)
        assert "Sales Dataset.csv" not in guest_files, "LEAK! Sales Dataset.csv visible to Guest!"
        print("[PASS] Sales Dataset.csv is NOT visible to Guest.")

        # Guest direct read
        read_res = await client.get("/files/read?path=Sales Dataset.csv", headers=guest_headers)
        assert read_res.status_code == 404, f"Expected 404, got {read_res.status_code}"
        print("[PASS] Direct read of Sales Dataset.csv returns 404 for Guest.")

        # Guest path traversal read
        trav_res = await client.get("/files/read?path=../user_admin_super/default/Sales Dataset.csv", headers=guest_headers)
        assert trav_res.status_code == 403, f"Expected 403, got {trav_res.status_code}"
        print("[PASS] Path traversal read returns 403 Forbidden for Guest.")

        print("\n=== 2. TEST SUPERADMIN AUTHENTICATION & ACCESS ===")
        # Login as SuperAdmin
        # First check admin bootstrap password from config/env
        from services.api.config import settings
        admin_email = settings.ADMIN_BOOTSTRAP_EMAIL
        admin_pass = settings.ADMIN_BOOTSTRAP_PASSWORD

        login_res = await client.post("/auth/login", json={"email": admin_email, "password": admin_pass})
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        admin_token = login_res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print(f"[PASS] Logged in as SuperAdmin ({admin_email})")

        # SuperAdmin lists files
        admin_files_res = await client.get("/files", headers=admin_headers)
        admin_files = [f["name"] for f in admin_files_res.json()]
        print("SuperAdmin files visible:", admin_files)
        assert "Sales Dataset.csv" in admin_files, "Sales Dataset.csv should be visible to SuperAdmin!"
        print("[PASS] Sales Dataset.csv is correctly visible in SuperAdmin private workspace.")

        # SuperAdmin reads file
        admin_read = await client.get("/files/read?path=Sales Dataset.csv", headers=admin_headers)
        assert admin_read.status_code == 200, f"Expected 200, got {admin_read.status_code}"
        assert len(admin_read.json().get("content", "")) > 1000, "Content should be non-empty"
        print(f"[PASS] SuperAdmin successfully read Sales Dataset.csv ({len(admin_read.json().get('content', ''))} chars).")

        print("\n=== 3. TEST REGULAR USER (STUDENT) ISOLATION ===")
        # Register fresh student
        student_email = f"student_{int(asyncio.get_event_loop().time() * 1000)}@example.com"
        reg_res = await client.post("/auth/register", json={
            "email": student_email,
            "password": "Password123!",
            "full_name": "Test Student",
            "role": "student"
        })
        assert reg_res.status_code == 200, f"Register failed: {reg_res.text}"
        student_token = reg_res.json()["access_token"]
        student_headers = {"Authorization": f"Bearer {student_token}"}
        print(f"[PASS] Registered & logged in new Student: {student_email}")

        # Student lists files
        student_files_res = await client.get("/files", headers=student_headers)
        student_files = [f["name"] for f in student_files_res.json()]
        print("Student files visible:", student_files)
        assert "Sales Dataset.csv" not in student_files, "LEAK! Sales Dataset.csv visible to Student!"
        print("[PASS] Sales Dataset.csv is NOT visible to Student.")

        # Student path traversal
        student_trav = await client.get("/files/read?path=../user_admin_super/default/Sales Dataset.csv", headers=student_headers)
        assert student_trav.status_code == 403, f"Expected 403, got {student_trav.status_code}"
        print("[PASS] Path traversal read returns 403 Forbidden for Student.")

        print("\n=== 4. TEST PYTHON CODE EXECUTION TRAVERSAL PREVENTION ===")
        # A. Static traversal check via REST execution for Guest
        guest_exec_static = await client.post("/execution/run", json={
            "session_id": "test-sec-guest-1",
            "code": "with open('../user_admin_super/default/Sales Dataset.csv') as f: print(f.read())"
        }, headers=guest_headers)
        res_data = guest_exec_static.json()
        print("Guest static traversal execution result:", res_data.get("status"), res_data.get("outputs", [{}])[0].get("ename"))
        assert res_data.get("status") == "error"
        assert res_data.get("outputs", [{}])[0].get("ename") == "SecurityError"
        print("[PASS] Guest static traversal blocked with SecurityError.")

        # B. Static traversal check for Student
        student_exec_static = await client.post("/execution/run", json={
            "session_id": "test-sec-student-1",
            "code": "import os; print(os.listdir('../user_admin_super'))"
        }, headers=student_headers)
        s_data = student_exec_static.json()
        print("Student static traversal execution result:", s_data.get("status"), s_data.get("outputs", [{}])[0].get("ename"))
        assert s_data.get("status") == "error"
        assert s_data.get("outputs", [{}])[0].get("ename") == "SecurityError"
        print("[PASS] Student static traversal blocked with SecurityError.")

        # C. Runtime guard check via dynamic path construction
        # Guest dynamic path execution (obfuscated so static regex doesn't catch, testing runtime guard)
        guest_exec_dynamic = await client.post("/execution/run", json={
            "session_id": "test-sec-guest-dynamic-guard",
            "code": "p = ''.join([chr(46), chr(46), '/', 'user', '_admin', '_super', '/default/Sales Dataset.csv'])\ntry:\n    with open(p) as f:\n        print('LEAK:', f.read())\nexcept PermissionError as e:\n    print('RUNTIME_GUARD_CAUGHT:', str(e))\nexcept Exception as e:\n    print('OTHER_ERR:', str(e))"
        }, headers=guest_headers)
        dyn_data = guest_exec_dynamic.json()
        out_text = "".join([o.get("text", "") for o in dyn_data.get("outputs", [])])
        print("Guest dynamic traversal execution stdout:", out_text.strip())
        assert "RUNTIME_GUARD_CAUGHT: Permission Denied" in out_text, f"Expected runtime guard catch, got: {out_text}"
        print("[PASS] Guest dynamic path traversal caught and blocked by sitecustomize.py runtime guard!")

        # D. SuperAdmin authorized code execution accessing their own file
        admin_exec = await client.post("/execution/run", json={
            "session_id": "test-sec-admin-1",
            "code": "with open('Sales Dataset.csv') as f: print('ADMIN_READ_CHARS:', len(f.read()))"
        }, headers=admin_headers)
        admin_data = admin_exec.json()
        admin_out = "".join([o.get("text", "") for o in admin_data.get("outputs", [])])
        print("Admin execution stdout:", admin_out.strip())
        assert "ADMIN_READ_CHARS:" in admin_out, f"Expected admin read, got: {admin_out}"
        print("[PASS] SuperAdmin successfully executed code reading Sales Dataset.csv.")

        print("\n=== ALL BACKEND & PYTHON CODE SECURITY ISOLATION TESTS PASSED! ===")

if __name__ == "__main__":
    asyncio.run(test_backend_isolation())
