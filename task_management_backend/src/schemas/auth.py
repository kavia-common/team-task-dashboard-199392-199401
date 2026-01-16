from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email (unique).")
    password: str = Field(..., min_length=8, max_length=128, description="User password (min 8 chars).")
    roles: Optional[List[str]] = Field(None, description="Optional role names to assign (admin/member).")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email.")
    password: str = Field(..., description="User password.")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token (bearer).")
    token_type: str = Field("bearer", description="Token type.")


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool
    roles: List[str] = Field(default_factory=list)
