# Project State: Enterprise Python Cloud Studio

## Current Status Overview
- **Active Phase**: PHASE 10 COMPLETE & FULLY VERIFIED — Interactive Kernel Restart Lifecycle with Visual Feedback (Animated Spin, Toast Banners, Pulsing Blue Status), Seamless `%pip install` User-Site Auto-Discovery, ZeroMQ Clean Process Reconnection, and Comprehensive E2E Verification.
- **Current Milestone**: Milestone 4.1 (100% Passing Tests Across Pip Install & Kernel Restart Integration & E2E Suites, Zero Regressions Across All Baseline Systems).
- **Environment**: Windows 11 x64, Python 3.14.0, Node.js 24.16.0, npm 11.13.0, Git 2.54.0.
- **Dedicated Service Ports (Strictly Preserved)**:
  - Web Dashboard & API: `http://localhost:8765/` (Swagger docs: `http://localhost:8765/docs`)
  - Dev Server: `3765`
  - PostgreSQL Port (if configured): `5476`
  - Redis Port (if configured): `6395`
  - **CRITICAL CONSTRAINT**: NEVER use ports `8000`, `3000`, `5432`, or `6379`.

---

## Technical Decisions Record (TDR)

- **TDR-001**: Standalone monorepo architecture with clean boundaries: `apps/`, `services/`, `packages/`, `infrastructure/`, `tests/`.
- **TDR-002**: Real Python Kernel execution powered directly by `jupyter_client` and `ipykernel` with ZeroMQ message passing and asynchronous WebSockets bridge.
- **TDR-003**: Native `.ipynb` (v4 format) compatibility using `nbformat`.
- **TDR-004**: Database tier using SQLAlchemy 2.0 with asynchronous engine (`aiosqlite` for local dev, `asyncpg` for PostgreSQL production).
- **TDR-005**: Real-time communication for interactive notebook execution, outputs, and debugging using standard Jupyter Wire Protocol over WebSockets.
- **TDR-006**: React 19 + TypeScript frontend with unified static serving via FastAPI `/app` and `/` for zero-configuration developer onboarding.
- **TDR-007**: Google Colab-Style File Management with independently collapsible sidebars, auto-expanding right preview/editor panel on double-click, and multi-format support (`.py`, `.csv` tabular viewer, `.md` preview, `.ipynb`).
- **TDR-008**: Custom port allocation (API `8765`, Dev `3765`, Postgres `5476`, Redis `6395`) to prevent collisions with user's existing background systems.
- **TDR-009**: 100% Edge-to-Edge Responsive Layout: Center notebook editor dynamically fills all horizontal space between visible panels without 960px constraints or margins across all 4 sidebar permutations.
- **TDR-010**: Google Colab-Style Draggable Resizers: Vertical divider resizing for Left Sidebar (200–600px) and Right Sidebar (280–800px) with real-time mouse drag and `localStorage` persistence.
- **TDR-011**: Zero Login Wall & Guest Public Workspace: Instant notebook coding, file CRUD, and execution in `/storage/workspaces/public/` without authentication. Protected with capability tokens (`X-Guest-Token`) to prevent guest overwriting.
- **TDR-012**: Non-Intrusive Auth Modal & Private Workspace Isolation: Non-blocking login dialog preserving in-memory notebook state; seamless transition to isolated `./storage/workspaces/user_{id}/` directory.
- **TDR-013**: Preinstalled Enterprise Data Analysis Libraries: Verified locked dependencies including `numpy`, `pandas`, `scipy`, `scikit-learn`, `statsmodels`, `openpyxl`, `xlsxwriter`, `pyarrow`, `Pillow`, `requests`, `plotly`, `ipykernel`, `IPython`, `ipywidgets`, `ipympl`.
- **TDR-014**: Super Admin System & Database Authority: Idempotent bootstrap from `.env` (`admin@example.com` / `AdminSecurePassword2026!`). Password changes via Admin Console are persisted directly in the database and never overwritten on reboot.
- **TDR-015**: Multi-Tab File Management & Close Lifecycle: Multi-tab file manager in the right panel with unsaved dirty tracking (`●`), visible `(X)` close buttons, and an interactive confirmation modal ("Save and Close", "Discard Changes", "Cancel").
- **TDR-016**: System / Dark / Light Theme Switcher: Theme context supporting OS-synced `System` mode (`prefers-color-scheme` listener), `Dark`, and `Light` modes, stored in `localStorage ('pcs_theme')` and synced with user database profiles.
- **TDR-017**: Concurrent Multi-User Execution: Independent IPyKernel processes with per-session locking; verified non-blocking simultaneous execution across multiple concurrent users.
- **TDR-018**: Colab-Style Matplotlib Inline Multi-Figure Rendering: Inline display of PNG/JPEG/SVG graphics rendered sequentially with per-figure "Download Plot" action controls.
- **TDR-019**: Real-time Language Server & Diagnostic AST Analysis: FastAPI `/api/v1/editor/complete` and `/diagnostics` powered by Jedi static analysis + live IPyKernel introspection. Suppresses incomplete syntax errors during active typing; verifies clean imports for NumPy and Pandas.
- **TDR-020**: Semantic CSS Custom Properties Engine: Complete palette defined in `index.css` (`--bg-app`, `--bg-navbar`, `--bg-sidebar`, `--bg-cell`, `--bg-cell-gutter`, `--text-main`, `--dropdown-bg`, etc.) replacing all hardcoded Tailwind and inline hex colors across all components.
- **TDR-021**: Vertically Resizable Code Cells & Metadata Persistence:
  - Drag handle at cell bottom (`[data-testid="cell-resize-handle"]`) resizes editor height (80px–800px).
  - Synchronizes line number gutter and diagnostic underline layer `scrollTop` in lockstep with the textarea.
  - Persists custom height in `cell.metadata.custom_height` across executions, theme switches, cell navigation, and saves.
  - Double-click resets cell back to auto-fit.
