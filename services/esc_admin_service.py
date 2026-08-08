"""ESC Admin triggers (detection / reset / disconnect) for IPR and related suites.

Persists verifiable control-plane state consumed by heartbeat / DPA protection.
No harness fixture DPA names or device IDs are hard-coded.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from models.models import AdminInjectedData
from services.clock import utc_now
from services.meas_report import admin_flag_set

FLAG_ESC_DETECTION = "esc_detection"
FLAG_ESC_DISCONNECTED = "esc_disconnected"
FLAG_ESC_ABSENT = "esc_absent"
KIND_ESC_AUDIT = "esc_admin_audit"


def _append_audit(db: Session, event: str, detail: dict[str, Any]) -> None:
    db.add(
        AdminInjectedData(
            kind=KIND_ESC_AUDIT,
            data_json=json.dumps(
                {
                    "event": event,
                    "at": utc_now().replace(microsecond=0).isoformat(),
                    **detail,
                },
                default=str,
            ),
        )
    )


def _write_flag(db: Session, kind: str, payload: dict[str, Any]) -> None:
    """Upsert flag row without committing (caller owns the transaction)."""
    existing = db.query(AdminInjectedData).filter_by(kind=kind).first()
    raw = json.dumps(payload)
    if existing:
        existing.data_json = raw
    else:
        db.add(AdminInjectedData(kind=kind, data_json=raw))


def apply_esc_detection(db: Session, body: dict[str, Any] | None) -> dict[str, Any]:
    """Record ESC detection event (TriggerEscZone)."""
    payload = dict(body) if isinstance(body, dict) else {}
    payload.setdefault("detected", True)
    payload["updatedAt"] = utc_now().replace(microsecond=0).isoformat()
    _write_flag(db, FLAG_ESC_DETECTION, payload)
    _append_audit(db, "esc_detection", {"keys": sorted(str(k) for k in payload.keys())})
    db.commit()
    return payload


def reset_esc_zone(db: Session) -> None:
    """Clear ESC detection state (ResetEscZone)."""
    db.query(AdminInjectedData).filter_by(kind=FLAG_ESC_DETECTION).delete()
    _append_audit(db, "esc_reset", {})
    db.commit()


def disconnect_esc(db: Session) -> dict[str, Any]:
    """Mark ESC-DE disconnected (TriggerEscDisconnect / IPR)."""
    payload = {
        "disconnected": True,
        "disconnectedAt": utc_now().replace(microsecond=0).isoformat(),
    }
    _write_flag(db, FLAG_ESC_DISCONNECTED, payload)
    _append_audit(db, "esc_disconnect", {})
    db.commit()
    return payload


def is_esc_disconnected(db: Session) -> bool:
    if not admin_flag_set(db, FLAG_ESC_DISCONNECTED):
        return False
    row = db.query(AdminInjectedData).filter_by(kind=FLAG_ESC_DISCONNECTED).first()
    if not row:
        return False
    try:
        data = json.loads(row.data_json or "{}")
    except json.JSONDecodeError:
        # Fail closed for RF: treat corrupt disconnect flag as disconnected.
        return True
    if isinstance(data, dict) and "disconnected" in data:
        return bool(data.get("disconnected"))
    return True


def set_esc_absent(db: Session, *, absent: bool = True) -> dict[str, Any]:
    """Mark that no ESC is present (IPR.1 — protect all ESC-monitored DPAs)."""
    if not absent:
        db.query(AdminInjectedData).filter_by(kind=FLAG_ESC_ABSENT).delete()
        _append_audit(db, "esc_absent_cleared", {})
        db.commit()
        return {"absent": False}
    payload = {
        "absent": True,
        "updatedAt": utc_now().replace(microsecond=0).isoformat(),
    }
    _write_flag(db, FLAG_ESC_ABSENT, payload)
    _append_audit(db, "esc_absent", {})
    db.commit()
    return payload


def is_esc_absent(db: Session) -> bool:
    if not admin_flag_set(db, FLAG_ESC_ABSENT):
        return False
    row = db.query(AdminInjectedData).filter_by(kind=FLAG_ESC_ABSENT).first()
    if not row:
        return False
    try:
        data = json.loads(row.data_json or "{}")
    except json.JSONDecodeError:
        return True
    if isinstance(data, dict) and "absent" in data:
        return bool(data.get("absent"))
    return True


def esc_detection_active(db: Session) -> bool:
    return bool(admin_flag_set(db, FLAG_ESC_DETECTION))
