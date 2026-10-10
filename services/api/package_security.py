import os
import re
import ast
from typing import Tuple, Optional, Dict, Any, Union
from dotenv import dotenv_values

# Dangerous OS-level package managers and privilege escalation commands
BLOCKED_SYSTEM_COMMANDS = re.compile(
    r"""(?:^\s*!(?:sudo|apt|apt-get|yum|apk|pacman|brew|dnf|rpm|dpkg|curl\s+.*\|\s*(?:ba)?sh|wget\s+.*\|\s*(?:ba)?sh|sh\s+-c|bash\s+-c)|(?:os\.system|subprocess\.(?:run|Popen|call|check_call|check_output))\s*\(\s*\[?\s*['"].*?\b(?:sudo|apt|apt-get|yum|apk|pacman|brew|dnf|reboot|shutdown))""",
    re.MULTILINE | re.IGNORECASE
)

# Package installation patterns in notebook cells (magics, bang commands, python invocation)
PIP_MAGIC_PATTERN = re.compile(
    r"^\s*(?:%pip|!pip|!pip3|%pip3|!python\s+-m\s+pip)\s+(install|uninstall|download)",
    re.MULTILINE | re.IGNORECASE
)

# Subprocess or os.system invocation of pip
SUBPROCESS_PIP_PATTERN = re.compile(
    r"""(?:(?:subprocess|__import__\(['"]subprocess['"]\))\.(?:run|Popen|call|check_call|check_output)\s*\(\s*\[?\s*['"](?:pip|pip3|python)['"]|os\.system\s*\(\s*['"].*?\bpip\s+install)""",
    re.IGNORECASE
)

# Server-level secret environment keys that must NEVER leak to user kernels
SENSITIVE_SERVER_KEYS = {
    "SECRET_KEY",
    "ADMIN_BOOTSTRAP_PASSWORD",
    "ADMIN_BOOTSTRAP_EMAIL",
    "DATABASE_URL",
    "ALGORITHM",
    "JWT_SECRET",
    "POSTGRES_PASSWORD",
    "PGPASSWORD",
    "REDIS_PASSWORD",
}


# Cross-workspace path traversal patterns targeting private directories of other users
CROSS_WORKSPACE_TRAVERSAL_PATTERN = re.compile(
    r"""(?:\.\.[/\\]+user_|\.\.[/\\]+storage[/\\]workspaces[/\\]user_|user_admin_super|storage[/\\]workspaces[/\\]user_|[/\\]workspaces[/\\]user_[a-zA-Z0-9_\-]+)""",
    re.IGNORECASE
)


def validate_code_security(code: str, user: Any) -> Tuple[bool, Optional[str], str]:
    """
    Inspects Python code for package installation and OS modification attempts.
    Enforces role and permission checks:
      - Guests are unconditionally blocked from installing packages or running OS tools.
      - Authenticated users without can_manage_packages are blocked.
      - Authorized users have pip install automatically isolated with --user.
      - Non-superadmin users are strictly prevented from cross-workspace traversal.

    Returns:
      (is_allowed: bool, error_message: Optional[str], transformed_code: str)
    """
    is_guest = getattr(user, "is_guest", False) or getattr(user, "id", "") in ("public", "public_guest")
    role = getattr(user, "role", "student")
    can_manage = getattr(user, "can_manage_packages", False) or role in ("admin", "super_admin")
    is_super_admin = role == "super_admin"

    # 1. Block unauthorized cross-workspace traversal targeting other users' private workspaces
    if not is_super_admin and CROSS_WORKSPACE_TRAVERSAL_PATTERN.search(code):
        return (
            False,
            "Security Violation: Accessing other users' private workspaces or cross-workspace paths is strictly prohibited.",
            code,
        )

    # 2. Block unauthorized OS commands and privilege escalation
    if BLOCKED_SYSTEM_COMMANDS.search(code):
        return (
            False,
            "Security Violation: Operating system commands and package managers (apt, yum, sudo, etc.) are strictly prohibited. The host system is protected.",
            code,
        )

    # 3. Check for pip installation attempts
    has_pip_magic = bool(PIP_MAGIC_PATTERN.search(code))
    has_pip_subprocess = bool(SUBPROCESS_PIP_PATTERN.search(code))

    if has_pip_magic or has_pip_subprocess:
        if is_guest:
            return (
                False,
                "Permission Denied: Guest users are strictly prohibited from installing packages or modifying runtime environments. Please sign in with an authorized account.",
                code,
            )

        if not can_manage:
            return (
                False,
                "Permission Denied: Package installation is disabled for your account. Please contact an administrator to request package installation privileges.",
                code,
            )

        # Authorized user: Ensure user environment isolation
        # If running %pip install or !pip install, automatically ensure --user or isolated target
        transformed_code = code
        for line in code.split("\n"):
            if PIP_MAGIC_PATTERN.match(line) and "install" in line.lower() and "--user" not in line and "--target" not in line:
                # Add --user to install inside the user's isolated workspace environment
                isolated_line = line.strip() + " --user"
                transformed_code = transformed_code.replace(line, isolated_line)

        return (True, None, transformed_code)

    return (True, None, code)


