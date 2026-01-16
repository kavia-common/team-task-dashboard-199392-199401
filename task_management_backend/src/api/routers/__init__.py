from src.api.routers.analytics import router as analytics_router
from src.api.routers.auth import router as auth_router
from src.api.routers.boards import router as boards_router
from src.api.routers.notifications import router as notifications_router
from src.api.routers.tasks import router as tasks_router
from src.api.routers.teams import router as teams_router

__all__ = [
    "auth_router",
    "teams_router",
    "boards_router",
    "tasks_router",
    "analytics_router",
    "notifications_router",
]