- **TDR-022**: Google Colab-Grade Autocomplete & Text Insertion Engine:
  - **Full Symbol Delivery**: Backend always supplies `insert_text = c.name` (`read_csv`, `DataFrame`, `array`), avoiding Jedi delta suffix truncation.
  - **Deterministic Live-DOM Replacement**: `acceptCompletion` computes the token range directly from `textarea.value` and `selectionStart` at the instant of execution (`/\.([a-zA-Z0-9_]*)$/` for member access, `/\b([a-zA-Z0-9_]+)$/` for identifiers), ensuring zero corruptions (`pd.read_csv`, `np.array`).
  - **Input Parity**: Enter, Tab, and mouse clicks produce identical results. Mouse click uses `onMouseDown={e.preventDefault()}` to preserve editor selection.
  - **Keyboard Auto-Scrolling**: `listRef` synchronizes active suggestion index with DOM `scrollTop` so the highlighted item is always visible.
  - **Viewport-Aware Positioning**: Dynamically calculates space below; flips above the cursor if space below is <260px; clamps horizontally to prevent overflowing editor boundaries.
  - **Dismissal Lifecycle & Async Request Guards**: Global `pointerdown` outside click listener and window `Escape` listener dismiss popups. Uses monotonic `autocompleteReqIdRef` to discard in-flight completions arriving after dismissal.
- **TDR-024**: Server-Side Secret Shielding & Kernel Environment Sanitization:
  - `get_sanitized_kernel_env()` strips critical infrastructure credentials (`SECRET_KEY`, `DATABASE_URL`, `ADMIN_BOOTSTRAP_PASSWORD`) before launching tenant IPyKernel processes.
  - Binds tenant user site packages to `PYTHONUSERBASE=workspace/.local`.
  - Injects tenant `.env` safely into runtime without exposing platform host variables.
- **TDR-025**: Permission-Based Package Installation & OS-Level Escape Prevention:
  - Static AST and regex inspection in `validate_code_security()` intercepts unauthorized `%pip` / `!pip` calls for unprivileged users and guests.
  - Rewrites authorized `%pip` to include `--user` targeting isolated tenant workspace.
  - Intercepts OS escapes (`!apt`, `!sudo`, `os.system("sudo ...")`) and writes security violations to audit log.
- **TDR-026**: High-Concurrency Database Architecture (SQLite WAL & Busy Timeout):
  - Configures SQLite `PRAGMA journal_mode=WAL;` and `PRAGMA busy_timeout=60000;` alongside connection timeout 60s, completely eliminating database locking under 100+ concurrent user read/write bursts.
- **TDR-027**: Persistent Workspace Session Resumption & Debounced Auto-Save:
  - 2.5-second debounced save pipeline on cell edits.
  - Saves active notebook ID in `localStorage.pcs_active_notebook_id` and restores session state automatically on browser reconnection.
  - Standalone `NotebooksModal.tsx` provides full CRUD, duplication, download, and switching across workspace notebooks.
