from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120, description="Team name (unique).")


class TeamOut(BaseModel):
    id: UUID
    name: str
    created_by_user_id: Optional[UUID] = None


class TeamMemberAdd(BaseModel):
    user_id: UUID = Field(..., description="User to add to the team.")
    role_in_team: str = Field("member", description="Role in team (e.g. member/admin).")


class TeamMemberOut(BaseModel):
    team_id: UUID
    user_id: UUID
    role_in_team: str


class TeamDetail(TeamOut):
    members: List[TeamMemberOut] = Field(default_factory=list)
