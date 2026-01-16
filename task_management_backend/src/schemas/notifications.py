from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationOut(BaseModel):
    id: UUID
    user_id: UUID
    type: str = Field(..., description="info|warning|task|system")
    title: str
    message: str
    is_read: bool
    created_at: datetime


class NotificationMarkRead(BaseModel):
    is_read: bool = Field(True, description="Set notification read flag.")
