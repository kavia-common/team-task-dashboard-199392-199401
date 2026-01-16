import os
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker


def _default_db_connection_file() -> Path:
    """
    Returns the expected path to db_connection.txt based on the monorepo layout.

    task_management_backend (this container) lives in:
      team-task-dashboard-199392-199401/task_management_backend

    task_management_database lives in:
      team-task-dashboard-199392-199403/task_management_database

    We use relative traversal from this file to avoid hardcoding absolute paths.
    """
    # .../task_management_backend/src/db/session.py
    backend_container_root = Path(__file__).resolve().parents[3]
    # .../code-generation/team-task-dashboard-199392-199401/task_management_backend
    monorepo_root = backend_container_root.parents[1]
    # .../code-generation
    return (
        monorepo_root
        / "team-task-dashboard-199392-199403"
        / "task_management_database"
        / "db_connection.txt"
    )


def _read_db_url_from_db_connection_txt(path: Path) -> str:
    """
    Reads db_connection.txt which typically contains a `psql postgresql://...` command,
    and returns the extracted SQLAlchemy-compatible database URL.

    Expected formats:
      - psql postgresql://user:pass@host:port/dbname
      - postgresql://user:pass@host:port/dbname
    """
    if not path.exists():
        raise RuntimeError(
            f"Database connection file not found at {path}. "
            "Ensure task_management_database/db_connection.txt exists."
        )

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise RuntimeError(f"Database connection file {path} is empty.")

    # Accept either "psql postgresql://..." or direct URL
    parts = raw.split()
    url = parts[-1] if parts else raw
    if not (url.startswith("postgresql://") or url.startswith("postgres://")):
        raise RuntimeError(
            f"Unrecognized db_connection.txt content: {raw}. "
            "Expected a psql command or a postgresql:// URL."
        )

    # SQLAlchemy expects postgresql:// scheme; psycopg2 supports it.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """
    Creates and memoizes a SQLAlchemy Engine for the whole app.

    Uses DB URL from task_management_database/db_connection.txt by default.

    Env overrides (optional):
      - DATABASE_URL: directly specify a SQLAlchemy database URL
      - DB_CONNECTION_FILE: point to a different db_connection.txt file
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        conn_file = Path(os.getenv("DB_CONNECTION_FILE") or _default_db_connection_file())
        db_url = _read_db_url_from_db_connection_txt(conn_file)

    # Connection pool defaults are fine for this app; enable pre_ping for resiliency.
    return create_engine(db_url, pool_pre_ping=True)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


# PUBLIC_INTERFACE
def get_db():
    """FastAPI dependency that yields a DB session and guarantees cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
