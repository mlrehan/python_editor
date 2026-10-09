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

from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

# Register WebSockets router
app.include_router(websockets.router)

# Mount static frontend build if present
dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "web-dashboard", "dist"))
assets_path = os.path.join(dist_path, "assets")
index_html = os.path.join(dist_path, "index.html")

if os.path.exists(assets_path):
    app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    app.mount("/app/assets", StaticFiles(directory=assets_path), name="app_assets")

if os.path.exists(dist_path) and os.path.exists(index_html):
    @app.get("/")
    async def serve_root():
        return FileResponse(index_html)

    @app.get("/app")
    @app.get("/app/")
    async def serve_app():
        return FileResponse(index_html)
else:
    @app.get("/")
    async def root():
        return {
            "platform": settings.APP_NAME,
            "version": "1.0.0",
            "docs_url": "/docs",
            "api_v1_prefix": "/api/v1",
        }

