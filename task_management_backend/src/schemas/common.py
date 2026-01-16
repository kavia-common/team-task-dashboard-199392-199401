from __future__ import annotations

from datetime import datetime
from typing import Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIError(BaseModel):
    """Standard error response."""
    detail: str = Field(..., description="Human-readable error message.")


class PageMeta(BaseModel):
    """Pagination metadata."""
    limit: int = Field(..., ge=1, le=200, description="Page size used.")
    offset: int = Field(..., ge=0, description="Offset used.")
    total: int = Field(..., ge=0, description="Total number of matching records.")


class Page(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    items: List[T]
    meta: PageMeta


class Timestamped(BaseModel):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UUIDModel(BaseModel):
    id: UUID
