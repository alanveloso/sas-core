"""CPAS / peer FAD sync — UUT acts as SAS↔SAS client during daily activities."""

from __future__ import annotations

import json
import logging
import threading
from typing import Any

from sqlalchemy.orm import Session

from models.models import Cbsd, Grant, PeerFadRecord
from services.fad_client_service import run_peer_fad_sync
from services.fad_service import fad_cbsd_id
from services.meas_report import clear_admin_flags, set_admin_flag

logger = logging.getLogger(__name__)

FLAG_CPAS_RUNNING = "cpas_running"
_cpas_dispatch_lock = threading.RLock()


def is_cpas_running(db: Session) -> bool:
    from services.meas_report import admin_flag_set

    return admin_flag_set(db, FLAG_CPAS_RUNNING)


def get_daily_activities_completed(db: Session) -> bool:
    """Harness async contract: completed=true only when CPAS is not running."""
    return not is_cpas_running(db)


def _clear_cpas_running_flag(db: Session) -> None:
    try:
        clear_admin_flags(db, FLAG_CPAS_RUNNING)
    except Exception:
        logger.exception("Failed to clear CPAS running flag")
        try:
            db.rollback()
        except Exception:
            logger.exception("Failed to rollback after CPAS flag clear error")


def trigger_daily_activities(db: Session) -> None:
    """Start CPAS once.

    - ``production``: enqueue Celery ``run_cpas`` (requires broker/worker).
    - ``certification``: run the same ``execute_cpas_pipeline`` in-process
      without a broker, on a worker thread so ``/get_daily_activities_status``
      can still observe ``completed=false`` while CPAS runs.

    Duplicate calls while CPAS is already running are no-ops.
    """
    from config import get_settings

    with _cpas_dispatch_lock:
        if is_cpas_running(db):
            return

        set_admin_flag(db, FLAG_CPAS_RUNNING)
        mode = get_settings().sas_execution_mode

        if mode == "production":
            try:
                from tasks import run_cpas

                run_cpas.delay()
            except Exception:
                logger.exception(
                    "Failed to enqueue CPAS Celery task; clearing running flag"
                )
                _clear_cpas_running_flag(db)
                raise
            return

        # certification: claim under the lock, then run domain logic off-request.
        try:
            worker = threading.Thread(
                target=_run_certification_cpas,
                name="cpas-certification",
                daemon=True,
            )
            worker.start()
        except Exception:
            logger.exception("Failed to start certification CPAS thread")
            _clear_cpas_running_flag(db)
            raise


def _run_certification_cpas() -> None:
    """In-process CPAS worker for certification mode (same domain pipeline)."""
    from database import SessionLocal

    session = SessionLocal()
    try:
        execute_cpas_pipeline(session)
    except Exception:
        logger.exception("CPAS certification-mode pipeline failed")
        try:
            session.rollback()
        except Exception:
            logger.exception("Failed to rollback certification CPAS session")
    finally:
        _clear_cpas_running_flag(session)
        session.close()


def execute_cpas_pipeline(db: Session) -> None:
    """Synchronous CPAS body shared by Celery workers and certification mode."""
    from services.cpas_schedule_service import mark_scheduled_success_if_applicable
    from services.database_sync_service import sync_injected_database_urls

    sync_injected_database_urls(db)
    run_peer_fad_sync(db)
    apply_peer_conflict_to_local_grants(db)
    mark_scheduled_success_if_applicable(db)


def _peer_cbsd_records(db: Session) -> list[dict[str, Any]]:
    rows = db.query(PeerFadRecord).filter_by(record_type="cbsd").all()
    out: list[dict[str, Any]] = []
    for row in rows:
        try:
            data = json.loads(row.data_json or "{}")
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            out.append(data)
    return out


def _active_peer_grants(record: dict[str, Any]) -> list[dict[str, Any]]:
    grants = record.get("grants") or []
    if not isinstance(grants, list):
        return []
    active: list[dict[str, Any]] = []
    for g in grants:
        if not isinstance(g, dict):
            continue
        if g.get("terminated") is True:
            continue
        active.append(g)
    return active


def peer_has_grant_for_cbsd(db: Session, cbsd: Cbsd) -> bool:
    """True when any peer FAD CBSD record matches this local CBSD and has an active grant."""
    target_id = fad_cbsd_id(cbsd.fcc_id, cbsd.cbsd_serial_number)
    for record in _peer_cbsd_records(db):
        if record.get("id") != target_id:
            continue
        if _active_peer_grants(record):
            return True
    return False


