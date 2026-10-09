# 🚀 Local Development & User Guide

Welcome to **Enterprise Python Cloud Studio** (`python-cloud-studio`)!

This guide explains **exactly how to run, test, and use the platform** on your local machine with zero confusion.

---

## ⚡ Quick Start in 60 Seconds

The easiest way to start the entire studio is using the provided scripts or standard commands:

### Option A: One-Click Launch (Windows)
Double-click either:
- **`run_app.bat`** (Windows Command Prompt)
- or run in PowerShell:
  ```powershell
  .\run_app.ps1
  ```

### Option B: Terminal Command
Open PowerShell or Command Prompt in the repository folder:
```powershell
cd d:\LAIT\Code_Editors\Jupyter_Lab\python-cloud-studio
python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 🌐 Opening the Platform in Your Browser

Once the command is running, open your web browser:

| Interface | URL | Description |
| :--- | :--- | :--- |
| **🎨 Web Dashboard & Notebook Studio** | **[http://localhost:8000/](http://localhost:8000/)** (or `/app/`) | Complete interactive notebook studio, file manager, AI assistant, and classroom panel |
| **📚 Interactive API Documentation** | **[http://localhost:8000/docs](http://localhost:8000/docs)** | OpenAPI Swagger documentation for all REST endpoints |
| **🩺 Health Probe** | **[http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)** | Live system metrics, active kernels count, and Python runtime status |

---

## 🧪 How to Verify Everything is Working (Automated Tests)

We provide an automated acceptance test suite that verifies **real Python execution**, **NumPy**, **Pandas**, **Matplotlib charts**, **exception tracebacks**, **kernel restart state resetting**, **multi-user isolation**, and **workspace path traversal defenses**.

To run all tests:
```powershell
python -m pytest tests/integration/ -v
```
*(Or simply double-click `run_tests.bat`)*

### Expected Output:
You will see 18 passed tests with **100% success rate**:
```text
tests/integration/test_api_endpoints.py::test_api_health PASSED
tests/integration/test_api_endpoints.py::test_32_to_37_multi_user_auth_and_isolation PASSED
tests/integration/test_api_endpoints.py::test_16_to_22_notebook_crud_and_ipynb_export PASSED
tests/integration/test_api_endpoints.py::test_39_deny_workspace_path_traversal PASSED
tests/integration/test_api_endpoints.py::test_48_to_51_classroom_and_assignment_workflow PASSED
tests/integration/test_api_endpoints.py::test_api_code_execution_endpoint PASSED
tests/integration/test_kernel_execution.py::test_01_execute_hello_world PASSED
tests/integration/test_kernel_execution.py::test_02_perform_arithmetic PASSED
tests/integration/test_kernel_execution.py::test_03_persist_variables_across_cells PASSED
tests/integration/test_kernel_execution.py::test_04_execute_functions PASSED
tests/integration/test_kernel_execution.py::test_05_execute_python_classes PASSED
tests/integration/test_kernel_execution.py::test_06_import_numpy PASSED
tests/integration/test_kernel_execution.py::test_07_create_pandas_dataframe PASSED
tests/integration/test_kernel_execution.py::test_08_read_csv_with_pandas PASSED
tests/integration/test_kernel_execution.py::test_09_generate_matplotlib_chart PASSED
tests/integration/test_kernel_execution.py::test_11_handle_python_exception PASSED
tests/integration/test_kernel_execution.py::test_13_and_14_restart_kernel_and_variable_reset PASSED
tests/integration/test_kernel_execution.py::test_15_stdout_and_stderr_behavior PASSED

