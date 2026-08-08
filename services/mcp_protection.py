"""Multi-constraint IAP + DPA protection orchestration (P7-005 MCP.1).

When IAP points and coupling are available, CPAS evaluates IAP first, then
recomputes DPA movelists with effective EIRPs so outcomes jointly satisfy both
constraint families. Without IAP inputs, behaviour matches peer + DPA only.

CPAS/MCP always shares one frozen generation (``CpasSnapshot``) for local
grants, peer FAD, IAP and DPA.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def resolve_iap_points(
    db: Session,
    iap_points: Sequence[Any] | None,
    *,
    build_from_db: bool = True,
) -> list[Any]:
    """Return explicit points, or build from injected entities when enabled."""
    if iap_points is not None:
        return list(iap_points)
    if not build_from_db:
        return []
    from services.iap.protection_points import build_protection_points_from_db

    return list(build_protection_points_from_db(db))


def effective_eirp_by_grant_id(
    decisions: Sequence[Any],
) -> dict[str, float]:
    """Map grant_id → authorized EIRP for IAP reduce_power decisions."""
    out: dict[str, float] = {}
    for d in decisions:
        action = getattr(d, "action", None)
        if action != "reduce_power":
            continue
        eirp = getattr(d, "authorized_eirp_dbm_mhz", None)
        gid = getattr(d, "grant_id", None)
        if gid is None or eirp is None:
            continue
        out[str(gid)] = float(eirp)
    return out


def iap_terminated_grant_ids(decisions: Sequence[Any]) -> set[str]:
    return {
        str(d.grant_id)
        for d in decisions
        if getattr(d, "action", None) == "terminate"
        and getattr(d, "reason", None) == "iap"
        and getattr(d, "grant_id", None) is not None
    }


def merge_constraint_decisions(
    peer: Sequence[Any],
    iap: Sequence[Any],
    dpa: Sequence[Any],
) -> list[Any]:
    """Merge peer / IAP / DPA decisions with terminate taking precedence per grant."""
    by_pk: dict[int, Any] = {}
    order: list[int] = []

    def _consider(decision: Any) -> None:
        pk = getattr(decision, "grant_pk", None)
        if pk is None:
            return
        pk_i = int(pk)
        existing = by_pk.get(pk_i)
        if existing is None:
            by_pk[pk_i] = decision
            order.append(pk_i)
            return
        # terminate wins over reduce_power / keep
        if getattr(decision, "action", None) == "terminate":
            by_pk[pk_i] = decision
        elif (
            getattr(existing, "action", None) != "terminate"
            and getattr(decision, "action", None) == "reduce_power"
        ):
            by_pk[pk_i] = decision

    for group in (peer, iap, dpa):
        for d in group:
            _consider(d)
    return [by_pk[pk] for pk in order]


def log_iap_skip_without_coupling(point_count: int) -> None:
    if point_count > 0:
        logger.info(
            "MCP: %d IAP protection point(s) present but no coupling; "
            "skipping IAP (DPA/peer still apply)",
            point_count,
        )
