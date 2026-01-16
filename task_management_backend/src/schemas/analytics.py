from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectAnalyticsOut(BaseModel):
    project_id: UUID
    total_tasks: int = Field(..., ge=0)
    open_tasks: int = Field(..., ge=0)
    in_progress_tasks: int = Field(..., ge=0)
    done_tasks: int = Field(..., ge=0)
    updated_at: datetime


class TeamAnalyticsOut(BaseModel):
    team_id: UUID
    total_projects: int = Field(..., ge=0)
    total_tasks: int = Field(..., ge=0)
    done_tasks: int = Field(..., ge=0)
    updated_at: datetime