def get_sanitized_kernel_env(workspace_dir: str, user_id: str, is_admin: bool = False) -> Dict[str, str]:
    """
    Constructs a sanitized, isolated process environment for the IPyKernel.
    - Strips all server secrets, database URLs, and admin credentials.
    - Configures PYTHONUSERBASE to the user's isolated workspace directory.
    - Pre-creates and configures user site-packages in PYTHONPATH so pip packages are immediately discoverable.
    - Injects runtime security guard (sitecustomize.py) for workspace boundary enforcement.
    - Safely loads workspace-specific .env variables for the user.
    """
    import sys
    clean_env: Dict[str, str] = {}

    # 1. Inherit only safe system variables
    safe_keys = {
        "PATH", "SYSTEMROOT", "SYSTEMDRIVE", "TEMP", "TMP", "USERPROFILE",
        "HOMEDRIVE", "HOMEPATH", "HOME", "LANG", "LC_ALL", "COMSPEC", "PATHEXT",
        "WINDIR", "TERM", "ALLUSERSPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA",
        "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "OS",
    }
    for k, v in os.environ.items():
        if k.upper() in safe_keys and k not in SENSITIVE_SERVER_KEYS:
            clean_env[k] = v

    # 2. Configure isolated user package repository (PYTHONUSERBASE)
    local_dir = os.path.join(os.path.abspath(workspace_dir), ".local")
    os.makedirs(local_dir, exist_ok=True)
    clean_env["PYTHONUSERBASE"] = local_dir
    clean_env["PYTHON_CLOUD_STUDIO_USER"] = str(user_id)
    clean_env["PYTHON_CLOUD_STUDIO_USER_ID"] = str(user_id)
    clean_env["PYTHON_CLOUD_STUDIO_WORKSPACE"] = os.path.abspath(workspace_dir)
    clean_env["PYTHON_CLOUD_STUDIO_IS_ADMIN"] = (
        "1" if (is_admin or user_id in ("admin_super", "user_admin_super")) else "0"
    )

    # Pre-create user site-packages directory so Python's site.py activates it on boot
    major = sys.version_info.major
    minor = sys.version_info.minor
    if sys.platform == "win32":
        user_site = os.path.join(local_dir, f"Python{major}{minor}", "site-packages")
    else:
        user_site = os.path.join(local_dir, "lib", f"python{major}.{minor}", "site-packages")
    os.makedirs(user_site, exist_ok=True)

    # 3. Configure PYTHONPATH to include runtime guards, user workspace, and isolated site-packages
    python_paths = []

    # Runtime security guards
    guards_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "runtime_management", "runtime_guards")
    )
    if os.path.exists(guards_dir):
        python_paths.append(guards_dir)

    python_paths.extend([os.path.abspath(workspace_dir), user_site])

    # Also discover any existing site-packages directories under user's own .local
    if os.path.exists(local_dir):
        for root, dirs, _ in os.walk(local_dir):
            if os.path.basename(root) == "site-packages" and root not in python_paths:
                python_paths.append(root)

    # Discover shared public workspace libraries (never leak other private user_* workspaces)
    workspaces_root = os.path.dirname(os.path.abspath(workspace_dir))
    if os.path.basename(workspaces_root) != "workspaces":
        parent = os.path.dirname(workspaces_root)
        if os.path.basename(parent) == "workspaces":
            workspaces_root = parent
    if os.path.basename(workspaces_root) == "workspaces" and os.path.exists(workspaces_root):
        public_site = os.path.join(workspaces_root, "public", ".local")
        if os.path.exists(public_site) and public_site != local_dir:
            for root, dirs, _ in os.walk(public_site):
                if os.path.basename(root) == "site-packages" and root not in python_paths:
                    python_paths.append(root)

    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    if existing_pythonpath:
        for p in existing_pythonpath.split(os.pathsep):
            if p and p not in python_paths:
                python_paths.append(p)

    clean_env["PYTHONPATH"] = os.pathsep.join(python_paths)

    # 4. Safely inject user workspace .env variables (if present)
    user_env_file = os.path.join(workspace_dir, ".env")
    if os.path.exists(user_env_file):
        try:
            user_vars = dotenv_values(user_env_file)
            for key, val in user_vars.items():
                if key and val and key not in SENSITIVE_SERVER_KEYS:
                    clean_env[key] = str(val)
        except Exception as e:
            print(f"Warning: Failed to load user workspace .env: {e}")

    return clean_env
