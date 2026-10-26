# Projects Workspace & 100-User Scale Plan

Status: **Phase 0 code complete (not deployed); Phase 1+ awaiting server specs** · Written 2026-10-26 · Covers: VS Code–style projects, running 100 concurrent users safely on one Docker host.

Requirements agreed with the product owner:
- Long-term goal is a VS Code–like IDE next to the notebook.
- Projects are **private and require login**. No code is shared between users.
- Deployment is **Docker on the existing Linux server** (host nginx in front, possibly Cloudflare).
- Up to **100 users may be editing and executing code at the same time**.

---

## 1. Why the current design cannot serve 100 users

Measured on the dev machine (one IPyKernel process):

| State | Memory (RSS) | Threads |
|---|---|---|
| Idle kernel | ~60 MB | 19 |
| After `import numpy, pandas, matplotlib` | ~140 MB | 20 |
| Holding a 200k × 10 DataFrame | ~155 MB | 20 |

How the code and compose file use that today:

| Fact | Where | Effect |
|---|---|---|
| Every user's kernels run **inside the API container** | `kernel_pool.py`, `docker-compose.yml` | One container's limits are shared by everyone |
| API container limit: **2 GB RAM, 1.5 CPU, 300 PIDs** | `docker-compose.yml` `deploy.resources` | ~12–14 kernels with pandas loaded before OOM or PID exhaustion; then kernels fail to start, or the whole container is killed and every user is disconnected |
| One kernel **per notebook opened**, never shut down | `App.tsx` session id includes notebook id | Kernels accumulate as users switch notebooks |
| Idle reaper exists but **is never called** | `KernelPoolManager.reap_idle_sessions` | Kernels live until the server restarts |
| Guests get their own kernel per browser, **no global cap** | `websockets.py`, `kernel_pool.py` | Anonymous visitors can exhaust the host |
| Kernel registry is an **in-memory dict** in one uvicorn process | `kernel_pool.py` | Cannot add workers; an API restart orphans every kernel |
| User code runs as the **same OS user as the API** (root in Docker), no sandbox | `Dockerfile.api`, `sitecustomize.py` | Any user can read server secrets, the DB credentials and other users' files; one user can starve everyone |

The production screenshot ("Python 3 (Disconnected)" followed by a failed execution with an empty error) matches container resource exhaustion or a container restart. **To confirm**, run on the server:

```bash
docker inspect pcs-api --format 'restarts={{.RestartCount}} oom={{.State.OOMKilled}} started={{.State.StartedAt}}'
docker stats --no-stream pcs-api
docker logs pcs-api --since 6h 2>&1 | grep -iE "error|killed|resource|thread|memory" | tail -50
sudo tail -100 /var/log/nginx/python_cloud_studio_error.log
```

---

## 2. Target architecture

```
Browser ──HTTPS/WSS──> host nginx ──> API container (control plane, no user code)
                                         │  Docker API (via a restricted socket proxy)
                                         ▼
                        ┌─ runtime container: user A ─┐  ┌─ runtime container: user B ─┐
                        │ runtime agent (WS/HTTP)      │  │ ...                          │
                        │  • IPyKernels (notebooks)    │  │                              │
                        │  • project processes (run)   │  │                              │
                        │  • terminal PTYs             │  │                              │
                        │ /workspace = user's volume   │  │                              │
                        └──────────────────────────────┘  └──────────────────────────────┘
                          isolated "runtimes" network: no route to postgres/redis/API internals
```

**Control plane (existing FastAPI app)** keeps auth, files metadata, notebooks, projects, admin. It never executes user code. It proxies browser WebSockets to the user's runtime agent after checking ownership.

**One runtime container per signed-in user**, started on first use and stopped after an idle period:
- Image: `Dockerfile.runtime` extended with the data-science baseline and a small runtime agent.
- Hardening: non-root UID, `--cap-drop ALL`, `no-new-privileges`, read-only root filesystem with writable `/workspace` and `/tmp`, default seccomp profile, no Docker socket.
- Per-user limits (proposed defaults, configurable by admin): **1 GB RAM, 1 CPU, 256 PIDs, 5 GB disk quota**.
- Network: attached only to a dedicated runtime network that cannot reach postgres, redis or the API's internal ports. Outbound internet allowed (needed for `pip install`), metadata/private ranges blocked.
- Only that user's workspace volume is mounted, so cross-tenant file access is impossible by construction (this replaces the bypassable `sitecustomize.py` guard and the regex filters).

