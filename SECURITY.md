# Enterprise Python Cloud Studio: Security Policy & Threat Model

## 1. Security Philosophy
Untrusted code execution is the core capability of this platform. Therefore, defensive engineering must be applied across every tier:
1. **Never trust client input.** All permissions, limits, and paths are validated server-side.
2. **Never execute user code in the control plane.** API processes never `eval()`, `exec()`, or import untrusted user files.
3. **Defense in Depth**: Container/process isolation, capability dropping, filesystem sandboxing, and network egress filtering.

---

## 2. Threat Model Analysis (STRIDE)

| Threat Category | Potential Vector | Platform Mitigation |
|-----------------|------------------|---------------------|
| **Spoofing** | Forged user identities or token hijacking | Signed JWT tokens with short expiry, cryptographic signature verification, CORS validation, WebSocket connection token verification. |
| **Tampering** | Modifying another tenant's files or notebooks | Tenant-scoped database queries, strict ownership checks, canonical path validation (`os.path.commonpath`) to prevent path traversal (`../`). |
| **Repudiation** | Denying sensitive administrative or sharing actions | Append-only structured audit logs capturing actor, action, resource ID, IP, and timestamp. |
| **Information Disclosure** | Reading cloud metadata, env secrets, or other tenants' memory | Kernel runtimes run without access to control-plane env variables or AWS/GCP metadata endpoints (`169.254.169.254`). Database credentials reside solely in the API container. |
| **Denial of Service** | Fork bombs, memory leaks, runaway loops | Process limits (`pids.max`), memory limits (cgroups), CPU quotas, execution timeouts, idle kernel auto-termination. |
| **Elevation of Privilege** | Container escape, root escalation | Runtimes execute strictly under non-root unprivileged UIDs (`uid 1000`), with `CAP_DROP ALL`, `no-new-privileges:true`. |

---

## 3. Path Traversal & Workspace Isolation
All user file operations (read, write, delete, upload) must verify that the canonical real path is strictly a descendant of the user's allocated workspace directory:

```python
resolved_path = os.path.realpath(requested_path)
if not resolved_path.startswith(os.path.realpath(workspace_root)):
    raise PermissionDenied("Access outside of authorized workspace is prohibited.")
```

---

## 4. Network Security & Egress Filtering
- Kernel containers in production are attached to dedicated isolated bridge networks.
- Internal control plane services (PostgreSQL, Redis, API internal endpoints) are strictly firewalled from runtime networks.
- Egress to public internet is configurable per organization policy.

---

## 5. Security Incident Reporting
Security findings and vulnerabilities should be documented in the vulnerability tracker and resolved before any production deployment gate.

