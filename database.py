"""SQLAlchemy engine and session helpers (PostgreSQL in production, SQLite locally)."""

from __future__ import annotations

import logging
import threading
import time

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()

_engine_kwargs: dict = {
    "echo": _settings.db_echo,
}
if _settings.is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs.update(
        {
            "pool_size": _settings.db_pool_size,
            "max_overflow": _settings.db_max_overflow,
            "pool_timeout": _settings.db_pool_timeout,
            "pool_recycle": _settings.db_pool_recycle,
            "pool_pre_ping": _settings.db_pool_pre_ping,
        }
    )

engine = create_engine(_settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_init_lock = threading.Lock()


def rebind_engine(database_url: str, *, echo: bool = False) -> None:
    """Replace the process-wide engine/session factory.

    Intended for isolated test databases. Callers that did
    ``from database import SessionLocal`` keep the old binding; prefer
    ``database.SessionLocal`` after rebind, or use the ``db_session`` fixture.
    """
    global engine, SessionLocal

    kwargs: dict = {"echo": echo}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs.update(
            {
                "pool_size": _settings.db_pool_size,
                "max_overflow": _settings.db_max_overflow,
                "pool_timeout": _settings.db_pool_timeout,
                "pool_recycle": _settings.db_pool_recycle,
                "pool_pre_ping": _settings.db_pool_pre_ping,
            }
        )
    with _init_lock:
        previous = engine
        engine = create_engine(database_url, **kwargs)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        previous.dispose()


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db(*, retries: int = 10, delay_seconds: float = 2.0) -> None:
    """Create tables, retrying briefly while PostgreSQL becomes ready."""
    from models import models  # noqa: F401

    with _init_lock:
        last_exc: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                Base.metadata.create_all(bind=engine)
                _ensure_lifecycle_columns(engine)
                return
            except OperationalError as exc:
                last_exc = exc
                message = str(exc).lower()
                # Concurrent create_all can race on SQLite ("table already exists").
                if "already exists" in message:
                    _ensure_lifecycle_columns(engine)
                    return
                logger.warning(
                    "init_db attempt %s/%s failed: %s", attempt, retries, exc
                )
                if attempt < retries:
                    time.sleep(delay_seconds)
        if last_exc is not None:
            raise last_exc


def _ensure_lifecycle_columns(bind) -> None:
    """Add lifecycle_state columns on existing DBs (create_all does not ALTER)."""
    from sqlalchemy import inspect, text

    inspector = inspect(bind)
    statements: list[str] = []
    if "cbsds" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("cbsds")}
        if "lifecycle_state" not in cols:
            statements.append(
                "ALTER TABLE cbsds ADD COLUMN lifecycle_state VARCHAR(32) "
                "DEFAULT 'REGISTERED' NOT NULL"
            )
    if "grants" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("grants")}
        if "lifecycle_state" not in cols:
            statements.append(
                "ALTER TABLE grants ADD COLUMN lifecycle_state VARCHAR(32) "
                "DEFAULT 'GRANTED' NOT NULL"
            )
    if not statements:
        return
    with bind.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
    logger.info("Applied lifecycle schema patches: %s", statements)


def reset_db() -> None:
    """Drop and recreate all tables (admin/reset)."""
    from models import models  # noqa: F401

    with _init_lock:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
