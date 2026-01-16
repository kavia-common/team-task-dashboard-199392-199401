from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.models import Team, User
from src.schemas.common import Page, PageMeta
from src.schemas.teams import TeamCreate, TeamDetail, TeamMemberAdd, TeamMemberOut, TeamOut
from src.services.auth import get_current_user
from src.services.domain import add_team_member, create_team, list_team_members

router = APIRouter(prefix="/teams", tags=["teams"])


@router.post(
    "",
    response_model=TeamOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a team",
    description="Creates a new team. The creator becomes an admin member of the team.",
)
def create_team_endpoint(payload: TeamCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> TeamOut:
    team = create_team(db, payload.name, created_by_user_id=user.id)
    return TeamOut(id=team.id, name=team.name, created_by_user_id=team.created_by_user_id)


@router.get(
    "",
    response_model=Page[TeamOut],
    summary="List teams",
    description="Lists teams (paginated). Currently returns all teams; frontend can filter client-side.",
)
def list_teams(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[TeamOut]:
    total = db.execute(select(Team).count()).scalar_one() if hasattr(select(Team), "count") else db.query(Team).count()
    items = db.execute(select(Team).order_by(Team.created_at.desc()).limit(limit).offset(offset)).scalars().all()
    return Page(
        items=[TeamOut(id=t.id, name=t.name, created_by_user_id=t.created_by_user_id) for t in items],
        meta=PageMeta(limit=limit, offset=offset, total=total),
    )


@router.get(
    "/{team_id}",
    response_model=TeamDetail,
    summary="Get team detail",
    description="Returns a team and its members.",
)
def get_team(team_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> TeamDetail:
    team = db.get(Team, team_id)
    if not team:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Team not found")
    members = list_team_members(db, team.id)
    return TeamDetail(
        id=team.id,
        name=team.name,
        created_by_user_id=team.created_by_user_id,
        members=[TeamMemberOut(team_id=m.team_id, user_id=m.user_id, role_in_team=m.role_in_team) for m in members],
    )


@router.post(
    "/{team_id}/members",
    response_model=TeamMemberOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add team member",
    description="Adds a user to a team. Requires requester to be a team admin.",
)
def add_member(
    team_id: str,
    payload: TeamMemberAdd,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TeamMemberOut:
    tm = add_team_member(db, UUID(team_id), payload.user_id, actor_user_id=user.id, role_in_team=payload.role_in_team)
    return TeamMemberOut(team_id=tm.team_id, user_id=tm.user_id, role_in_team=tm.role_in_team)


from uuid import UUID  # keep import at end to avoid circular in some linters
