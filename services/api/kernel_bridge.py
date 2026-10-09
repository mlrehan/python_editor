import os
import sys

try:
    from services.runtime_management.kernel_pool import KernelPoolManager
except ImportError:
    from ..runtime_management.kernel_pool import KernelPoolManager

from .config import settings

kernel_pool = KernelPoolManager(
    workspaces_root=settings.WORKSPACES_ROOT,
    max_kernels_per_user=settings.MAX_CONCURRENT_KERNELS_PER_USER,
    idle_timeout_seconds=settings.KERNEL_IDLE_TIMEOUT_SECONDS,
)

