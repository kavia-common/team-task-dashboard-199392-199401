from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models import models as m


def _not_found(entity: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} not found")


def _conflict(msg: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)


def _bad_request(msg: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


def _ensure_team_member(db: Session, team_id: UUID, user_id: UUID) -> m.TeamMembership:
    membership = db.get(m.TeamMembership, {"team_id": team_id, "user_id": user_id})
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this team")
    return membership


def create_team(db: Session, name: str, created_by_user_id: Optional[UUID]) -> m.Team:
    existing = db.execute(select(m.Team).where(m.Team.name == name)).scalar_one_or_none()
    if existing:
        raise _conflict("Team name already exists")
    team = m.Team(name=name, created_by_user_id=created_by_user_id)
    db.add(team)
    db.flush()
    if created_by_user_id:
        # creator becomes member/admin by default
        db.add(m.TeamMembership(team_id=team.id, user_id=created_by_user_id, role_in_team="admin"))
    db.commit()
    db.refresh(team)
    return team


def add_team_member(db: Session, team_id: UUID, user_id: UUID, actor_user_id: UUID, role_in_team: str) -> m.TeamMembership:
    membership = _ensure_team_member(db, team_id, actor_user_id)
    if membership.role_in_team != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only team admins can add members")

    if not db.get(m.Team, team_id):
        raise _not_found("Team")
    if not db.get(m.User, user_id):
        raise _not_found("User")

    existing = db.get(m.TeamMembership, {"team_id": team_id, "user_id": user_id})
    if existing:
        raise _conflict("User already in team")

    tm = m.TeamMembership(team_id=team_id, user_id=user_id, role_in_team=role_in_team or "member")
    db.add(tm)
    db.commit()
    return tm


def list_team_members(db: Session, team_id: UUID) -> List[m.TeamMembership]:
    if not db.get(m.Team, team_id):
        raise _not_found("Team")
    return db.execute(select(m.TeamMembership).where(m.TeamMembership.team_id == team_id)).scalars().all()


def create_project(db: Session, team_id: UUID, name: str, actor_user_id: UUID) -> m.Project:
    _ensure_team_member(db, team_id, actor_user_id)
    # uniqueness enforced by constraint, but we provide nicer error
    existing = db.execute(
        select(m.Project).where(m.Project.team_id == team_id, m.Project.name == name)
    ).scalar_one_or_none()
    if existing:
        raise _conflict("Project name already exists in team")

    project = m.Project(team_id=team_id, name=name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def create_board(db: Session, project_id: UUID, name: str, actor_user_id: UUID) -> m.Board:
    project = db.get(m.Project, project_id)
    if not project:
        raise _not_found("Project")
    _ensure_team_member(db, project.team_id, actor_user_id)

    existing = db.execute(
        select(m.Board).where(m.Board.project_id == project_id, m.Board.name == name)
    ).scalar_one_or_none()
    if existing:
        raise _conflict("Board name already exists in project")

    board = m.Board(project_id=project_id, name=name)
    db.add(board)
    db.commit()
    db.refresh(board)
    return board


def create_column(db: Session, board_id: UUID, name: str, position: int, actor_user_id: UUID) -> m.BoardColumn:
    board = db.get(m.Board, board_id)
    if not board:
        raise _not_found("Board")
    project = db.get(m.Project, board.project_id)
    if not project:
        raise _not_found("Project")
    _ensure_team_member(db, project.team_id, actor_user_id)

    existing_name = db.execute(
        select(m.BoardColumn).where(m.BoardColumn.board_id == board_id, m.BoardColumn.name == name)
    ).scalar_one_or_none()
    if existing_name:
        raise _conflict("Column name already exists in board")

    existing_pos = db.execute(
        select(m.BoardColumn).where(m.BoardColumn.board_id == board_id, m.BoardColumn.position == position)
    ).scalar_one_or_none()
    if existing_pos:
        raise _conflict("Column position already exists in board")

    col = m.BoardColumn(board_id=board_id, name=name, position=position)
    db.add(col)
    db.commit()
    db.refresh(col)
    return col


def list_board_columns(db: Session, board_id: UUID) -> List[m.BoardColumn]:
    if not db.get(m.Board, board_id):
        raise _not_found("Board")
    return (
        db.execute(select(m.BoardColumn).where(m.BoardColumn.board_id == board_id).order_by(m.BoardColumn.position))
        .scalars()
        .all()
    )


def create_task(
    db: Session,
    actor_user_id: UUID,
    project_id: UUID,
    title: str,
    description: Optional[str],
    priority: str,
    status: str,
    board_id: Optional[UUID],
    column_id: Optional[UUID],
    due_date,
    assignee_user_ids: List[UUID],
) -> m.Task:
    project = db.get(m.Project, project_id)
    if not project:
        raise _not_found("Project")
    _ensure_team_member(db, project.team_id, actor_user_id)

    if board_id:
        board = db.get(m.Board, board_id)
        if not board or board.project_id != project_id:
            raise _bad_request("board_id must belong to the same project")
    if column_id:
        col = db.get(m.BoardColumn, column_id)
        if not col:
            raise _bad_request("column_id not found")
        if board_id and col.board_id != board_id:
            raise _bad_request("column_id must belong to board_id")
        if board_id is None:
            # infer board_id from column
            board_id = col.board_id

    task = m.Task(
        project_id=project_id,
        board_id=board_id,
        column_id=column_id,
        title=title,
        description=description,
        priority=priority,
        status=status,
        due_date=due_date,
        created_by_user_id=actor_user_id,
    )
    db.add(task)
    db.flush()

    # Assign users (validate they exist)
    if assignee_user_ids:
        users = db.execute(select(m.User).where(m.User.id.in_(assignee_user_ids))).scalars().all()
        found = {u.id for u in users}
        missing = [str(uid) for uid in assignee_user_ids if uid not in found]
        if missing:
            raise _bad_request(f"Unknown assignees: {missing}")

        for uid in assignee_user_ids:
            db.add(m.TaskAssignment(task_id=task.id, user_id=uid))
            # Create a notification for assignment
            db.add(
                m.Notification(
                    user_id=uid,
                    type="task",
                    title="Task assigned",
                    message=f"You were assigned to task: {title}",
                    is_read=False,
                )
            )

    _update_rollups_for_project(db, project_id)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: UUID, actor_user_id: UUID) -> m.Task:
    task = db.get(m.Task, task_id)
    if not task:
        raise _not_found("Task")
    project = db.get(m.Project, task.project_id)
    if not project:
        raise _not_found("Project")
    _ensure_team_member(db, project.team_id, actor_user_id)
    return task


def list_tasks(
    db: Session,
    actor_user_id: UUID,
    project_id: Optional[UUID],
    team_id: Optional[UUID],
    status_filter: Optional[str],
    priority_filter: Optional[str],
    board_id: Optional[UUID],
    column_id: Optional[UUID],
    assignee_user_id: Optional[UUID],
    q: Optional[str],
    limit: int,
    offset: int,
):
    # Determine team scope
    if project_id:
        project = db.get(m.Project, project_id)
        if not project:
            raise _not_found("Project")
        _ensure_team_member(db, project.team_id, actor_user_id)
        team_id = project.team_id
    elif team_id:
        _ensure_team_member(db, team_id, actor_user_id)
    else:
        raise _bad_request("Either project_id or team_id is required")

    stmt = select(m.Task)

    if project_id:
        stmt = stmt.where(m.Task.project_id == project_id)
    else:
        # tasks for all projects in team
        stmt = stmt.join(m.Project, m.Project.id == m.Task.project_id).where(m.Project.team_id == team_id)

    if status_filter:
        stmt = stmt.where(m.Task.status == status_filter)
    if priority_filter:
        stmt = stmt.where(m.Task.priority == priority_filter)
    if board_id:
        stmt = stmt.where(m.Task.board_id == board_id)
    if column_id:
        stmt = stmt.where(m.Task.column_id == column_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(m.Task.title.ilike(like) | m.Task.description.ilike(like))

    if assignee_user_id:
        stmt = stmt.join(m.TaskAssignment, m.TaskAssignment.task_id == m.Task.id).where(
            m.TaskAssignment.user_id == assignee_user_id
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()

    items = (
        db.execute(stmt.order_by(m.Task.created_at.desc()).limit(limit).offset(offset))
        .scalars()
        .all()
    )
    return items, total


def update_task(
    db: Session,
    task_id: UUID,
    actor_user_id: UUID,
    title: Optional[str],
    description: Optional[str],
    priority: Optional[str],
    status: Optional[str],
    board_id: Optional[UUID],
    column_id: Optional[UUID],
    due_date,
    assignee_user_ids: Optional[List[UUID]],
) -> m.Task:
    task = get_task(db, task_id, actor_user_id)

    if board_id is not None:
        if board_id:
            board = db.get(m.Board, board_id)
            if not board or board.project_id != task.project_id:
                raise _bad_request("board_id must belong to the same project")
        task.board_id = board_id

    if column_id is not None:
        if column_id:
            col = db.get(m.BoardColumn, column_id)
            if not col:
                raise _bad_request("column_id not found")
            if task.board_id and col.board_id != task.board_id:
                raise _bad_request("column_id must belong to current board")
            if task.board_id is None:
                task.board_id = col.board_id
        task.column_id = column_id

    if title is not None:
        task.title = title
    if description is not None:
        task.description = description
    if priority is not None:
        task.priority = priority
    if status is not None:
        task.status = status
    if due_date is not None:
        task.due_date = due_date

    if assignee_user_ids is not None:
        # replace assignment set
        db.execute(
            m.TaskAssignment.__table__.delete().where(m.TaskAssignment.task_id == task.id)
        )
        if assignee_user_ids:
            users = db.execute(select(m.User).where(m.User.id.in_(assignee_user_ids))).scalars().all()
            found = {u.id for u in users}
            missing = [str(uid) for uid in assignee_user_ids if uid not in found]
            if missing:
                raise _bad_request(f"Unknown assignees: {missing}")

            for uid in assignee_user_ids:
                db.add(m.TaskAssignment(task_id=task.id, user_id=uid))
                db.add(
                    m.Notification(
                        user_id=uid,
                        type="task",
                        title="Task assignment updated",
                        message=f"You were assigned to task: {task.title}",
                        is_read=False,
                    )
                )

    _update_rollups_for_project(db, task.project_id)
    db.commit()
    db.refresh(task)
    return task


def add_task_comment(db: Session, task_id: UUID, actor_user_id: UUID, body: str) -> m.TaskComment:
    task = get_task(db, task_id, actor_user_id)
    comment = m.TaskComment(task_id=task.id, author_user_id=actor_user_id, body=body)
    db.add(comment)

    # notify assignees
    assignees = db.execute(
        select(m.TaskAssignment.user_id).where(m.TaskAssignment.task_id == task.id)
    ).scalars().all()
    for uid in set(assignees):
        if uid == actor_user_id:
            continue
        db.add(
            m.Notification(
                user_id=uid,
                type="task",
                title="New comment",
                message=f"New comment on task '{task.title}'",
                is_read=False,
            )
        )

    db.commit()
    db.refresh(comment)
    return comment


def list_task_comments(db: Session, task_id: UUID, actor_user_id: UUID) -> List[m.TaskComment]:
    _ = get_task(db, task_id, actor_user_id)
    return (
        db.execute(select(m.TaskComment).where(m.TaskComment.task_id == task_id).order_by(m.TaskComment.created_at.asc()))
        .scalars()
        .all()
    )


def list_notifications(db: Session, actor_user_id: UUID, unread_only: bool, limit: int, offset: int):
    stmt = select(m.Notification).where(m.Notification.user_id == actor_user_id)
    if unread_only:
        stmt = stmt.where(m.Notification.is_read.is_(False))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = (
        db.execute(stmt.order_by(m.Notification.created_at.desc()).limit(limit).offset(offset))
        .scalars()
        .all()
    )
    return items, total


def mark_notification_read(db: Session, notification_id: UUID, actor_user_id: UUID, is_read: bool) -> m.Notification:
    notif = db.get(m.Notification, notification_id)
    if not notif or notif.user_id != actor_user_id:
        raise _not_found("Notification")
    notif.is_read = is_read
    db.commit()
    db.refresh(notif)
    return notif


def _update_rollups_for_project(db: Session, project_id: UUID) -> None:
    # project rollup
    counts = db.execute(
        select(
            func.count().label("total"),
            func.sum(func.case((m.Task.status == "open", 1), else_=0)).label("open"),
            func.sum(func.case((m.Task.status == "in_progress", 1), else_=0)).label("in_progress"),
            func.sum(func.case((m.Task.status == "done", 1), else_=0)).label("done"),
        ).where(m.Task.project_id == project_id)
    ).mappings().one()

    rollup = db.get(m.AnalyticsProjectRollup, project_id)
    if not rollup:
        rollup = m.AnalyticsProjectRollup(project_id=project_id)
        db.add(rollup)

    rollup.total_tasks = int(counts["total"] or 0)
    rollup.open_tasks = int(counts["open"] or 0)
    rollup.in_progress_tasks = int(counts["in_progress"] or 0)
    rollup.done_tasks = int(counts["done"] or 0)

    # team rollup from all projects
    project = db.get(m.Project, project_id)
    if project:
        team_id = project.team_id
        total_projects = db.execute(select(func.count()).select_from(m.Project).where(m.Project.team_id == team_id)).scalar_one()
        team_counts = db.execute(
            select(
                func.count().label("total_tasks"),
                func.sum(func.case((m.Task.status == "done", 1), else_=0)).label("done_tasks"),
            )
            .select_from(m.Task)
            .join(m.Project, m.Project.id == m.Task.project_id)
            .where(m.Project.team_id == team_id)
        ).mappings().one()

        team_rollup = db.get(m.AnalyticsTeamRollup, team_id)
        if not team_rollup:
            team_rollup = m.AnalyticsTeamRollup(team_id=team_id)
            db.add(team_rollup)

        team_rollup.total_projects = int(total_projects or 0)
        team_rollup.total_tasks = int(team_counts["total_tasks"] or 0)
        team_rollup.done_tasks = int(team_counts["done_tasks"] or 0)
