from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.models import Role, User
from src.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from src.services.auth import (
    create_access_token,
    ensure_roles_exist,
    get_current_user,
    hash_password,
    user_role_names,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new user with email/password, and optionally assigns roles by role name.",
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserOut:
    """
    Create a new user.

    - Email must be unique.
    - Password is stored as bcrypt hash.
    - If roles are provided, they must exist in the roles table.
    """
    existing = db.execute(select(User).where(User.email == str(payload.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=str(payload.email), password_hash=hash_password(payload.password), is_active=True)
    db.add(user)
    db.flush()

    role_objs = []
    if payload.roles:
        role_objs = ensure_roles_exist(db, payload.roles)
    else:
        # default role = member if exists
        member = db.execute(select(Role).where(Role.name == "member")).scalar_one_or_none()
        if member:
            role_objs = [member]

    user.roles = role_objs
    db.commit()
    db.refresh(user)

    return UserOut(id=user.id, email=user.email, is_active=user.is_active, roles=user_role_names(user))


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login (JWT)",
    description="Verifies credentials and returns a JWT bearer token.",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Login using email/password and return JWT."""
    user = db.execute(select(User).where(User.email == str(payload.email))).scalar_one_or_none()
    if not user or not user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(user.id, user_role_names(user))
    return TokenResponse(access_token=token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current user",
    description="Returns the authenticated user's profile and roles.",
)
def me(user: User = Depends(get_current_user)) -> UserOut:
    """Return current user's identity."""
    return UserOut(id=user.id, email=user.email, is_active=user.is_active, roles=user_role_names(user))
