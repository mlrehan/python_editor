# Changelog

All notable changes to the `python-cloud-studio` project will be documented in this file.

## [1.0.0] - 2026-10-09
### Added
- **Phase 0: Project Discovery & Architecture**:
  - Independent monorepo initialized in `python-cloud-studio`.
  - Comprehensive architectural specification (`ARCHITECTURE.md`) with C4 Context and Container diagrams.
  - Threat Model and security policy (`SECURITY.md`) with STRIDE analysis.
  - Complete development guide (`DEVELOPMENT.md`).

- **Phase 1: Local Development Foundation**:
  - FastAPI asynchronous backend application (`services/api`).
  - SQLAlchemy 2.0 async database models (Users, Organizations, Notebooks, Classrooms, Assignments, Submissions, Audit Logs).
  - JWT authentication with bcrypt password hashing and RBAC dependencies.
  - Dockerfiles (`Dockerfile.api`, `Dockerfile.runtime`) and full `docker-compose.yml`.

- **Phase 2: Genuine Python Execution Engine**:
  - Async kernel session manager (`services/runtime_management/kernel_session.py`) coordinating real `ipykernel` instances via ZeroMQ wire protocol.
  - Multi-tenant kernel session pool (`services/runtime_management/kernel_pool.py`) with workspace isolation and concurrency controls.
  - Bidirectional WebSocket proxy (`/ws/kernels/{session_id}`) streaming cell execution stdout, stderr, and MIME outputs.
  - Standard Jupyter format persistence (`nbformat` v4) supporting creation, saving, downloading, and `.ipynb` export.

- **Phase 3: Premium React 19 Web Dashboard**:
  - Full-featured React 19 + TypeScript + Vite frontend (`apps/web-dashboard`).
  - Top Navigation with inline notebook title editing, real-time save indicator, kernel status indicator, and run controls.
  - Left Sidebar with Notebook explorer, workspace File explorer, and Classrooms list.
  - Center Workspace with interactive Code and Markdown cells, cell controls (run, add, delete, reorder), and rich output rendering (stdout, stderr, HTML, Matplotlib PNG charts, traceback formatting).
  - Right Panel with AI Assistant (contextual snippet generation), Variables Inspector, and Runtime Quotas.
  - Direct integration into FastAPI: serving `/app/` out of the box.

- **Automated Acceptance Test Suite**:
  - 18 passing automated tests in `tests/integration/` verifying Tests 01 through 15 (Hello World, math, variable persistence, functions, OOP, NumPy, Pandas, CSV files, Matplotlib charts, exception handling, restart reset, stdout/stderr separation) and Tests 16-22, 32-37, 39, 48-51 (Notebook CRUD, multi-user isolation, path traversal prevention, and classroom assignment workflows).
