from __future__ import annotations

from typing import List
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    team_id: UUID = Field(..., description="Owning team id.")
    name: str = Field(..., min_length=2, max_length=200, description="Project name (unique within team).")


class ProjectOut(BaseModel):
    id: UUID
    team_id: UUID
    name: str


class BoardCreate(BaseModel):
    project_id: UUID = Field(..., description="Owning project id.")
    name: str = Field(..., min_length=2, max_length=200, description="Board name (unique within project).")


class BoardOut(BaseModel):
    id: UUID
    project_id: UUID
    name: str


class ColumnCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Column name (unique per board).")
    position: int = Field(..., ge=0, le=1000, description="Column order position (unique per board).")


class ColumnOut(BaseModel):
    id: UUID
    board_id: UUID
    name: str
    position: int


class BoardDetail(BoardOut):
    columns: List[ColumnOut] = Field(default_factory=list)
