from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import (
    analytics_router,
    auth_router,
    boards_router,
    notifications_router,
    tasks_router,
    teams_router,
)

openapi_tags = [
    {"name": "auth", "description": "Registration, login, JWT identity."},
    {"name": "teams", "description": "Teams and team memberships."},
    {"name": "boards", "description": "Projects, boards, and board columns."},
    {"name": "tasks", "description": "Task CRUD, assignment, and comments."},
    {"name": "analytics", "description": "Aggregated analytics rollups."},
    {"name": "notifications", "description": "User notifications and read status."},
]


app = FastAPI(
    title="Task Management Backend API",
    description=(
        "Backend for task management dashboards: auth/roles, teams, kanban boards, tasks, analytics, notifications.\n\n"
        "Authentication: obtain a JWT via POST /auth/login and pass it as:\n"
        "  Authorization: Bearer <token>\n"
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# NOTE: For production, set allow_origins to the deployed frontend URL(s).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/",
    tags=["auth"],
    summary="Health check",
    description="Basic health check endpoint.",
)
def health_check():
    """Health check endpoint for container uptime monitoring."""
    return {"message": "Healthy"}


app.include_router(auth_router)
app.include_router(teams_router)
app.include_router(boards_router)
app.include_router(tasks_router)
app.include_router(analytics_router)
app.include_router(notifications_router)
