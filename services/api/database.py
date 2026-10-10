from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from .config import settings

# Configure SQLite or PostgreSQL async engine
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    connect_args["timeout"] = 60.0

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    connect_args=connect_args,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Creates database tables if they do not exist, runs column migrations, and bootstraps Super Admin."""
    async with engine.begin() as conn:
        if settings.DATABASE_URL.startswith("sqlite"):
            from sqlalchemy import text
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            await conn.execute(text("PRAGMA busy_timeout=60000;"))
            await conn.execute(text("PRAGMA synchronous=NORMAL;"))

        await conn.run_sync(Base.metadata.create_all)

        # Safe SQLite column migration for existing database files
        if settings.DATABASE_URL.startswith("sqlite"):
            from sqlalchemy import text
            res = await conn.execute(text("PRAGMA table_info(users)"))
            cols = [row[1] for row in res.fetchall()]
            if "can_manage_packages" not in cols:
                await conn.execute(text("ALTER TABLE users ADD COLUMN can_manage_packages BOOLEAN DEFAULT 0 NOT NULL"))
            if "theme_preference" not in cols:
                await conn.execute(text("ALTER TABLE users ADD COLUMN theme_preference VARCHAR(20) DEFAULT 'system' NOT NULL"))

    # Ensure system public_guest user and Super Admin exist
    async with AsyncSessionLocal() as session:
        from .models import User
        from .auth import hash_password
        from sqlalchemy import select

        # 1. Ensure public_guest user
        res_guest = await session.execute(select(User).where(User.id == "public_guest"))
        if not res_guest.scalar_one_or_none():
            guest = User(
                id="public_guest",
                email="guest@cloudstudio.internal",
                hashed_password="not-a-usable-password-hash",
                full_name="Guest Visitor",
                role="student",
                is_active=True,
                can_manage_packages=False,
                theme_preference="system",
            )
            session.add(guest)

        # 2. Super Admin Bootstrap Check:
        # Check if ANY user with role == 'super_admin' exists in the database
        res_super = await session.execute(select(User).where(User.role == "super_admin").limit(1))
        existing_super = res_super.scalars().first()

        if not existing_super:
            # Check if bootstrap email already exists
            res_email = await session.execute(select(User).where(User.email == settings.ADMIN_BOOTSTRAP_EMAIL))
            user_by_email = res_email.scalar_one_or_none()
            if user_by_email:
                # Promote to super_admin
                user_by_email.role = "super_admin"
                user_by_email.can_manage_packages = True
            else:
                # Create initial Super Admin from .env credentials
                super_admin = User(
                    id="admin_super",
                    email=settings.ADMIN_BOOTSTRAP_EMAIL,
                    hashed_password=hash_password(settings.ADMIN_BOOTSTRAP_PASSWORD),
                    full_name="Super Administrator",
                    role="super_admin",
                    is_active=True,
                    can_manage_packages=True,
                    theme_preference="system",
                )
                session.add(super_admin)

        try:
            await session.commit()
        except Exception:
            await session.rollback()