**Runtime agent** (inside each container): starts/stops kernels, runs project processes, hosts PTYs, streams output. The control plane talks to it over the private network with a per-container secret.

**State that must survive API restarts** (container id, agent address, kernel ids) moves from the in-memory dict to the database/redis, so the API can restart or run several workers without killing user sessions.

**Guests**: keep anonymous notebook use only if required, in a separate small pool of short-lived, tightly limited containers (e.g. 256 MB, 0.25 CPU, 10 min idle) with a global cap. Projects stay login-only.

### Capacity sizing (needs your server specs)
Typical active user: one kernel or one project process, 150–400 MB. With per-user limits enforced, 100 concurrent active users need roughly **32 GB RAM and 8+ vCPU** with headroom; idle users cost nothing because their containers are stopped. These numbers must be validated with the load test in Phase 0.

---

## 3. Projects feature (VS Code–style)

| Capability | Design |
|---|---|
| Create project | `POST /api/v1/projects` from a template: **FastAPI**, Flask, Python CLI app, data analysis, empty. Stored in `workspace/projects/<slug>/`. The `projects` table already exists in `models.py`. |
| Dependencies | Per-project `requirements.txt` and virtualenv (`.venv`, created with `uv` for speed) inside the user's container. |
| Explorer & editor | Project-scoped file tree (the nested tree and drag-and-drop now exist). Replace the textarea with **Monaco** (VS Code's editor component): syntax highlighting, multi-cursor, find/replace, minimap. |
| Run | Run configurations per project (e.g. `python main.py`, `uvicorn app.main:app --reload`). Run / Stop / Restart buttons, live **Output panel** streamed over WebSocket, exit code shown. |
| Web app preview | A process listening on `$PORT` inside the container is exposed at a private preview URL, authorized to the owner only. Recommended: `https://<id>.preview.<your-domain>` (needs wildcard DNS + TLS); fallback: path-based `/preview/<id>/` (some apps break under a sub-path). |
| Terminal | xterm.js in the browser + PTY in the user's container. |
| Language features | Pyright or jedi-language-server inside the container, connected to Monaco via LSP over WebSocket (completion, hover, go-to-definition, diagnostics). |
| Later | Debugger (debugpy/DAP), git integration, search across files, problems panel. |

---

## 4. Delivery phases

Each phase ends with automated tests plus a load test against the agreed targets.

| Phase | Scope | Exit criteria |
|---|---|---|
| **0. Stabilize production (urgent)** | Confirm the outage cause with the commands above. Raise compose limits to match the host. Start the idle-kernel reaper. Shut a notebook's kernel down when the user switches away. Cap guest kernels. Fix the anonymous code-execution hole in `/editor/complete`. Remove `server_env` from git and rotate those secrets. Basic monitoring (container memory, kernel count). | No disconnects in a 100-virtual-user load test of notebook execution at the agreed mix; secrets rotated |
| **1. Sandboxed runtimes** | Runtime image + agent, per-user containers, private network, persistent session registry, admin view of runtimes. Notebooks move onto it. | Cross-tenant access tests fail closed; one user's runaway code cannot affect others; API restart keeps sessions |
| **2. Projects MVP** | Project CRUD + templates, project explorer, run configurations, Output panel, Stop. Login required. | Create a FastAPI project from template, run it, see logs, stop it |
| **3. Preview & terminal** | Web app preview URL, browser terminal | Open the running FastAPI app's `/docs` from the IDE; terminal works |
| **4. Editor upgrade** | Monaco + language server, search, problems panel | Completion/hover/go-to-definition in project files |
| **5. Advanced** | Debugger, git, extras | Agreed per feature |

---

## 5. Phase 0 status (code changes done 2026-10-26, not yet deployed)

Implemented and covered by `tests/integration/test_kernel_capacity.py`:
- Server-wide (`MAX_TOTAL_KERNELS`), guest (`MAX_GUEST_KERNELS`) and per-user (`MAX_CONCURRENT_KERNELS_PER_USER`, now 3) kernel caps. When full, abandoned kernels (no browser attached, not executing) are evicted oldest-first; otherwise the user gets a clear "server is at full capacity" message and the browser retries slowly.
- Background maintenance every 30 s: kernels with no browser for `KERNEL_DETACHED_TIMEOUT_SECONDS` (10 min) or no execution for `KERNEL_IDLE_TIMEOUT_SECONDS` (1 h) are shut down; executing kernels never are.
- Memory watchdog: a kernel whose process tree exceeds `KERNEL_MAX_MEMORY_MB` (1 GB) is killed; the running cell reports why and the kernel restarts on the next run.
- Crashed kernels are detected within ~1 s (previously the cell waited for the 60 s timeout) and restarted on the next run.
- Kernel start-up is queued (`KERNEL_START_CONCURRENCY`, default one per CPU core) so bursts of logins no longer all time out.
- Auth no longer holds a database connection for the whole request (pool exhaustion under load); pool sized via `DB_POOL_SIZE`/`DB_MAX_OVERFLOW`; bcrypt and admin `pip` run off the event loop.
- `/editor/complete` no longer imports user-named modules into the API process (anonymous code execution), Jedi no longer searches other users' workspaces, and kernel introspection only uses the caller's own kernel. `get_session` no longer returns another user's (or an admin's) kernel, and two guests no longer share one kernel.
- REST execution timeout is capped at 600 s. `/health` reports kernel capacity (`kernels` field).
- Compose: refuses to start without `SECRET_KEY`, `ADMIN_BOOTSTRAP_PASSWORD`, `POSTGRES_PASSWORD`; the API also refuses public default secrets when `APP_ENV=production`. API limits are configurable (`API_MEM_LIMIT`, `API_CPU_LIMIT`, `API_PIDS_LIMIT`) and `init: true` reaps zombie processes.
- `server_env` and SQLite journal files are no longer tracked or copied into images. They remain in git history.

