"""Central ORM model registration for ``Base.metadata.create_all``.

Importing this module (or calling ``load_all_models``) ensures every mapped
table is attached to ``models.base.Base`` before schema initialization.
"""

from __future__ import annotations

from models.base import Base
from models.models import (
    AdminInjectedData,
    BlacklistedFccId,
    BlacklistedFccIdSerial,
    Cbsd,
    ConditionalRegistration,
    CpiUser,
    EscSensor,
    FadDump,
    FadFile,
    FccIdRecord,
    Grant,
    PalRecord,
    PeerFadRecord,
    PeerSas,
    UserIdRecord,
)

# Explicit registry: keep in sync when adding ORM tables.
MODEL_MODULES: tuple[object, ...] = (
    AdminInjectedData,
    BlacklistedFccId,
    BlacklistedFccIdSerial,
    Cbsd,
    ConditionalRegistration,
    CpiUser,
    EscSensor,
    FadDump,
    FadFile,
    FccIdRecord,
    Grant,
    PalRecord,
    PeerFadRecord,
    PeerSas,
    UserIdRecord,
)

# Tables required for Admin / Registration protocol paths (CI regression).
REQUIRED_TABLES: frozenset[str] = frozenset(
    {
        "admin_injected_data",
        "blacklisted_fcc_ids",
        "blacklisted_fcc_id_serials",
        "cbsds",
        "conditional_registrations",
        "cpi_users",
        "esc_sensors",
        "fad_dumps",
        "fad_files",
        "fcc_ids",
        "grants",
        "pal_records",
        "peer_fad_records",
        "peer_sas",
        "user_ids",
    }
)


def load_all_models() -> None:
    """Force-import all mapped classes onto ``Base.metadata``."""
    # Touching the registry tuple keeps imports live under linters / trees shaking.
    if not MODEL_MODULES:
        raise RuntimeError("ORM model registry is empty")
    missing = REQUIRED_TABLES - set(Base.metadata.tables)
    if missing:
        raise RuntimeError(
            "ORM metadata incomplete after model import; missing tables: "
            + ", ".join(sorted(missing))
        )


def expected_table_names() -> frozenset[str]:
    load_all_models()
    return frozenset(Base.metadata.tables)
