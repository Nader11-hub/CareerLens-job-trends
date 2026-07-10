"""CareerLens — JWT Authentication Core.

Provides password hashing, JWT token creation/decoding, and FastAPI
dependency functions for protecting endpoints by role.
"""
from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.serving.api.dependencies import get_db

# ---------------------------------------------------------------------------
# Configuration — read from env with safe defaults (override in .env)
# ---------------------------------------------------------------------------
JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "careerlens-secret-key-change-in-production-2024")
JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES: int = int(os.environ.get("JWT_EXPIRE_MINUTES", "480"))  # 8 hours

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Encode *data* into a signed JWT with an expiry claim."""
    payload = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    payload["exp"] = expire
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode *token* and return its payload, or raise HTTP 401."""
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ---------------------------------------------------------------------------
# FastAPI dependency — resolve current user
# ---------------------------------------------------------------------------

def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """FastAPI dependency: return the authenticated User or raise 401."""
    from src.ingestion.db import User  # local import avoids circular deps

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    user_id: int | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token.")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated.",
        )
    return user


def require_admin(current_user=Depends(get_current_user)):
    """FastAPI dependency: ensure the current user has the 'admin' role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return current_user


# ---------------------------------------------------------------------------
# Default admin seeder
# ---------------------------------------------------------------------------

def seed_default_admin(db: Session) -> None:
    """Create a default admin account from env vars if no admin exists."""
    from src.ingestion.db import User  # local import

    admin_username = os.environ.get("ADMIN_USERNAME", "admin")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@careerlens.io")

    existing = db.query(User).filter(User.role == "admin").first()
    if existing:
        return  # admin already exists

    admin = User(
        username=admin_username,
        email=admin_email,
        hashed_password=hash_password(admin_password),
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()
