import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .kernel_bridge import kernel_pool
from .routers import health, auth, notebooks, execution, files, classrooms, websockets


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database schema
    await init_db()
    # Ensure storage paths exist
    os.makedirs(settings.WORKSPACES_ROOT, exist_ok=True)
    os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
    yield
    # Shutdown: clean up any running kernels
    await kernel_pool.shutdown_all()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Enterprise Python Cloud Studio Control Plane & Execution Gateway",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers under /api/v1
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(notebooks.router, prefix="/api/v1")
app.include_router(execution.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(classrooms.router, prefix="/api/v1")

from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

# Register WebSockets router
app.include_router(websockets.router)

# Mount static frontend build if present
dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "web-dashboard", "dist"))
if os.path.exists(dist_path):
    app.mount("/app", StaticFiles(directory=dist_path, html=True), name="dashboard")


@app.get("/")
async def root():
    if os.path.exists(dist_path):
        return RedirectResponse(url="/app/")
    return {
        "platform": settings.APP_NAME,
        "version": "1.0.0",
        "docs_url": "/docs",
        "api_v1_prefix": "/api/v1",
    }

