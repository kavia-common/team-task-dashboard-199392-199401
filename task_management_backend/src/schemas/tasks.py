from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    project_id: UUID = Field(..., description="Owning project id.")
    title: str = Field(..., min_length=1, max_length=200, description="Task title.")
    description: Optional[str] = Field(None, max_length=5000, description="Task description.")
    priority: str = Field("medium", description="low|medium|high")
    status: str = Field("open", description="open|in_progress|done")
    board_id: Optional[UUID] = Field(None, description="Optional board id.")
    column_id: Optional[UUID] = Field(None, description="Optional column id.")
    due_date: Optional[datetime] = Field(None, description="Optional due date.")
    assignee_user_ids: List[UUID] = Field(default_factory=list, description="Optional list of user IDs to assign.")


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    priority: Optional[str] = Field(None, description="low|medium|high")
    status: Optional[str] = Field(None, description="open|in_progress|done")
    board_id: Optional[UUID] = None
    column_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    assignee_user_ids: Optional[List[UUID]] = Field(None, description="Replace assignees with this set.")


class TaskOut(BaseModel):
    id: UUID
    project_id: UUID
    board_id: Optional[UUID] = None
    column_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    due_date: Optional[datetime] = None
    created_by_user_id: Optional[UUID] = None
    assignee_user_ids: List[UUID] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TaskCommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000, description="Comment body.")


class TaskCommentOut(BaseModel):
    id: UUID
    task_id: UUID
    author_user_id: Optional[UUID] = None
    body: str
    created_at: datetime