def _peer_esc_params() -> tuple[float, int, int]:
    from spectrum_profiles.context import get_active_profile

    profile = get_active_profile()
    rule = profile.get_protection("peer_esc")
    if rule and rule.enabled:
        radius_m = float(rule.params.get("radius_m", 40_000.0))
        low = int(rule.params.get("low_hz", profile.band_plan.low_hz))
        high = int(rule.params.get("high_hz", profile.band_plan.high_hz))
        return radius_m, low, high
    bp = profile.band_plan
    return 40_000.0, bp.low_hz, bp.high_hz


def _peer_ppa_buffer_m() -> float:
    from spectrum_profiles.context import get_active_profile

    rule = get_active_profile().get_protection("peer_ppa")
    if rule and rule.enabled:
        return float(rule.params.get("buffer_m", 1_000.0))
    return 1_000.0


def _peer_records_of_type(db: Session, record_type: str) -> list[dict[str, Any]]:
    rows = db.query(PeerFadRecord).filter_by(record_type=record_type).all()
    out: list[dict[str, Any]] = []
    for row in rows:
        try:
            data = json.loads(row.data_json or "{}")
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            out.append(data)
    return out


def _cbsd_lat_lon(cbsd: Cbsd) -> tuple[float | None, float | None]:
    from services.spectrum_inquiry_service import _cbsd_location

    return _cbsd_location(cbsd)


def _freq_overlaps(a_low: int, a_high: int, b_low: int, b_high: int) -> bool:
    return a_low < b_high and a_high > b_low


def _ppa_protected_ranges(db: Session, ppa: dict[str, Any]) -> list[tuple[int, int]]:
    """Resolve PPA-protected frequencies via linked local PAL records."""
    from services.spectrum_inquiry_service import _load_injected, _pal_freq

    ppa_info = ppa.get("ppaInfo") or {}
    pal_ids = ppa_info.get("palId") or []
    if not pal_ids:
        return []
    pals = _load_injected(db, "pal")
    pal_by_id = {p.get("palId"): p for p in pals if p.get("palId")}
    ranges: list[tuple[int, int]] = []
    for pal_id in pal_ids:
        pal = pal_by_id.get(pal_id)
        if not pal:
            continue
        pf = _pal_freq(pal)
        if pf:
            ranges.append(pf)
    return ranges


def _grant_conflicts_peer_ppa(db: Session, cbsd: Cbsd, grant: Grant) -> bool:
    """True when CBSD is in/near a peer PPA and the grant overlaps the PPA PAL band."""
    from services.geometry import within_geojson_buffer_m

    lat, lon = _cbsd_lat_lon(cbsd)
    if lat is None or lon is None:
        return False
    buffer_m = _peer_ppa_buffer_m()
    for record in _peer_records_of_type(db, "zone"):
        if record.get("usage") != "PPA" and "ppaInfo" not in record:
            continue
        if record.get("terminated") is True:
            continue
        if not within_geojson_buffer_m(lat, lon, record.get("zone"), buffer_m):
            continue
        for low, high in _ppa_protected_ranges(db, record):
            if _freq_overlaps(grant.low_frequency, grant.high_frequency, low, high):
                return True
    return False


def _grant_conflicts_peer_esc(db: Session, cbsd: Cbsd, grant: Grant) -> bool:
    """True when CBSD is within ESC protection distance of a peer ESC sensor."""
    from services.geometry import haversine_m

    esc_radius_m, esc_low, esc_high = _peer_esc_params()
    if not _freq_overlaps(
        grant.low_frequency, grant.high_frequency, esc_low, esc_high
    ):
        return False
    lat, lon = _cbsd_lat_lon(cbsd)
    if lat is None or lon is None:
        return False
    for record in _peer_records_of_type(db, "esc_sensor"):
        inst = record.get("installationParam") or {}
        esc_lat, esc_lon = inst.get("latitude"), inst.get("longitude")
        if esc_lat is None or esc_lon is None:
            continue
        if haversine_m(lat, lon, float(esc_lat), float(esc_lon)) <= esc_radius_m:
            return True
    return False


def apply_peer_conflict_to_local_grants(db: Session) -> None:
    """Terminate local grants that conflict with peer FAD (same CBSD, PPA, or ESC).

    - Same-CBSD active peer grant → GRA_5 / GRA_6.
    - Inside peer PPA + frequency overlap with linked PAL → FAD_2 (G4).
    - Near peer ESC sensor + CBRS overlap → FAD_2 (G2).
    """
    changed = False
    for cbsd in db.query(Cbsd).all():
        grants = (
            db.query(Grant)
            .filter_by(cbsd_id=cbsd.cbsd_id, terminated=False)
            .all()
        )
        if not grants:
            continue
        same_cbsd = peer_has_grant_for_cbsd(db, cbsd)
        for grant in grants:
            if same_cbsd or _grant_conflicts_peer_ppa(db, cbsd, grant) or _grant_conflicts_peer_esc(
                db, cbsd, grant
            ):
                grant.terminated = True
                changed = True
    if changed:
        db.commit()
