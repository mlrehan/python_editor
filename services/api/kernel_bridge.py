import os
import sys

try:
    from services.runtime_management.kernel_pool import KernelPoolManager, KernelCapacityError
except ImportError:
    from ..runtime_management.kernel_pool import KernelPoolManager, KernelCapacityError

from .config import settings

kernel_pool = KernelPoolManager(
    workspaces_root=settings.WORKSPACES_ROOT,
    max_kernels_per_user=settings.MAX_CONCURRENT_KERNELS_PER_USER,
    idle_timeout_seconds=settings.KERNEL_IDLE_TIMEOUT_SECONDS,
    max_total_kernels=settings.MAX_TOTAL_KERNELS,
    max_guest_kernels=settings.MAX_GUEST_KERNELS,
    detached_timeout_seconds=settings.KERNEL_DETACHED_TIMEOUT_SECONDS,
    max_kernel_memory_mb=settings.KERNEL_MAX_MEMORY_MB,
    start_concurrency=settings.KERNEL_START_CONCURRENCY,
)
