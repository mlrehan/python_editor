# Development Guide: Enterprise Python Cloud Studio

## Prerequisites
- **Python**: 3.12+ (tested with 3.14)
- **Node.js**: 20+ (tested with v24.16.0) & npm 10+
- **Git**
- Optional: Docker & Docker Compose (for production container tests)

---

## Quickstart (Local Development)

### 1. Backend Setup
From the repository root (`python-cloud-studio/`):
```bash
# Verify environment
python -m pip install -r services/api/requirements.txt

# Run the FastAPI control plane & Kernel Gateway
python -m uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be available at: `http://localhost:8000/docs`

### 2. Frontend Setup
From the repository root:
```bash
cd apps/web-dashboard
npm install
npm run dev
```
Web Dashboard will be available at: `http://localhost:3000`

---

## Running Automated Tests

### Python Backend & Kernel Execution Tests
```bash
python -m pytest tests/unit tests/integration -v
```

### End-to-End Tests
```bash
python -m pytest tests/e2e -v
```

---

## Code Quality Standards
- Python: Formatted with clean typing (`mypy` / `pyright`), documented functions, explicit schemas.
- TypeScript: Strict typing enabled (`tsconfig.json`), no `any` where avoidable.
- Tests: Every milestone requires real functional verification. No fake mocks for actual Python code execution.