- **TDR-028**: Workspace-Level `.env` & AI API Key Management:
  - Dedicated `/api/v1/files/env` REST endpoint and `SecretsModal.tsx` for configuring `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `HUGGINGFACEHUB_API_TOKEN`, and custom variables.
- **TDR-029**: Production HTTP Security Headers:
  - Registered ASGI security middleware enforcing `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Content-Security-Policy`.
- **TDR-030**: Mobile-Responsive Drawer Overlays & Non-Colliding Layout:
  - Viewports <768px transition sidebars to overlay drawer mode with backdrop dismissal.
  - Dynamic navbar spacing (`flexShrink: 0`, auto overflow) preventing touch target collision on 375px screens.
- **TDR-031**: Dual-Path Synchronous Kernel Restart & Interactive Feedback Lifecycle:
  - Clean ZeroMQ socket channel teardown and IPyKernel subprocess re-initialization in `KernelSession.restart()`.
  - Frontend triggers REST `/api/v1/execution/control` (with WebSocket fallback), updating UI with animated spinning icon (`animate-spin`), button disabled state, pulsing blue status indicator (`Python 3 (restarting)`), and immediate toast banners ("Restarting Python kernel..." -> "Python kernel restarted successfully. Variables reset.").
- **TDR-032**: Python User-Site Packages Auto-Discovery & Post-PIP Runtime Refresh Hook:
  - Pre-creates versioned user site-packages (`.local/Python{major}{minor}/site-packages` on Windows, `.local/lib/python{major}.{minor}/site-packages` on Unix) and configures `PYTHONPATH` + `PYTHONUSERBASE` at launch.
  - `KernelSession.execute()` automatically runs an internal site-packages refresh and `importlib.invalidate_caches()` hook whenever `%pip` / `!pip` runs, making newly installed packages immediately importable in subsequent cells without requiring manual restart.
- **TDR-033**: Multi-Tenant Workspace Package Discovery & Live Diagnostics Synchronization:
  - Resolves workspace-installed libraries (`.local/site-packages`) across user workspaces and `workspaces_root` via `importlib.machinery.PathFinder.find_spec(root_pkg, search_paths)`.
  - Injects resolved paths into `jedi.Project(path=primary_ws, sys_path=full_sys_paths)` so Jedi autocompletes workspace-installed libraries (`rich`, `seaborn`, local modules) with full docstrings and signatures.
  - Dispatches `pcs-refresh-diagnostics` custom events upon cell execution completion (WS & REST) and kernel restarts, prompting cell editors to immediately refresh diagnostics without requiring code changes.
  - Guarantees 0 false "unresolved import" warnings on valid installed packages while maintaining strict red squiggly underlines on genuine missing modules and syntax errors.
- **TDR-034**: Google Colab-Grade Interactive Tabular Data Viewer (`DataTableView`):
  - Converts raw pandas/Jupyter HTML tables (`<table class="dataframe">`) into a modern, full-featured interactive data viewer component.
  - Features dynamic column sorting (numeric and alphanumeric with visual `▲`/`▼` indicators), live cross-column search filtering with clear button, selectable page sizes (10, 25, 50, 100, All), full pagination navigation, CSV file download, and one-click TSV clipboard copying.
  - Implements intelligent column type inference (`number`, `string`, `date`, `boolean`) with proper right/left alignment, monospace numeric formatting, and elegant badges for missing values (`NaN`, `None`, `<NA>`, `NaT`).
  - Seamlessly integrates with system Dark and Light themes via semantic CSS variables.
- **TDR-035**: Google Colab-Style User File and Folder Isolation & Session Boundary Enforcement:
  - **Dynamic Sidebar Remounting**: `key={user ? `user-${user.id}` : 'guest-public'}` forces complete React unmounting/remounting on session transitions (SuperAdmin <-> Guest <-> Student), eliminating any DOM or state retention of private files.
  - **Session State Cleansing**: Logout and login handlers reset `openFiles: []`, `activeFilePath: null`, `isRightSidebarOpen: false`, clear `pcs_active_notebook_id` from `localStorage`, and dispatch `pcs-refresh-files` window event.
  - **Workspace Status Indication**: Visual badge in Sidebar header explicitly displays current isolation context (`[Public]`, `[Private]`, `[Admin]`).
  - **Defense-in-Depth Path Traversal Interception**:
    - **Backend File API**: `get_safe_user_path()` strictly restricts directory resolution within the tenant's workspace root, returning `403 Forbidden` for `../` escapes.
    - **Static Code Analyzer**: `validate_code_security()` rejects any code referencing cross-workspace paths (`user_admin_super`, `../user_`, `workspaces/user_`) with `SecurityError`.
    - **Runtime Sandbox Guard (`sitecustomize.py`)**: Intercepts `builtins.open`, `io.open`, `IPython.core.interactiveshell.io_open`, `os.listdir`, `os.scandir`, and `os.stat` in IPyKernel processes, raising `PermissionError` if resolved realpath points to another user's workspace.
    - **PYTHONPATH Shielding**: `get_sanitized_kernel_env()` only exposes `public/.local` and the user's own `.local` packages, completely preventing cross-tenant library discovery.

---

## Verified Acceptance Test Results (100% Passing)

### Live Workspace Diagnostics & Interactive Table Suite (100% Passing)
- [x] `test_diagnostics_live_workspace_resolution` (PASSED)
  - `from rich import print`: 0 diagnostics (installed package recognized in workspace site-packages).
  - `import nonexistent_fake_pkg`: 1 accurate diagnostic (`Unresolved import 'nonexistent_fake_pkg': No module named 'nonexistent_fake_pkg' found in active Python runtime.`).
  - `np.` transient expression: 0 false syntax errors.
  - Jedi `/api/v1/editor/complete` returns 98 completions for `from rich import ` (`abc`, `align`, `ansi`, `Any`, `bar`, ...).
- [x] `scratch/test_e2e_verification.py::run` (PASSED in browser)
  - Interactive Data Table: `DataTableView` renders with record count pill (`12 rows × 7 cols`).
  - Column headers with sort arrows and column type badges (`#` for number, `T` for text).
  - Numeric sorting: sorting `salary` ascending orders values numerically (`75000` to `125000`).
  - Live search filtering: typing "Engineering" dynamically filters table down to `3 of 12 rows`.
  - Missing values: `None` / `NaN` formatted with elegant muted badges.
  - CSV export & TSV clipboard copy buttons verified.
  - Rich module execution verified with green styled output and 0 squiggly underlines.
  - Visual artifacts: `interactive_datatable_view_verified.png`, `table_salary_sorted_asc_verified.png`, `table_filtered_engineering_verified.png`, `rich_module_no_diagnostics_verified.png`, `table_and_editor_light_theme_verified.png`.

