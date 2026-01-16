from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.models import User
from src.schemas.common import Page, PageMeta
from src.schemas.tasks import (
    TaskCommentCreate,
    TaskCommentOut,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)
from src.services.auth import get_current_user
from src.services.domain import (
    add_task_comment,
    create_task,
    get_task,
    list_task_comments,
    list_tasks,
    update_task,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _task_to_out(t) -> TaskOut:
    # Fetch assignments explicitly for response to avoid implicit lazy loads
    return TaskOut(
        id=t.id,
        project_id=t.project_id,
        board_id=t.board_id,
        column_id=t.column_id,
        title=t.title,
        description=t.description,
        status=t.status,
        priority=t.priority,
        due_date=t.due_date,
        created_by_user_id=t.created_by_user_id,
        assignee_user_ids=[],
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


@router.post(
    "",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create task",
    description="Creates a task under a project; optional board/column; can assign users and emits notifications.",
)
def create_task_endpoint(payload: TaskCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> TaskOut:
    t = create_task(
        db=db,
        actor_user_id=user.id,
        project_id=payload.project_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        status=payload.status,
        board_id=payload.board_id,
        column_id=payload.column_id,
        due_date=payload.due_date,
        assignee_user_ids=payload.assignee_user_ids,
    )
    # Attach assignee ids via assignments table
    from src.models.models import TaskAssignment

    ids = db.query(TaskAssignment.user_id).filter(TaskAssignment.task_id == t.id).all()
    out = _task_to_out(t)
    out.assignee_user_ids = [r[0] for r in ids]
    return out


@router.get(
    "",
    response_model=Page[TaskOut],
    summary="List tasks",
    description="Lists tasks with pagination and filters. Requires either team_id or project_id.",
)
def list_tasks_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    team_id: UUID | None = Query(None, description="Filter tasks by team (requires membership)"),
    project_id: UUID | None = Query(None, description="Filter tasks by project (requires membership)"),
    status_filter: str | None = Query(None, alias="status", description="Filter by task status"),
    priority_filter: str | None = Query(None, alias="priority", description="Filter by priority"),
    board_id: UUID | None = Query(None),
    column_id: UUID | None = Query(None),
    assignee_user_id: UUID | None = Query(None, description="Filter tasks assigned to a user"),
    q: str | None = Query(None, description="Search in title/description"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[TaskOut]:
    items, total = list_tasks(
        db=db,
        actor_user_id=user.id,
        project_id=project_id,
        team_id=team_id,
        status_filter=status_filter,
        priority_filter=priority_filter,
        board_id=board_id,
        column_id=column_id,
        assignee_user_id=assignee_user_id,
        q=q,
        limit=limit,
        offset=offset,
    )

    from src.models.models import TaskAssignment

    outs: list[TaskOut] = []
    for t in items:
        out = _task_to_out(t)
        ids = db.query(TaskAssignment.user_id).filter(TaskAssignment.task_id == t.id).all()
        out.assignee_user_ids = [r[0] for r in ids]
        outs.append(out)

    return Page(items=outs, meta=PageMeta(limit=limit, offset=offset, total=int(total)))


@router.get(
    "/{task_id}",
    response_model=TaskOut,
    summary="Get task",
    description="Gets a task by id (requires membership in the task's project team).",
)
def get_task_endpoint(task_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> TaskOut:
    t = get_task(db, task_id, user.id)
    from src.models.models import TaskAssignment

    ids = db.query(TaskAssignment.user_id).filter(TaskAssignment.task_id == t.id).all()
    out = _task_to_out(t)
    out.assignee_user_ids = [r[0] for r in ids]
    return out


@router.patch(
    "/{task_id}",
    response_model=TaskOut,
    summary="Update task",
    description="Updates a task fields and optionally replaces assignees; emits notifications to new assignees.",
)
def update_task_endpoint(
    task_id: UUID, payload: TaskUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> TaskOut:
    t = update_task(
        db=db,
        task_id=task_id,
        actor_user_id=user.id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        status=payload.status,
        board_id=payload.board_id,
        column_id=payload.column_id,
        due_date=payload.due_date,
        assignee_user_ids=payload.assignee_user_ids,
    )
    from src.models.models import TaskAssignment

    ids = db.query(TaskAssignment.user_id).filter(TaskAssignment.task_id == t.id).all()
    out = _task_to_out(t)
    out.assignee_user_ids = [r[0] for r in ids]
    return out


@router.post(
    "/{task_id}/comments",
    response_model=TaskCommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add comment",
    description="Adds a comment to a task and notifies assignees.",
)
def add_comment_endpoint(
    task_id: UUID, payload: TaskCommentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> TaskCommentOut:
    c = add_task_comment(db, task_id, user.id, payload.body)
    return TaskCommentOut(id=c.id, task_id=c.task_id, author_user_id=c.author_user_id, body=c.body, created_at=c.created_at)


@router.get(
    "/{task_id}/comments",
    response_model=list[TaskCommentOut],
    summary="List comments",
    description="Lists comments for a task (requires membership in the task's project team).",
)
def list_comments_endpoint(task_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[TaskCommentOut]:
    items = list_task_comments(db, task_id, user.id)
    return [TaskCommentOut(id=c.id, task_id=c.task_id, author_user_id=c.author_user_id, body=c.body, created_at=c.created_at) for c in items]
