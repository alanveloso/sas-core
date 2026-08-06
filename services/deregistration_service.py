"""Deregistration business logic aligned with WINNF_FT_S_DRG expectations."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.models import Cbsd, Grant

SUCCESS = 0
MISSING_PARAM = 102
INVALID_PARAM = 103


def _resp(code: int, *, cbsd_id: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"response": {"responseCode": code}}
    if cbsd_id is not None:
        out["cbsdId"] = cbsd_id
    return out


def process_deregistration(
    db: Session,
    requests: list[dict[str, Any]],
    *,
    certificate_hash: str | None = None,
) -> list[dict[str, Any]]:
    from services.cbsd_auth import cbsd_certificate_mismatch

    responses: list[dict[str, Any]] = []

    for req in requests:
        cbsd_id = req.get("cbsdId")
        if not cbsd_id:
            responses.append(_resp(MISSING_PARAM))
            continue

        cbsd = db.query(Cbsd).filter_by(cbsd_id=cbsd_id).first()
        if not cbsd:
            # Already deregistered or unknown → 103 without echoing cbsdId (DRG_3/4).
            responses.append(_resp(INVALID_PARAM))
            continue

        # Wrong client cert for this cbsdId → 103 without echoing cbsdId.
        if cbsd_certificate_mismatch(cbsd, certificate_hash):
            responses.append(_resp(INVALID_PARAM))
            continue

        from services.lifecycle import (
            CbsdEvent,
            CbsdState,
            GrantEvent,
            apply_grant_event,
            evaluate_cbsd_transition,
            resolve_cbsd_state,
        )

        outcome = evaluate_cbsd_transition(
            CbsdEvent.DEREGISTER,
            current=resolve_cbsd_state(cbsd),
            payload={"cbsdId": cbsd_id},
        )
        if not outcome.ok:
            responses.append(_resp(outcome.response_code))
            continue

        # Invalidate grants immediately, then remove the CBSD registration.
        # Cascade delete-orphan also removes Grant rows so re-registration cannot
        # reuse old grantIds (DRG_5) and new Grants for this cbsdId return 103 (DRG_1).
        for grant in db.query(Grant).filter_by(cbsd_id=cbsd_id).all():
            apply_grant_event(
                grant,
                GrantEvent.TERMINATE,
                payload={"cbsdId": cbsd_id, "grantId": grant.grant_id},
            )
        cbsd.lifecycle_state = CbsdState.DEREGISTERED.value
        db.delete(cbsd)
        responses.append(_resp(SUCCESS, cbsd_id=cbsd_id))

    db.commit()
    return responses
