from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models import models as m
from src.schemas.analytics import ProjectAnalyticsOut, TeamAnalyticsOut
from src.services.auth import get_current_user
from src.services.domain import _ensure_team_member

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/projects/{project_id}",
    response_model=ProjectAnalyticsOut,
    summary="Get project analytics",
    description="Returns analytics rollup for a project (requires team membership).",
)
def get_project_analytics(project_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)) -> ProjectAnalyticsOut:
    project = db.get(m.Project, project_id)
    if not project:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Project not found")
    _ensure_team_member(db, project.team_id, user.id)

    rollup = db.get(m.AnalyticsProjectRollup, project_id)
    if not rollup:
        # return zeros if not computed yet
        return ProjectAnalyticsOut(
            project_id=project_id,
            total_tasks=0,
            open_tasks=0,
            in_progress_tasks=0,
            done_tasks=0,
            updated_at=project.updated_at,
        )

    return ProjectAnalyticsOut(
        project_id=rollup.project_id,
        total_tasks=rollup.total_tasks,
        open_tasks=rollup.open_tasks,
        in_progress_tasks=rollup.in_progress_tasks,
        done_tasks=rollup.done_tasks,
        updated_at=rollup.updated_at,
    )


@router.get(
    "/teams/{team_id}",
    response_model=TeamAnalyticsOut,
    summary="Get team analytics",
    description="Returns analytics rollup for a team (requires team membership).",
)
def get_team_analytics(team_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)) -> TeamAnalyticsOut:
    _ensure_team_member(db, team_id, user.id)

    rollup = db.get(m.AnalyticsTeamRollup, team_id)
    if not rollup:
        team = db.get(m.Team, team_id)
        if not team:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Team not found")
        return TeamAnalyticsOut(team_id=team_id, total_projects=0, total_tasks=0, done_tasks=0, updated_at=team.updated_at)

    return TeamAnalyticsOut(
        team_id=rollup.team_id,
        total_projects=rollup.total_projects,
        total_tasks=rollup.total_tasks,
        done_tasks=rollup.done_tasks,
        updated_at=rollup.updated_at,
    )
