from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models import models as m
from src.schemas.boards import (
    BoardCreate,
    BoardDetail,
    BoardOut,
    ColumnCreate,
    ColumnOut,
    ProjectCreate,
    ProjectOut,
)
from src.schemas.common import Page, PageMeta
from src.services.auth import get_current_user
from src.services.domain import create_board, create_column, create_project, list_board_columns

router = APIRouter(prefix="/boards", tags=["boards"])


@router.post(
    "/projects",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
    description="Creates a project under a team (requires team membership).",
)
def create_project_endpoint(payload: ProjectCreate, db: Session = Depends(get_db), user=Depends(get_current_user)) -> ProjectOut:
    p = create_project(db, payload.team_id, payload.name, actor_user_id=user.id)
    return ProjectOut(id=p.id, team_id=p.team_id, name=p.name)


@router.get(
    "/projects",
    response_model=Page[ProjectOut],
    summary="List projects",
    description="List projects for a team (paginated). Requires team membership.",
)
def list_projects(
    team_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[ProjectOut]:
    from src.services.domain import _ensure_team_member  # internal helper

    _ensure_team_member(db, team_id, user.id)
    stmt = select(m.Project).where(m.Project.team_id == team_id)
    total = db.execute(select(m.Project).where(m.Project.team_id == team_id).with_only_columns(m.func.count()).order_by(None)).scalar_one()  # type: ignore
    items = db.execute(stmt.order_by(m.Project.created_at.desc()).limit(limit).offset(offset)).scalars().all()
    return Page(
        items=[ProjectOut(id=p.id, team_id=p.team_id, name=p.name) for p in items],
        meta=PageMeta(limit=limit, offset=offset, total=int(total)),
    )


@router.post(
    "",
    response_model=BoardOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a board",
    description="Creates a board under a project (requires project team membership).",
)
def create_board_endpoint(payload: BoardCreate, db: Session = Depends(get_db), user=Depends(get_current_user)) -> BoardOut:
    b = create_board(db, payload.project_id, payload.name, actor_user_id=user.id)
    return BoardOut(id=b.id, project_id=b.project_id, name=b.name)


@router.get(
    "",
    response_model=Page[BoardOut],
    summary="List boards",
    description="List boards for a project (paginated). Requires project team membership.",
)
def list_boards(
    project_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[BoardOut]:
    from src.services.domain import _ensure_team_member  # internal helper

    project = db.get(m.Project, project_id)
    if not project:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Project not found")
    _ensure_team_member(db, project.team_id, user.id)

    stmt = select(m.Board).where(m.Board.project_id == project_id)
    total = db.execute(select(m.func.count()).select_from(stmt.subquery())).scalar_one()
    items = db.execute(stmt.order_by(m.Board.created_at.desc()).limit(limit).offset(offset)).scalars().all()
    return Page(
        items=[BoardOut(id=b.id, project_id=b.project_id, name=b.name) for b in items],
        meta=PageMeta(limit=limit, offset=offset, total=int(total)),
    )


@router.post(
    "/{board_id}/columns",
    response_model=ColumnOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a column",
    description="Creates a board column (requires board's project team membership).",
)
def create_column_endpoint(
    board_id: UUID,
    payload: ColumnCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> ColumnOut:
    c = create_column(db, board_id, payload.name, payload.position, actor_user_id=user.id)
    return ColumnOut(id=c.id, board_id=c.board_id, name=c.name, position=c.position)


@router.get(
    "/{board_id}",
    response_model=BoardDetail,
    summary="Get board",
    description="Returns board details including columns.",
)
def get_board(board_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)) -> BoardDetail:
    board = db.get(m.Board, board_id)
    if not board:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Board not found")
    project = db.get(m.Project, board.project_id)
    if not project:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Project not found")
    from src.services.domain import _ensure_team_member  # internal helper

    _ensure_team_member(db, project.team_id, user.id)

    cols = list_board_columns(db, board_id)
    return BoardDetail(
        id=board.id,
        project_id=board.project_id,
        name=board.name,
        columns=[ColumnOut(id=c.id, board_id=c.board_id, name=c.name, position=c.position) for c in cols],
    )