Load test (`tests/load/capacity_load_test.py`), dev machine with 2 CPUs, caps scaled down to 12 kernels, 30 users at once: before the fixes 15 hard errors (DB pool timeouts, kernel start timeouts) and p95 31 s; after: **0 hard errors**, p95 3.3 s, over-capacity users rejected gracefully, server healthy. A 100-user run must be done on the production-sized host.

**Required on the server before/when deploying Phase 0 (by you):**
1. **Rotate every secret that was in `server_env`** (`SECRET_KEY`, `ADMIN_BOOTSTRAP_PASSWORD`/admin password, `POSTGRES_PASSWORD`). They are in git history, so removing the file is not enough. Rotating `SECRET_KEY` signs everyone out once.
2. Update the server `.env` with the new capacity settings (see `.env.production.example` section 7), sized to the host: currently it sets `API_MEM_LIMIT=2G`, which caps the platform at ~12 active kernels.
3. Rebuild and redeploy the image, then run `python tests/load/capacity_load_test.py --base-url https://<your-domain> --users 100` and watch `docker stats pcs-api`.

Still open from Phase 0: confirming the production outage cause (diagnostics above); stored XSS in notebook HTML outputs (render them in a sandboxed iframe); the API container still runs as root (moving kernels to non-root per-user containers in Phase 1 fixes this without a risky volume ownership migration now).

## 6. Decisions needed before Phase 1

1. **Server specs**: CPU cores, RAM, disk, OS, Docker version. Other sites on the host (LMS) also need headroom.
2. **Domain/TLS**: is Cloudflare in front? Can we use a wildcard subdomain for previews?
3. **Per-user quotas**: accept 1 GB RAM / 1 CPU / 5 GB disk defaults?
4. **Internet access from user code**: allowed (needed for `pip install`), or allow-list only?
5. **Guests**: keep anonymous notebook execution, restrict it to the small guest pool, or require login for all execution?
6. **Access to production**: share the outputs of the diagnostic commands above; changes to the server are made by you or with your explicit approval.
