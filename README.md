# Enterprise Python Cloud Studio

[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141%2B-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-blue.svg)](https://react.dev/)
[![Jupyter](https://img.shields.io/badge/Jupyter-IPyKernel-orange.svg)](https://jupyter.org/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)]()

> A production-grade, multi-tenant online Python IDE, notebook workspace, interactive debugger, and collaborative education platform designed for students, instructors, and enterprise teams.

---

## Key Highlights
- **100% Independent**: Fully decoupled from any legacy LMS. Has its own database, authentication, file storage, and execution management.
- **Genuine Execution**: Real Python execution powered by `ipykernel`, `jupyter_client`, and the standard Jupyter wire protocol over WebSockets.
- **Interactive Debugger**: Real step-through debugging, call stack inspection, and variable watch powered by the Jupyter Debug Protocol & `debugpy`.
- **Collaborative Classrooms**: Custom workflows for instructors to assign notebook exercises, distribute datasets, review student snapshots, and provide inline feedback.
- **Defense in Depth**: Zero trust execution architecture with non-root runtimes, workspace path enforcement, and isolated resource quotas.

---

## Repository Structure
```text
python-cloud-studio/
├── apps/
│   ├── web-dashboard/        # Modern React 19 + TypeScript + Vite UI
│   ├── admin-dashboard/      # Organization and platform management UI
│   └── notebook-extensions/  # JupyterLab extensions & custom widgets
├── services/
│   ├── api/                  # FastAPI Control Plane (Auth, Workspaces, Files)
│   ├── runtime-management/   # Kernel Manager, Wire Protocol & ZMQ Bridge
│   ├── collaboration/        # Real-time multi-user synchronization
│   └── ai-assistant/         # Context-aware AI coding assistance
├── packages/
│   ├── shared-types/         # Unified TypeScript/Python data schemas
│   └── ui-components/        # Reusable design tokens and components
├── runtimes/
│   └── base-python/          # Versioned kernel environments
├── infrastructure/
│   ├── docker/               # Containerfiles & Docker Compose
│   └── kubernetes/           # Helm charts & K8s deployment manifests
├── tests/
│   ├── unit/                 # Unit tests
│   ├── integration/          # Real Python kernel execution & API tests
│   └── e2e/                  # End-to-end integration workflows
└── docs/                     # Comprehensive architecture and security documentation
```

---

## Quick Start
See [DEVELOPMENT.md](DEVELOPMENT.md) for full setup instructions.
```bash
# 1. Run tests
python -m pytest tests/ -v

# 2. Start Backend API & Kernel Gateway
python -m uvicorn services.api.main:app --port 8000 --reload

# 3. Start Frontend Dashboard
cd apps/web-dashboard
npm run dev
```

---

## License
Confidential and Proprietary.
