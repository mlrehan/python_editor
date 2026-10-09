# 🚀 Enterprise Python Cloud Studio — Local Development & User Guide

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
python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8765 --reload
```

---

## 🌐 Opening the Platform in Your Browser

Once the command is running, open your web browser:

| Interface | URL | Description |
| :--- | :--- | :--- |
| **🎨 Web Dashboard & Notebook Studio** | **[http://localhost:8765/](http://localhost:8765/)** (or `/app/`) | Complete interactive notebook studio, file manager, AI assistant, and classroom panel |
| **📚 Interactive API Documentation** | **[http://localhost:8765/docs](http://localhost:8765/docs)** | OpenAPI Swagger documentation for all REST endpoints |
| **🩺 Health Probe** | **[http://localhost:8765/api/v1/health](http://localhost:8765/api/v1/health)** | Live system metrics, active kernels count, and Python runtime status |

---

## 🔑 Super Admin Credentials & Console

The platform includes a dedicated **Super Admin System** bootstrapped from `.env`:

- **Bootstrap Email**: `admin@example.com`
- **Bootstrap Password**: `AdminSecurePassword2026!`
- **Database Authority**: After the initial bootstrap, credentials are permanently stored in the database. Changing your password in the Admin Console persists across server restarts without ever being overwritten by `.env`.

### Accessing the Super Admin Console:
1. Open [http://localhost:8765/](http://localhost:8765/)
2. Click **Sign In** and enter `admin@example.com` / `AdminSecurePassword2026!`
3. An amber **Admin** button will appear in the top Navbar next to your profile.
4. Click **Admin** to open the full Super Admin Console with 7 management tabs:
   - **System Overview**: Live CPU, RAM, disk storage gauges, total users, and active kernel counts.
   - **User Management**: View, search, create, update roles, toggle package management permissions, and reset user passwords.
   - **Python Packages**: View installed packages, search packages, install new libraries via pip, and uninstall non-protected packages.
   - **Kernel Memory**: Inspect running IPyKernel processes (PID, RAM in MB, CPU %, Idle time), and free memory for individual sessions or terminate all runtimes.
   - **Global Workspaces**: Browse public guest files and private user workspaces; delete obsolete files and folders globally.
   - **Audit Logs**: Full administrative audit trail of all security and system actions.
   - **Admin Profile**: Change Super Admin email, username, and password with real-time database persistence.

---

## 🎨 System / Dark / Light Theme Switcher

The studio includes complete multi-theme support:
- Click the **Theme Toggle** button in the top navigation bar (displays Laptop, Moon, or Sun icon).
- **System**: Automatically syncs with your operating system preference via `prefers-color-scheme`. If Windows flips between Dark and Light mode, the studio UI dynamically adapts instantly.
- **Dark Mode**: Rich enterprise dark navy theme optimized for coding.
- **Light Mode**: High-contrast, clean light theme for presentation and daytime work.
- Preferences are saved locally in `localStorage` and automatically synced to your database profile upon sign-in.

---

## 📂 Multi-Tab File Explorer & Close Lifecycle

The right-side file preview panel delivers a true IDE multi-tab file editing experience:
- **Double-click any file** in the left Files explorer to open it in a tab.
- Opening multiple files creates a scrollable row of tabs with file type icons (`.py`, `.ipynb`, `.csv`, `.md`, `.json`, `.png`, etc.).
- **Dirty State**: If you make modifications to a file, an amber unsaved dot (`●`) appears on the tab.
- **Close Button (X)**:
  - If the file is **saved**: Clicking `(X)` closes the tab immediately.
  - If the file has **unsaved changes**: A modal confirmation appears asking:
    - **Save and Close**: Writes changes to disk and closes tab.
    - **Discard Changes**: Discards unsaved edits and closes tab.
    - **Cancel**: Keeps tab open with edits intact.
- Closing the active tab switches focus to an adjacent open tab; closing the last tab resets the panel cleanly.

---

## 📊 Preinstalled Data Science Libraries & Inline Plots

All core Python data analysis packages are preinstalled and verified:
- **Core Stack**: `numpy`, `pandas`, `scipy`, `scikit-learn`, `statsmodels`
- **Visualization**: `matplotlib`, `seaborn`, `plotly`, `ipympl`
- **Spreadsheets & Data**: `openpyxl`, `xlsxwriter`, `pyarrow`, `Pillow`, `requests`
- **Jupyter Architecture**: `ipykernel`, `IPython`, `ipywidgets`

### Google Colab–Style Visualization:
- When running `plt.plot()` or `sns.heatmap()`, plots render inline immediately beneath code cells as crisp, centered graphics.
- Cells containing multiple `plt.figure()` calls render all figures sequentially in proper order.
- Each figure features a dedicated **Download Plot** button to save high-resolution figures directly to disk.

---

## ⚡ Concurrent Multi-User Execution

The kernel runtime architecture uses per-session locking:
- IPyKernels run in independent processes.
- Long-running computations (e.g. `time.sleep(10)`) by User A do **NOT** block other users.
- User B executing code on their own session computes instantly without waiting for User A.

---

## 🧪 Automated Testing & Verification

Run the test suite using pytest in PowerShell or Command Prompt:

```powershell
cd d:\LAIT\Code_Editors\Jupyter_Lab\python-cloud-studio

# 1. Run all 5 feature enhancement tests (Libraries, Matplotlib, Concurrency, Super Admin, Theme)
python -m pytest tests/integration/test_feature_enhancements.py -v

# 2. Run the full integration test suite (24 tests total)
python -m pytest tests/integration/ -v
```

### Expected Output:
```text
tests/integration/test_feature_enhancements.py::test_01_preinstalled_libraries_import PASSED
tests/integration/test_feature_enhancements.py::test_02_matplotlib_multi_figure_inline PASSED
tests/integration/test_feature_enhancements.py::test_03_concurrent_multi_user_execution PASSED
tests/integration/test_feature_enhancements.py::test_04_super_admin_bootstrap_and_apis PASSED
tests/integration/test_feature_enhancements.py::test_05_theme_preference_persistence PASSED
======================= 5 passed in 17.67s =======================
```

---

## 🔌 Custom Non-Colliding Ports

The application strictly avoids all common default ports (`8000`, `3000`, `5432`, `6379`):

- **FastAPI Control Plane & Production Web Dashboard**: `http://localhost:8765`
- **Frontend Vite Dev Server (HMR development)**: `http://localhost:3765`
- **PostgreSQL Sandbox (Optional)**: `5476`
- **Redis Cache (Optional)**: `6395`

---

## 📁 Repository Structure

```text
python-cloud-studio/
│
├── apps/
│   └── web-dashboard/        # React 19 + TypeScript + Vite modern IDE frontend
│       ├── src/components/   # Navbar, Sidebar, NotebookEditor, FileEditorPanel, AdminDashboard
│       ├── src/context/      # ThemeContext (System, Dark, Light)
│       └── dist/             # Production build served directly by FastAPI
│
├── services/
│   ├── api/                  # FastAPI Control Plane (Auth, Admin, Files, Notebooks, Execution)
│   └── runtime_management/   # Multi-tenant IPyKernel manager & session bridge
│
├── tests/
│   └── integration/          # Automated integration & concurrency tests
│
├── .env                      # Application configuration and bootstrap secrets
├── run_app.bat               # One-click Windows starter
├── run_app.ps1               # PowerShell starter script
└── DEVELOPMENT.md            # This documentation
```
