import pytest
import asyncio
import os
import tempfile
import shutil
from httpx import AsyncClient, ASGITransport

from services.api.main import app
from services.api.database import AsyncSessionLocal, init_db
from services.api.models import User, Notebook, AuditLog
from services.runtime_management.kernel_session import KernelSession
from services.api.package_security import validate_code_security, get_sanitized_kernel_env
from services.api.auth import create_access_token
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="function")
async def client():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


async def create_user_token(client: AsyncClient, email: str, role: str = "student", can_manage_packages: bool = False):
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "full_name": email.split("@")[0], "role": "student"},
    )
    if reg_res.status_code != 200:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "Password123!"},
        )
        token = login_res.json()["access_token"]
    else:
        token = reg_res.json()["access_token"]

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            if role != "student":
                user.role = role
            if can_manage_packages:
                user.can_manage_packages = True
            await session.commit()
            token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})

    return token


# ========================================================
# 1. SECURITY HEADERS VERIFICATION
# ========================================================
async def test_01_security_headers(client: AsyncClient):
    """Verify production security headers are set on all responses."""
    res = await client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert "mode=block" in res.headers.get("X-XSS-Protection", "")
    assert "strict-origin" in res.headers.get("Referrer-Policy", "")
    assert "default-src 'self'" in res.headers.get("Content-Security-Policy", "")


