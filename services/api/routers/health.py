import sys
from datetime import datetime
from fastapi import APIRouter
from ..config import settings
from ..schemas import SystemHealthResponse
from ..kernel_bridge import kernel_pool

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=SystemHealthResponse)
async def health_check():
    """Returns application status, python runtime details, and active kernel counts."""
    return SystemHealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        active_kernels=len(kernel_pool._sessions),
        python_version=sys.version.split(" ")[0],
        timestamp=datetime.utcnow(),
    )