### Kernel Restart & Pip Installation Suite
- [x] `tests/integration/test_pip_install_and_restart.py::test_pip_install_and_kernel_restart_integration` (PASSED in 9.18s)
  - Authorized `%pip install rich` execution
  - Immediate `from rich import print` import in running kernel
  - Synchronous kernel restart via `/api/v1/execution/control`
  - Variable state reset (`x` raises `NameError`) and rich module persistence in restarted kernel
- [x] `tests/e2e/test_kernel_restart_and_pip_e2e.py::test_ui_restart_kernel_and_pip_rich_execution` (PASSED in 10.38s)
  - Verified UI restart button transitions to spinning icon & disabled state
  - Verified toast notification banner appears immediately and confirms success
  - Verified code cell execution of `from rich import print as rprint; rprint('[bold green]RICH WORKS![/bold green]')` with styled output in browser
  - Visual artifacts: `kernel_restart_toast_verified.png`, `rich_module_output_verified.png`

### Production Readiness & Security Audit Suite (9 Tests)
- [x] `tests/integration/test_production_security_audit.py::test_01_security_headers` (PASSED)
- [x] `tests/integration/test_production_security_audit.py::test_02_guest_package_install_rejected` (PASSED)
- [x] `tests/integration/test_production_security_audit.py::test_03_student_without_permission_rejected` (PASSED)
- [x] `tests/integration/test_production_security_audit.py::test_04_authorized_user_package_install` (PASSED)
- [x] `tests/integration/test_production_security_audit.py::test_05_os_escape_prevention` (PASSED)
- [x] `tests/integration/test_production_security_audit.py::test_06_server_secret_shielding_in_kernel` (PASSED)
- [x] `tests/integration/test_production_security_audit.py::test_07_workspace_env_and_ai_credentials` (PASSED)
- [x] `tests/integration/test_production_security_audit.py::test_08_superadmin_audited_endpoints` (PASSED)
- [x] `tests/integration/test_production_security_audit.py::test_09_cross_user_file_isolation` (PASSED)

