"""Alembic helpers for process-bound engines (P8-002).

Transactional isolation (documented):
- SQLAlchemy ``SessionLocal`` uses ``autocommit=False`` / ``autoflush=False``.
- Request sessions (``get_db``) roll back on exception and close in ``finally``.
- Default isolation is the database default (PostgreSQL ``READ COMMITTED``,
  SQLite serializable-ish file lock). Protocol mutations that must be atomic
  commit explicitly inside the domain service or route.
- Admin ``/reset`` drops/recreates schema under ``_init_lock``; callers must
  not hold an open request Session across that boundary.

Schema application:
- Default: ``alembic upgrade head``.
- Fast path for local pytest: set ``SAS_SCHEMA_VIA_CREATE_ALL=1`` to use
  ``Base.metadata.create_all`` then ``stamp head`` (models must stay aligned
  with ``alembic/versions``; covered by upgrade/downgrade unit tests).
"""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ALEMBIC_INI = _REPO_ROOT / "alembic.ini"
HEAD_REVISION = "20260808_0001"


def alembic_config(database_url: str) -> Config:
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", database_url)
    cfg.set_main_option("script_location", str(_REPO_ROOT / "alembic"))
    return cfg


def upgrade_head(*, database_url: str) -> None:
    command.upgrade(alembic_config(database_url), "head")


def downgrade_base(*, database_url: str) -> None:
    command.downgrade(alembic_config(database_url), "base")


def stamp_head(*, database_url: str) -> None:
    command.stamp(alembic_config(database_url), "head")


def current_revision(*, database_url: str) -> str | None:
    """Return the current alembic revision id, or None if unversioned."""
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import create_engine

    engine = create_engine(database_url)
    try:
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            return context.get_current_revision()
    finally:
        engine.dispose()


def _schema_via_create_all() -> bool:
    return os.environ.get("SAS_SCHEMA_VIA_CREATE_ALL", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def database_url_for_alembic(engine: Engine) -> str:
    """Return a migration URL that keeps credentials.

    ``str(engine.url)`` redacts passwords as ``***``, which breaks PostgreSQL
    auth when Alembic opens a second connection.
    """
    return engine.url.render_as_string(hide_password=False)


def apply_schema(engine: Engine) -> None:
    """Bring ``engine`` to Alembic head.

    - Empty DB → ``upgrade head`` (or create_all+stamp when fast-path enabled).
    - Legacy DB with all required tables and no ``alembic_version`` → stamp head.
    - Legacy DB missing required tables → ``create_all`` then stamp (do not
      stamp an incomplete schema).
    - Versioned DB → ``upgrade head``.
    """
    from models.base import Base
    from models.registry import REQUIRED_TABLES

    url = database_url_for_alembic(engine)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "alembic_version" not in tables and tables:
        if REQUIRED_TABLES <= tables:
            stamp_head(database_url=url)
            return
        # Incomplete pre-Alembic DB: materialize missing tables, then stamp.
        Base.metadata.create_all(bind=engine)
        stamp_head(database_url=url)
        return
    if not tables and _schema_via_create_all():
        Base.metadata.create_all(bind=engine)
        stamp_head(database_url=url)
        return
    upgrade_head(database_url=url)
