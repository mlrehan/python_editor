import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Enterprise Python Cloud Studio"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    API_PORT: int = 8765
    WEB_PORT: int = 3765

    # Security & JWT
    SECRET_KEY: str = "pcs-super-secret-key-change-in-production-32chars-min!!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Initial Super Admin Bootstrap (from .env)
    ADMIN_BOOTSTRAP_EMAIL: str = "admin@example.com"
    ADMIN_BOOTSTRAP_PASSWORD: str = "AdminSecurePassword2026!"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./studio_dev.db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Runtime and Storage
    DEFAULT_KERNEL_NAME: str = "python3"
    MAX_CONCURRENT_KERNELS_PER_USER: int = 3
    # Server-wide caps: size these to the host (each active kernel uses ~150-400 MB)
    MAX_TOTAL_KERNELS: int = 40
    MAX_GUEST_KERNELS: int = 10
    # No execution for this long -> kernel is shut down (variables are lost, like Colab's idle timeout)
    KERNEL_IDLE_TIMEOUT_SECONDS: int = 3600
    # No browser attached (tab closed / notebook switched) for this long -> kernel is shut down
    KERNEL_DETACHED_TIMEOUT_SECONDS: int = 600
    # A kernel whose process tree exceeds this is killed so it cannot starve other users (0 = no limit)
    KERNEL_MAX_MEMORY_MB: int = 1024
    KERNEL_MAINTENANCE_INTERVAL_SECONDS: int = 30
    # Kernels allowed to start at the same time (0 = one per CPU core); others wait their turn
    KERNEL_START_CONCURRENCY: int = 0
    WORKSPACES_ROOT: str = "./storage/workspaces"
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_PATH: str = "./storage/artifacts"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

_DEFAULT_SECRET_KEY = "pcs-super-secret-key-change-in-production-32chars-min!!"
_DEFAULT_ADMIN_PASSWORD = "AdminSecurePassword2026!"


def assert_production_secrets(s: Settings) -> None:
    """Refuses to run in production with the public default secrets (anyone could forge admin tokens)."""
    if s.APP_ENV.lower() != "production":
        return
    problems = []
    if s.SECRET_KEY == _DEFAULT_SECRET_KEY or len(s.SECRET_KEY) < 32:
        problems.append("SECRET_KEY is the public default or shorter than 32 characters")
    if s.ADMIN_BOOTSTRAP_PASSWORD == _DEFAULT_ADMIN_PASSWORD:
        problems.append("ADMIN_BOOTSTRAP_PASSWORD is the public default")
    if problems:
        raise RuntimeError("Insecure production configuration: " + "; ".join(problems) + ". Set them in .env.")


assert_production_secrets(settings)

