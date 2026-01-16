from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.models import User
from src.schemas.common import Page, PageMeta
from src.schemas.notifications import NotificationMarkRead, NotificationOut
from src.services.auth import get_current_user
from src.services.domain import list_notifications, mark_notification_read

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=Page[NotificationOut],
    summary="List notifications",
    description="Lists the current user's notifications (paginated).",
)
def list_notifications_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    unread_only: bool = Query(False, description="If true, return unread notifications only."),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[NotificationOut]:
    items, total = list_notifications(db, user.id, unread_only=unread_only, limit=limit, offset=offset)
    return Page(
        items=[
            NotificationOut(
                id=n.id,
                user_id=n.user_id,
                type=n.type,
                title=n.title,
                message=n.message,
                is_read=n.is_read,
                created_at=n.created_at,
            )
            for n in items
        ],
        meta=PageMeta(limit=limit, offset=offset, total=int(total)),
    )


@router.patch(
    "/{notification_id}",
    response_model=NotificationOut,
    summary="Mark notification read/unread",
    description="Updates is_read for a notification belonging to the current user.",
)
def mark_notification(
    notification_id: UUID,
    payload: NotificationMarkRead,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationOut:
    n = mark_notification_read(db, notification_id, user.id, is_read=payload.is_read)
    return NotificationOut(
        id=n.id,
        user_id=n.user_id,
        type=n.type,
        title=n.title,
        message=n.message,
        is_read=n.is_read,
        created_at=n.created_at,
    )
