# Project State: Enterprise Python Cloud Studio

## Current Status Overview
- **Active Phase**: PHASE 8 COMPLETE & FULLY VERIFIED — Google Colab–Grade Non-Overlapping Autocomplete & Function Signature Popups, Active Parameter Highlighting, Single-Key Escape Priority Dismissal, and Comprehensive E2E Verification.
- **Current Milestone**: Milestone 3.3 (100% Passing Tests Across Full Test Suites: 15/15 E2E & Integration IntelliSense/Theme Tests, Production Vite Frontend Built with 0 Errors, Zero Regressions Across All Baseline Systems).
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
- **TDR-023**: Non-Overlapping Dual Popups & Single-Key Escape Priority:
  - **Disjoint Geometry Invariant**: Signature help tooltip is positioned above cursor line (`top: lineTop - 6px`, `transform: translateY(-100%)`) while autocomplete dropdown is positioned below cursor line (`top: lineBottom + 6px`). Vertical separation is at least `lineHeight + 12px` (~33px), guaranteeing 0px overlap and unobstructed visibility of the line being written.
  - **Colab Trigger Differentiation**: Typing `print(` opens signature help only without popping open the 100+ completions dropdown. Autocomplete only opens when an identifier token is typed (e.g. `print(s`), a dot is typed (`np.`), or explicitly triggered (`Ctrl+Space`).
  - **Single-Key Escape Dismissal Priority**: Window capture-phase and textarea handlers use `__pcsHandledEscape` guard and `dismissTopmostPopup` helper. 1st `Escape` press closes *only* the autocomplete dropdown, leaving signature help visible. 2nd `Escape` press closes signature help.
  - **Active Parameter Highlighting**: Active parameter from language server is highlighted in the signature tooltip with an accent underline and background badge.

---

## Verified Acceptance Test Results (100% Passing)

### IntelliSense, Autocomplete & Theme Verification Suite (15 Tests)
- [x] `tests/e2e/test_signature_autocomplete_overlap_e2e.py::test_signature_and_autocomplete_overlap_and_escape_priority` (PASSED)
  - Typing `print(` shows signature help only (autocomplete closed)
  - Typing `print(s` shows both popups with disjoint vertical geometry (`sig_bottom <= drop_top`, difference +33px)
  - First Escape dismisses autocomplete only; signature help stays visible
  - Second Escape dismisses signature help
  - Typing `pri` + Enter inserts `print` without executing cell
- [x] `tests/e2e/test_autocomplete_full_e2e.py::test_autocomplete_exact_text_insertion_and_modes` (PASSED)
  - `pd.re` + Enter $\rightarrow$ `pd.read_csv` (Zero corruption: no `pd.ad_csv` or `pd._csv`)
  - `pd.re` + Tab $\rightarrow$ `pd.read_csv`
  - `pd.re` + Mouse Click $\rightarrow$ `pd.read_csv`
  - `pd.read_c` + Enter $\rightarrow$ `pd.read_csv`
  - `np.ar` + Enter $\rightarrow$ `np.array`
- [x] `tests/e2e/test_autocomplete_full_e2e.py::test_autocomplete_scrolling_escape_and_outside_click` (PASSED)
  - 8x ArrowDown scrolls dropdown listbox to 120px
  - ArrowUp scrolls listbox back up to 84px
  - Escape closes dropdown immediately without modifying code
  - Navbar click closes dropdown immediately
  - Signature tooltip (`pd.read_csv(`) displays parameters and closes on Escape
- [x] `tests/e2e/test_theme_and_cell_resize_e2e.py::test_theme_switching_system_dark_light` (PASSED)
  - Light mode: navbar `#ffffff`, body `#f8fafc`
  - Dark mode: navbar `#0f172a`
  - Autocomplete dropdown renders with theme-consistent styling
- [x] `tests/e2e/test_theme_and_cell_resize_e2e.py::test_vertical_cell_resizing_and_persistence` (PASSED)
  - Drag downward expands height from 68px to 188px
  - Height persists after cell code execution (`Ctrl+Enter`)
  - Double-click resets cell back to auto-fit (68px)
- [x] `tests/e2e/test_editor_intellisense_e2e.py::test_python_editor_autocomplete_and_clean_diagnostics` (PASSED)
- [x] `tests/integration/test_editor_intellisense.py::test_numpy_autocomplete` (PASSED)
- [x] `tests/integration/test_editor_intellisense.py::test_pandas_autocomplete` (PASSED)
- [x] `tests/integration/test_editor_intellisense.py::test_cross_cell_context_dataframe_autocomplete` (PASSED)
- [x] `tests/integration/test_editor_intellisense.py::test_prefix_filtering` (PASSED)
- [x] `tests/integration/test_editor_intellisense.py::test_signature_help` (PASSED)
- [x] `tests/integration/test_editor_intellisense.py::test_diagnostics_clean_on_valid_code` (PASSED)
- [x] `tests/integration/test_editor_intellisense.py::test_diagnostics_suppress_incomplete_expression` (PASSED)
- [x] `tests/integration/test_editor_intellisense.py::test_diagnostics_real_syntax_error` (PASSED)
- [x] `tests/integration/test_editor_intellisense.py::test_diagnostics_missing_module_error` (PASSED)

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

# 3. Run all automated tests:
python -m pytest tests/e2e/test_autocomplete_full_e2e.py -v -s
python -m pytest tests/e2e/test_theme_and_cell_resize_e2e.py -v -s
python -m pytest tests/integration/test_editor_intellisense.py -v
```

Dashboard is accessible at: `http://localhost:8765/`