====================== 18 passed in 36s ======================
```

---

## 💻 Manual Verification in the Web UI: What to Try

Once you open **[http://localhost:8000/](http://localhost:8000/)** in your browser, try these workflows:

### 1. Basic Python Execution
Type in the first cell:
```python
print("Hello World from Enterprise Python Cloud Studio!")
```
Click **Run** (or press `Shift + Enter`).  
*Result:* Output displays immediately below the cell, and the execution counter updates to `[1]`.

### 2. Cross-Cell Variable Persistence
In Cell 1:
```python
x = 100
```
Add a new code cell below (click **+ Add Code Cell**) and run:
```python
print(f"Computed total: {x * 5}")
```
*Result:* Displays `Computed total: 500`. Variables persist across cells in the same kernel session!

### 3. Data Science & Chart Rendering (Matplotlib)
Add a code cell and run:
```python
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
plt.figure(figsize=(6, 3))
plt.plot(x, np.sin(x), color='#3b82f6', lw=2)
plt.title("Sine Wave in Cloud Studio")
plt.show()
```
*Result:* A crisp Matplotlib chart renders right inside your notebook!

### 4. Pandas DataFrames
Add a code cell and run:
```python
import pandas as pd
df = pd.DataFrame({
    'Language': ['Python', 'SQL', 'Rust'],
    'Proficiency': [98, 92, 85]
})
print(df)
```
*Result:* Displays the formatted tabular output cleanly.

### 5. Exception & Traceback Handling
Add a cell with:
```python
1 / 0
```
*Result:* Displays a formatted, easy-to-read error box with `ZeroDivisionError` and the exact line traceback.

### 6. Kernel Lifecycle Controls
- Click **Restart** in the top navigation bar: The kernel restarts in seconds, clearing in-memory variables.
- Click **Run All**: Executes every code cell in sequence from top to bottom.
- Click **Save**: Persists the updated notebook to cloud storage.

### 7. AI Assistant
- In the right sidebar, switch to the **AI Assistant** tab.
- Type: `How do I create a bar plot in matplotlib?`
- Click **Send**: The assistant suggests formatted Python code with a **Insert in Notebook** button that pastes it directly into your active workspace!

---

## 🛠️ Frontend Development with Hot Reload (Vite)

If you wish to edit React/TypeScript frontend code with instant browser hot-reloading:

1. **Terminal 1 (Backend API):**
   ```powershell
   cd d:\LAIT\Code_Editors\Jupyter_Lab\python-cloud-studio
   python -m uvicorn services.api.main:app --port 8000 --reload
   ```

2. **Terminal 2 (Frontend Vite Dev Server):**
   ```powershell
   cd d:\LAIT\Code_Editors\Jupyter_Lab\python-cloud-studio\apps\web-dashboard
   npm run dev
   ```
   Open **[http://localhost:3000](http://localhost:3000)** for live hot module replacement. (API and WebSocket calls are automatically proxied to port 8000).

3. **Rebuilding Frontend Production Bundle:**
   Whenever you make changes you want baked into the static FastAPI server:
   ```powershell
   cd d:\LAIT\Code_Editors\Jupyter_Lab\python-cloud-studio\apps\web-dashboard
   npm run build
   ```

---

## 📁 Repository Structure Overview

```text
python-cloud-studio/
│
├── apps/
│   └── web-dashboard/        # React 19 + TypeScript + Vite modern IDE frontend
│
├── services/
│   ├── api/                  # FastAPI Control Plane (Auth, Workspaces, Files, Classrooms)
│   └── runtime_management/   # Real IPyKernel manager & ZeroMQ wire protocol bridge
│
├── infrastructure/
│   └── docker/               # Dockerfiles for API and non-root runtime sandbox
│
├── tests/
│   └── integration/          # 18 automated acceptance tests for kernel & API
│
├── run_app.bat               # One-click Windows starter
├── run_tests.bat             # One-click Windows test runner
├── run_app.ps1               # PowerShell starter script
├── docker-compose.yml        # PostgreSQL & Redis container configuration
├── ARCHITECTURE.md           # System architecture & C4 diagrams
├── SECURITY.md               # STRIDE threat model & sandboxing policies
└── DEVELOPMENT.md            # This setup and user guide
```

---

## ❓ Troubleshooting & FAQs

### Port 8000 is already in use
Run on a different port:
```powershell
python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8080 --reload
```
Then visit `http://localhost:8080/`.

### Missing Python packages
Run:
```powershell
python -m pip install -r services/api/requirements.txt
```

### Resetting local test database
If you want to clear your local development SQLite database:
Simply delete `studio_dev.db`. A clean database with all tables will automatically be recreated upon startup.
