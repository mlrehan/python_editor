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
    warm_pool_size=settings.KERNEL_WARM_POOL_SIZE,
    preload_modules=[m.strip() for m in settings.KERNEL_PRELOAD_MODULES.split(",") if m.strip()],
    warm_refill_delay_seconds=settings.KERNEL_WARM_REFILL_DELAY_SECONDS,
)

from .guest_workspace import GuestWorkspaces

# Private guest workspaces, seeded from the starter files in workspaces/public
guest_workspaces = GuestWorkspaces(settings.WORKSPACES_ROOT, template_dir=kernel_pool.get_public_workspace_path())
kernel_pool.guest_path_resolver = guest_workspaces.path


def _remove_idle_guest_workspaces() -> None:
    active = {s.user_id[len("guest_"):] for s in kernel_pool.sessions.values() if s.user_id.startswith("guest_")}
    guest_workspaces.remove_idle(settings.GUEST_WORKSPACE_IDLE_DAYS * 86400, active)


kernel_pool.maintenance_hooks.append(_remove_idle_guest_workspaces)