### Mobile & Tablet Responsiveness Suite (Playwright E2E)
- [x] `tests/e2e/test_mobile_responsiveness_e2e.py::test_mobile_and_tablet_responsiveness` (PASSED in 6.86s)
  - Mobile iPhone SE (375x667): Drawer overlay and backdrop dismissal verified.
  - Tablet iPad (768x1024): Non-overlapping toolbar and modal rendering verified.
  - Generated visual artifacts: `mobile_viewport_375x667_verified.png`, `mobile_notebooks_modal_verified.png`, `mobile_secrets_modal_verified.png`, `tablet_viewport_768x1024_verified.png`.

### High-Concurrency Empirical Benchmarks (100+ Users)
- [x] `test_100_concurrent_dashboard_requests`: 100/100 completed, 0 errors (0.00%), 47.63 req/sec, p50: 1224.42ms, p95: 1383.24ms, p99: 1425.61ms.
- [x] `test_100_concurrent_notebook_operations`: 100/100 completed, 0 errors (0.00%), 1.85 req/sec, p50: 30217.66ms, p95: 45999.12ms, p99: 52147.47ms.
- [x] `test_100_concurrent_websocket_connections`: 100/100 completed, 0 errors (0.00%), 37.48 req/sec, p50: 920.83ms, p95: 1755.04ms, p99: 1788.27ms.
- [x] `test_concurrent_kernel_executions`: 20/20 completed, 0 errors (0.00%), 0.62 req/sec, p50: 13434.83ms, p95: 19904.66ms, p99: 19904.66ms.

### IntelliSense, Autocomplete & Theme Verification Suite (15 Tests)
- [x] `tests/e2e/test_signature_autocomplete_overlap_e2e.py::test_signature_and_autocomplete_overlap_and_escape_priority` (PASSED)
- [x] `tests/e2e/test_autocomplete_full_e2e.py::test_autocomplete_exact_text_insertion_and_modes` (PASSED)
- [x] `tests/e2e/test_autocomplete_full_e2e.py::test_autocomplete_scrolling_escape_and_outside_click` (PASSED)
- [x] `tests/e2e/test_theme_and_cell_resize_e2e.py::test_theme_switching_system_dark_light` (PASSED)
- [x] `tests/e2e/test_theme_and_cell_resize_e2e.py::test_vertical_cell_resizing_and_persistence` (PASSED)
- [x] `tests/e2e/test_editor_intellisense_e2e.py::test_python_editor_autocomplete_and_clean_diagnostics` (PASSED)
- [x] All 9 Language Server unit & integration tests (PASSED)

### Baseline Platform Tests (100% Passing)
- [x] TEST FEATURE 01: Preinstalled Libraries Import (`test_01_preinstalled_libraries_import` PASSED)
- [x] TEST FEATURE 02: Colab-Style Matplotlib Multi-Figure Rendering (`test_02_matplotlib_multi_figure_inline` PASSED)
- [x] TEST FEATURE 03: Concurrent Multi-User Execution (`test_03_concurrent_multi_user_execution` PASSED)
- [x] TEST FEATURE 04: Super Admin Bootstrap, Stats, Packages, Runtimes, Workspaces (`test_04_super_admin_bootstrap_and_apis` PASSED)
- [x] TEST FEATURE 05: Theme Preference Persistence in DB (`test_05_theme_preference_persistence` PASSED)
- [x] Baseline Kernel Execution & Math Tests (`test_01_execute_hello_world` through `test_09_generate_matplotlib_chart` PASSED)
- [x] File Manager CRUD & Multi-tab tests (`test_comprehensive_file_management_crud` PASSED)
- [x] E2E Colab Layout, Drag Dividers & Guest Access (`test_layout_guest_and_resizing.py` PASSED)

---

## Commands to Run / Resume

```powershell
# 1. Start the platform server (Port 8765):
cd D:\LAIT\Code_Editors\Jupyter_Lab\python-cloud-studio
.\run_app.ps1
# Or directly:
python -m uvicorn services.api.main:app --port 8765 --reload

# 2. Build the frontend dashboard (Vite + TypeScript):
npm --prefix apps/web-dashboard run build

# 3. Run all automated verification tests:
python -m pytest tests/integration/test_production_security_audit.py -v
python -m pytest tests/e2e/test_mobile_responsiveness_e2e.py -v -s
python -m pytest tests/load/test_concurrency_100_users.py -v -s
```

Dashboard is accessible at: `http://localhost:8765/`
