from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.models import Role, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _secret_key() -> str:
    """
    Read JWT secret from env when available.

    NOTE: orchestrator should set JWT_SECRET in .env for production.
    """
    return os.getenv("JWT_SECRET", "dev-insecure-secret-change-me")


def _algorithm() -> str:
    return os.getenv("JWT_ALGORITHM", "HS256")


def _expiry_minutes() -> int:
    try:
        return int(os.getenv("JWT_EXPIRES_MINUTES", "720"))
    except ValueError:
        return 720


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against stored hash."""
    return pwd_context.verify(password, password_hash)


def create_access_token(subject_user_id: UUID, roles: List[str]) -> str:
    """Create JWT access token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject_user_id),
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=_expiry_minutes())).timestamp()),
    }
    return jwt.encode(payload, _secret_key(), algorithm=_algorithm())


def decode_token(token: str) -> dict:
    """Decode and validate JWT."""
    try:
        return jwt.decode(token, _secret_key(), algorithms=[_algorithm()])
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e


# PUBLIC_INTERFACE
def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """FastAPI dependency that returns the authenticated user."""
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = db.get(User, UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")
    return user


# PUBLIC_INTERFACE
def require_roles(required: List[str]):
    """
    Dependency factory to require that the current user has at least one of the required roles.
    Roles come from the DB relationship to ensure consistency.
    """

    def _dep(user: User = Depends(get_current_user)) -> User:
        names = {r.name for r in user.roles}
        if not names.intersection(set(required)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return _dep


def ensure_roles_exist(db: Session, role_names: List[str]) -> List[Role]:
    """Ensure requested roles exist; returns Role objects or raises 400."""
    if not role_names:
        return []

    rows = db.execute(select(Role).where(Role.name.in_(role_names))).scalars().all()
    found = {r.name for r in rows}
    missing = [r for r in role_names if r not in found]
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown roles: {missing}")
    return rows


def user_role_names(user: User) -> List[str]:
    """Return role names for a user."""
    return [r.name for r in user.roles]
