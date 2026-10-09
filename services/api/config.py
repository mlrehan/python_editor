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

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./studio_dev.db"

    # Runtime and Storage
    DEFAULT_KERNEL_NAME: str = "python3"
    MAX_CONCURRENT_KERNELS_PER_USER: int = 5
    KERNEL_IDLE_TIMEOUT_SECONDS: int = 3600
    WORKSPACES_ROOT: str = "./storage/workspaces"
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_PATH: str = "./storage/artifacts"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