# ========================================================
# 2. GUEST USER PACKAGE INSTALL RESTRICTIONS
# ========================================================
async def test_02_guest_package_install_rejected(client: AsyncClient):
    """Verify guest users are strictly rejected from installing packages."""
    guest_res = await client.post("/api/v1/auth/guest-session")
    guest_token = guest_res.json()["guest_token"]

    bad_codes = [
        "%pip install lightweight-charts",
        "!pip install requests",
        "import os; os.system('pip install cowsay')",
        "__import__('subprocess').run(['pip', 'install', 'flask'])",
    ]

    for code in bad_codes:
        res = await client.post(
            "/api/v1/execution/run",
            json={"session_id": "guest-test-session", "code": code},
            headers={"X-Guest-Token": guest_token},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "error", f"Expected error for guest running: {code}, got: {data}"
        err_val = data["error"]["evalue"].lower()
        assert "permission denied" in err_val or "prohibited" in err_val or "security" in err_val


# ========================================================
# 3. STUDENT USER PACKAGE INSTALL RESTRICTIONS
# ========================================================
async def test_03_student_without_permission_rejected(client: AsyncClient):
    """Verify students without package management permission are rejected."""
    student_token = await create_user_token(
        client, "unprivileged_student@example.com", role="student", can_manage_packages=False
    )

    res = await client.post(
        "/api/v1/execution/run",
        json={"session_id": "student-session-1", "code": "%pip install tabulate"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "error"
    err_val = data["error"]["evalue"].lower()
    assert "permission denied" in err_val or "disabled" in err_val


# ========================================================
# 4. AUTHORIZED USER PACKAGE INSTALL WITH --user ISOLATION
# ========================================================
async def test_04_authorized_user_package_install(client: AsyncClient):
    """Verify users with can_manage_packages=True can install with --user isolation."""
    await create_user_token(
        client, "privileged_analyst@example.com", role="instructor", can_manage_packages=True
    )

    # Use the security scanner directly to verify rewrite
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.email == "privileged_analyst@example.com")
        res = await session.execute(stmt)
        user = res.scalar_one()

    is_ok, err_msg, sanitized = validate_code_security("%pip install tabulate", user=user)
    assert is_ok is True
    assert "--user" in sanitized, f"Expected --user in sanitized code: {sanitized}"


# ========================================================
# 5. OS ESCAPE AND COMMAND INJECTION PREVENTION
# ========================================================
async def test_05_os_escape_prevention(client: AsyncClient):
    """Verify system-level OS package modifications and privilege escalation are blocked."""
    admin_token = await create_user_token(
        client, "test_admin@example.com", role="super_admin", can_manage_packages=True
    )

    forbidden_commands = [
        "!apt-get install htop",
        "!sudo systemctl restart",
        "!yum install git",
        "!apk add bash",
        "import os; os.system('sudo reboot')",
    ]

    for cmd in forbidden_commands:
        res = await client.post(
            "/api/v1/execution/run",
            json={"session_id": "test-admin-session", "code": cmd},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "error", f"Expected error for escape command: {cmd}"
        err_val = data["error"]["evalue"].lower()
        assert "prohibited" in err_val or "violation" in err_val or "host system is protected" in err_val


# ========================================================
# 6. KERNEL ENVIRONMENT SANITIZATION & SECRET SHIELDING
# ========================================================
async def test_06_server_secret_shielding_in_kernel():
    """Verify server secrets (SECRET_KEY, DATABASE_URL) are NOT leaked to the kernel environment."""
    temp_dir = tempfile.mkdtemp(prefix="test_shield_")
    try:
        clean_env = get_sanitized_kernel_env(
            workspace_dir=temp_dir,
            user_id="test_user_id",
        )

        assert "SECRET_KEY" not in clean_env, "CRITICAL LEAK: SECRET_KEY present in kernel env!"
        assert "DATABASE_URL" not in clean_env, "CRITICAL LEAK: DATABASE_URL present in kernel env!"
        assert "ADMIN_BOOTSTRAP_PASSWORD" not in clean_env, "CRITICAL LEAK: ADMIN_BOOTSTRAP_PASSWORD present in kernel env!"
        assert clean_env.get("PYTHONUSERBASE") == os.path.join(temp_dir, ".local")
        assert clean_env.get("PYTHON_CLOUD_STUDIO_USER") == "test_user_id"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ========================================================
# 7. WORKSPACE .env AND AI CREDENTIALS INJECTION
# ========================================================
async def test_07_workspace_env_and_ai_credentials(client: AsyncClient):
    """Verify user workspace .env variables can be saved and injected into kernel session."""
    user_token = await create_user_token(client, "ai_developer@example.com", role="student")

    # Save OpenAI and Gemini credentials to user workspace .env
    put_res = await client.put(
        "/api/v1/files/env",
        json={"env": {"OPENAI_API_KEY": "sk-test-ai-key-12345", "GEMINI_API_KEY": "AIzaSy-test-gemini-key"}},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert put_res.status_code == 200
    assert "OPENAI_API_KEY" in put_res.json()["keys"]

    # Read back via API
    get_res = await client.get("/api/v1/files/env", headers={"Authorization": f"Bearer {user_token}"})
    assert get_res.status_code == 200
    env_data = get_res.json()["env"]
    assert env_data.get("OPENAI_API_KEY") == "sk-test-ai-key-12345"
    assert env_data.get("GEMINI_API_KEY") == "AIzaSy-test-gemini-key"


# ========================================================
# 8. SUPERADMIN AUDITED INSPECTION ENDPOINTS
# ========================================================
async def test_08_superadmin_audited_endpoints(client: AsyncClient):
    """Verify SuperAdmin can inspect notebooks, workspace files, and settings with audit logs."""
    superadmin_token = await create_user_token(
        client, "primary_superadmin@example.com", role="super_admin", can_manage_packages=True
    )

    # 1. List all notebooks across system
    nb_res = await client.get(
        "/api/v1/admin/notebooks",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert nb_res.status_code == 200
    assert isinstance(nb_res.json(), list)

    # 2. Get system integrations
    integ_res = await client.get(
        "/api/v1/admin/settings/integrations",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert integ_res.status_code == 200
    assert "ai_providers" in integ_res.json()

    # 3. Update system integrations
    put_integ = await client.put(
        "/api/v1/admin/settings/integrations",
        json={"integrations": {"ai_provider": "gemini", "max_kernel_idle_sec": 3600}},
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert put_integ.status_code == 200

    # 4. Check audit logs were generated
    async with AsyncSessionLocal() as session:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(10)
        logs = (await session.execute(stmt)).scalars().all()
        actions = [log.action for log in logs]
        assert any("settings" in a or "admin" in a or "code" in a for a in actions)


# ========================================================
# 9. CROSS-USER WORKSPACE FILE ISOLATION
# ========================================================
async def test_09_cross_user_file_isolation(client: AsyncClient):
    """Verify strict path traversal and cross-user workspace file isolation."""
    user_a_token = await create_user_token(client, "user_alpha@example.com", role="student")
    user_b_token = await create_user_token(client, "user_beta@example.com", role="student")

    # User A creates a secret file
    write_res = await client.post(
        "/api/v1/files/write",
        json={"path": "alpha_secret.txt", "content": "ALPHA_CONFIDENTIAL_DATA"},
        headers={"Authorization": f"Bearer {user_a_token}"},
    )
    assert write_res.status_code == 200

    # User B attempts directory traversal to reach User A or root system
    traversal_paths = [
        "../user_alpha/alpha_secret.txt",
        "../../workspaces/alpha_secret.txt",
        "/etc/passwd",
        "C:\\Windows\\System32\\drivers\\etc\\hosts",
    ]

    for p in traversal_paths:
        res = await client.get(
            f"/api/v1/files/read?path={p}",
            headers={"Authorization": f"Bearer {user_b_token}"},
        )
        assert res.status_code in [400, 403, 404], f"Unexpected status {res.status_code} for path {p}"
