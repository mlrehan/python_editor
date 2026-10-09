from datetime import datetime, timedelta
from typing import Optional, List
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_db
from .models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against its bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Validates and decodes a JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency that resolves the authenticated User from the Bearer JWT token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account inactive or not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


class GuestUser:
    """Represents an unauthenticated guest accessing the public workspace."""
    def __init__(self, guest_token: str):
        self.id = "public_guest"
        self.guest_token = guest_token
        self.email = "guest@cloudstudio.internal"
        self.full_name = "Guest Visitor"
        self.role = "guest"
        self.is_guest = True
        self.is_active = True
        self.can_manage_packages = False
        self.theme_preference = "system"


from fastapi import Header
from typing import Union


async def get_current_user_or_guest(
    token: Optional[str] = Depends(oauth2_scheme),
    x_guest_token: Optional[str] = Header(None, alias="X-Guest-Token"),
    db: AsyncSession = Depends(get_db)
) -> Union[User, GuestUser]:
    """
    Resolves the authenticated User from the Bearer JWT token if present.
    If no valid token is supplied, returns a GuestUser bound to the public workspace.
    """
    if token:
        try:
            payload = decode_access_token(token)
            user_id: Optional[str] = payload.get("sub")
            if user_id:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if user and user.is_active:
                    user.is_guest = False
                    user.guest_token = None
                    return user
        except Exception:
            pass

    token_str = x_guest_token or "gst_guest_session"
    return GuestUser(token_str)


def require_role(*allowed_roles: str):
    """Enforces role-based authorization check."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles and current_user.role not in ("super_admin", "platform_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of the following roles: {', '.join(allowed_roles)}",
            )
        return current_user
    return role_checker


async def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Enforces that current user is a Super Admin."""
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to Super Administrators only.",
        )
    return current_user


async def require_admin_or_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Enforces that current user is an Admin or Super Admin."""
    if current_user.role not in ("super_admin", "admin", "platform_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to administrators.",
        )
    return current_user


async def require_package_permission(
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest)
) -> User:
    """Enforces that caller has permission to install/manage Python packages."""
    if getattr(current_user, "is_guest", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guest users are not permitted to install or modify Python packages.",
        )
    if current_user.role in ("super_admin", "admin", "platform_admin"):
        return current_user
    if getattr(current_user, "can_manage_packages", False):
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Permission Denied: You do not have permission to install or manage Python packages. Contact your administrator.",
    )

