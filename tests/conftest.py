"""Ensure the repository root is importable and provide shared pytest fixtures."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Import after sys.path fix.
import database  # noqa: E402
from database import init_db, rebind_engine  # noqa: E402
from tests.fixtures.factories import reset_factory_counter  # noqa: E402


@pytest.fixture
def repo_root() -> Path:
    return _ROOT


@pytest.fixture
def frozen_time():
    """Deterministic clock for tests (freezegun; prefer UTC-aware assertions)."""
    freezegun = pytest.importorskip("freezegun")
    with freezegun.freeze_time("2026-08-05T15:00:00+00:00"):
        yield


@pytest.fixture(autouse=True)
def _deterministic_haat_provider() -> Iterator[None]:
    """Unit/integration default: flat terrain (norm HAAT = 0) without NED tiles.

    Certification / REG.7 must inject or resolve the real NED-backed provider
    via ``SAS_TERRAIN_DIR``; this fixture keeps local pytest independent of
    the multi-GB USGS dataset.
    """
    from services.terrain import DeterministicHaatProvider, reset_haat_provider, set_haat_provider

    set_haat_provider(DeterministicHaatProvider(default_norm_haat_m=0.0))
    try:
        yield
    finally:
        reset_haat_provider()


@pytest.fixture
def db_session(tmp_path: Path) -> Iterator[Session]:
    """Isolated SQLite database rebound for a single test."""
    previous_url = str(database.engine.url)
    reset_factory_counter()
    db_path = tmp_path / "sas_test.db"
    url = f"sqlite:///{db_path}"
    rebind_engine(url)
    init_db(retries=1, delay_seconds=0)
    session = database.SessionLocal()
    try:
        yield session
    finally:
        session.close()
        rebind_engine(previous_url)
        # Keep process-default schema intact for module-level TestClient suites.
        init_db(retries=1, delay_seconds=0)
