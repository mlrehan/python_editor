import pytest
import json
import uuid
from httpx import AsyncClient, ASGITransport
from services.api.main import app
from services.api.database import init_db

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="function")
async def client():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


async def test_api_health(client):
    """Verifies health check endpoint."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "active_kernels" in data


async def test_32_to_37_multi_user_auth_and_isolation(client):
    """TEST 32-37: Multi-user authentication, JWT generation, and notebook isolation."""
    uid = uuid.uuid4().hex[:8]
    # 1. Register Student A
    res_a = await client.post("/api/v1/auth/register", json={
        "email": f"student_a_{uid}@example.com",
        "password": "Password123!",
        "full_name": "Student Alpha",
        "role": "student"
    })
    assert res_a.status_code == 200, res_a.text
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register Student B
    res_b = await client.post("/api/v1/auth/register", json={
        "email": f"student_b_{uid}@example.com",
        "password": "Password123!",
        "full_name": "Student Beta",
        "role": "student"
    })
    assert res_b.status_code == 200, res_b.text
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Student A creates a private notebook
    nb_res = await client.post("/api/v1/notebooks", json={
        "title": "Alpha Private Research",
        "kernel_name": "python3"
    }, headers=headers_a)
    assert nb_res.status_code == 200
    nb_id = nb_res.json()["id"]

    # 4. Student B tries to access Student A's notebook -> MUST BE 404/FORBIDDEN
    forbidden_res = await client.get(f"/api/v1/notebooks/{nb_id}", headers=headers_b)
    assert forbidden_res.status_code == 404

    # 5. Anonymous request without token -> MUST BE 401 UNAUTHORIZED
    unauth_res = await client.get(f"/api/v1/notebooks/{nb_id}")
    assert unauth_res.status_code == 401


async def test_16_to_22_notebook_crud_and_ipynb_export(client):
    """TEST 16-22: Create, read, update, export, and delete notebook."""
    uid = uuid.uuid4().hex[:8]
    # Register author
    res = await client.post("/api/v1/auth/register", json={
        "email": f"author_{uid}@example.com",
        "password": "Password123!",
        "full_name": "Notebook Author",
        "role": "student"
    })
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create notebook
    create_res = await client.post("/api/v1/notebooks", json={
        "title": "Machine Learning Lab 01",
        "kernel_name": "python3"
    }, headers=headers)
    assert create_res.status_code == 200
    nb_data = create_res.json()
    nb_id = nb_data["id"]
    assert nb_data["title"] == "Machine Learning Lab 01"
    assert "cells" in nb_data["content"]

    # Update notebook content
    updated_content = nb_data["content"]
    updated_content["cells"].append({
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "source": "import numpy as np\nprint(np.pi)",
        "outputs": []
    })
    put_res = await client.put(f"/api/v1/notebooks/{nb_id}", json={
        "title": "Machine Learning Lab 01 (Revised)",
        "content": updated_content
    }, headers=headers)
    assert put_res.status_code == 200
    assert put_res.json()["title"] == "Machine Learning Lab 01 (Revised)"

    # Export .ipynb
    export_res = await client.get(f"/api/v1/notebooks/{nb_id}/export", headers=headers)
    assert export_res.status_code == 200
    assert export_res.headers["content-type"] == "application/x-ipynb+json"
    exported_nb = json.loads(export_res.text)
    assert exported_nb["nbformat"] == 4

    # Delete notebook
    del_res = await client.delete(f"/api/v1/notebooks/{nb_id}", headers=headers)
    assert del_res.status_code == 204

    # Confirm deletion
    get_res = await client.get(f"/api/v1/notebooks/{nb_id}", headers=headers)
    assert get_res.status_code == 404


async def test_39_deny_workspace_path_traversal(client):
    """TEST 39: Security test verifying that path traversal (../) is rejected."""
    uid = uuid.uuid4().hex[:8]
    res = await client.post("/api/v1/auth/register", json={
        "email": f"security_tester_{uid}@example.com",
        "password": "Password123!",
        "full_name": "Security Tester",
        "role": "student"
    })
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to read outside workspace root using directory traversal
    attack_res = await client.get("/api/v1/files/read?path=../../etc/passwd", headers=headers)
    assert attack_res.status_code in (403, 404)


async def test_48_to_51_classroom_and_assignment_workflow(client):
    """TEST 48-51: Classroom assignment distribution, student submission snapshot, and instructor review."""
    uid = uuid.uuid4().hex[:8]
    # 1. Register instructor
    inst_res = await client.post("/api/v1/auth/register", json={
        "email": f"instructor_{uid}@example.com",
        "password": "Password123!",
        "full_name": "Professor Jane",
        "role": "instructor"
    })
    assert inst_res.status_code == 200, inst_res.text
    inst_token = inst_res.json()["access_token"]
    inst_headers = {"Authorization": f"Bearer {inst_token}"}

    # 2. Register student
    stud_res = await client.post("/api/v1/auth/register", json={
        "email": f"student_{uid}@example.com",
        "password": "Password123!",
        "full_name": "Bob Student",
        "role": "student"
    })
    assert stud_res.status_code == 200, stud_res.text
    stud_token = stud_res.json()["access_token"]
    stud_headers = {"Authorization": f"Bearer {stud_token}"}

    # 3. Instructor creates classroom
    class_res = await client.post("/api/v1/classrooms", json={
        "name": "Data Science 101",
        "description": "Introduction to Python & Data Analysis"
    }, headers=inst_headers)
    assert class_res.status_code == 200
    classroom = class_res.json()
    classroom_id = classroom["id"]
    join_code = classroom["join_code"]

    # 4. Student joins classroom using join_code
    join_res = await client.post(f"/api/v1/classrooms/join/{join_code}", headers=stud_headers)
    assert join_res.status_code == 200
    assert join_res.json()["status"] == "enrolled"

    # 5. Instructor creates assignment
    assign_res = await client.post("/api/v1/classrooms/assignments", json={
        "classroom_id": classroom_id,
        "title": "Assignment 1: NumPy Computations",
        "description": "Compute mean and standard deviation of provided array.",
        "template_notebook": {
            "nbformat": 4,
            "nbformat_minor": 5,
            "cells": [{"cell_type": "code", "source": "# Solution here\n", "metadata": {}, "outputs": []}],
            "metadata": {}
        }
    }, headers=inst_headers)
    assert assign_res.status_code == 200
    assignment_id = assign_res.json()["id"]

    # 6. Student submits completed notebook snapshot
    sub_res = await client.post("/api/v1/classrooms/submissions", json={
        "assignment_id": assignment_id,
        "notebook_content": {
            "nbformat": 4,
            "nbformat_minor": 5,
            "cells": [{"cell_type": "code", "source": "import numpy as np\nres = np.mean([10, 20, 30])\nprint(res)", "metadata": {}, "outputs": [{"output_type": "stream", "text": "20.0\n"}]}],
            "metadata": {}
        }
    }, headers=stud_headers)
    assert sub_res.status_code == 200
    submission_id = sub_res.json()["id"]
    assert sub_res.json()["status"] == "submitted"

    # 7. Instructor reviews submission and grades
    grade_res = await client.put(
        f"/api/v1/classrooms/submissions/{submission_id}/review?grade=95.0&feedback=Great+job+on+vectorization",
        headers=inst_headers
    )
    assert grade_res.status_code == 200
    assert grade_res.json()["grade"] == 95.0


async def test_api_code_execution_endpoint(client):
    """Verifies executing real Python code through POST /api/v1/execution/run."""
    uid = uuid.uuid4().hex[:8]
    # Register user
    res = await client.post("/api/v1/auth/register", json={
        "email": f"runner_{uid}@example.com",
        "password": "Password123!",
        "full_name": "Execution Runner",
        "role": "student"
    })
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Execute Python calculation
    exec_res = await client.post("/api/v1/execution/run", json={
        "session_id": f"test-api-session-{uid}",
        "code": "x = 42\nprint('Calculated:', x * 2)",
        "timeout": 20.0
    }, headers=headers)

    assert exec_res.status_code == 200
    data = exec_res.json()
    assert data["status"] == "ok"
    assert data["execution_count"] is not None
    stdout_text = "".join(o["text"] for o in data["outputs"] if o["output_type"] == "stream")
    assert "Calculated: 84" in stdout_text
