"""CPAS / peer FAD sync — UUT acts as SAS↔SAS client during daily activities.

P5-003 transactional pipeline:

1. sync external databases;
2. obtain/validate peer FADs;
3. freeze active-grant snapshot;
4. evaluate protections (peer CBSD / PPA / ESC);
5. apply grant decisions + publish FAD in one durable critical section;
6. update schedule status and append audit log.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from models.models import AdminInjectedData, Cbsd, Grant, PeerFadRecord
from services.clock import utc_now
from services.concurrency import acquire_cpas_pipeline_xact_lock
from services.fad_client_service import run_peer_fad_sync
from services.fad_service import create_full_activity_dump, fad_cbsd_id
from services.meas_report import clear_admin_flags, set_admin_flag

logger = logging.getLogger(__name__)

FLAG_CPAS_RUNNING = "cpas_running"
KIND_CPAS_AUDIT = "cpas_pipeline_audit"
_cpas_dispatch_lock = threading.RLock()
_cpas_pipeline_lock = threading.RLock()  # SQLite / same-process aid


@dataclass(frozen=True)
class CpasSnapshot:
    """Frozen view of local grants + peer sync inputs used for decisions."""

    frozen_at: str
    active_grant_pks: tuple[int, ...]
    peer_sync_report: dict[str, Any] = field(default_factory=dict)
    peer_record_count: int = 0
    # Durable peer FAD rows at freeze time:
    # (peer_sas_id, record_type, record_id, data_json).
    # Evaluation must use this set so mid-run peer N→N+1 cannot widen decisions.
    peer_records: tuple[tuple[int, str, str, str], ...] = ()


@dataclass(frozen=True)
class CpasDecision:
    grant_pk: int
    grant_id: str
    cbsd_id: str
    reason: str
    # P6-004: IAP / protection action. Boolean peer rules use terminate.
    action: str = "terminate"
    authorized_eirp_dbm_mhz: float | None = None
    explanation: str = ""


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


def _append_cpas_audit(db: Session, event: str, detail: dict[str, Any]) -> None:
    db.add(
        AdminInjectedData(
            kind=KIND_CPAS_AUDIT,
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


def freeze_cpas_snapshot(
    db: Session, peer_sync_report: dict[str, Any] | None = None
) -> CpasSnapshot:
    """Capture active grant PKs and peer FAD rows; decisions only use this set."""
    # SessionLocal uses autoflush=False; pending peer/grant rows must be visible.
    db.flush()
    rows = (
        db.query(Grant.id)
        .filter_by(terminated=False)
        .order_by(Grant.id)
        .all()
    )
    peer_rows = (
        db.query(PeerFadRecord)
        .order_by(PeerFadRecord.peer_sas_id, PeerFadRecord.record_type, PeerFadRecord.id)
        .all()
    )
    peer_records = tuple(
        (int(row.peer_sas_id), row.record_type, row.record_id, row.data_json)
        for row in peer_rows
    )
    return CpasSnapshot(
        frozen_at=utc_now().replace(microsecond=0).isoformat(),
        active_grant_pks=tuple(int(r[0]) for r in rows),
        peer_sync_report=dict(peer_sync_report or {}),
        peer_record_count=len(peer_records),
        peer_records=peer_records,
    )


def _frozen_peer_records(
    snapshot: CpasSnapshot, record_type: str
) -> list[dict[str, Any]]:
    """Parse peer records of one type from the frozen snapshot (not live DB)."""
    out: list[dict[str, Any]] = []
    for _peer_sas_id, rt, _record_id, data_json in snapshot.peer_records:
        if rt != record_type:
            continue
        try:
            data = json.loads(data_json or "{}")
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            out.append(data)
    return out


def _frozen_peer_cbsd_rows(
    snapshot: CpasSnapshot,
) -> list[tuple[int, dict[str, Any]]]:
    """Frozen peer CBSD records with owning peer_sas_id (not live DB)."""
    out: list[tuple[int, dict[str, Any]]] = []
    for peer_sas_id, rt, _record_id, data_json in snapshot.peer_records:
        if rt != "cbsd":
            continue
        try:
            data = json.loads(data_json or "{}")
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            out.append((int(peer_sas_id), data))
    return out


def evaluate_cpas_protections(
    db: Session,
    snapshot: CpasSnapshot,
    *,
    iap_points: list[Any] | None = None,
    iap_coupling: Any | None = None,
) -> list[CpasDecision]:
    """Compute grant decisions against the frozen snapshot (no DB writes).

    Boolean peer rules (same CBSD / PPA / ESC) still terminate. Optional IAP
    points (P6-004) may keep, reduce_power, or terminate remaining grants.
    """
    if not snapshot.active_grant_pks:
        return []
    peer_cbsd = _frozen_peer_records(snapshot, "cbsd")
    peer_zones = _frozen_peer_records(snapshot, "zone")
    peer_esc = _frozen_peer_records(snapshot, "esc_sensor")
    decisions: list[CpasDecision] = []
    decided_pks: set[int] = set()
    grants = (
        db.query(Grant)
        .filter(Grant.id.in_(snapshot.active_grant_pks))
        .order_by(Grant.id)
        .all()
    )
    for grant in grants:
        if grant.terminated:
            continue
        cbsd = db.query(Cbsd).filter_by(cbsd_id=grant.cbsd_id).first()
        if cbsd is None:
            continue
        reason: str | None = None
        if peer_has_grant_for_cbsd(db, cbsd, peer_cbsd_records=peer_cbsd):
            reason = "peer_same_cbsd_grant"
        elif _grant_conflicts_peer_ppa(db, cbsd, grant, peer_zones):
            reason = "peer_ppa"
        elif _grant_conflicts_peer_esc(db, cbsd, grant, peer_esc):
            reason = "peer_esc"
        if reason:
            decisions.append(
                CpasDecision(
                    grant_pk=grant.id,
                    grant_id=grant.grant_id,
                    cbsd_id=grant.cbsd_id,
                    reason=reason,
                    action="terminate",
                    explanation=reason,
                )
            )
            decided_pks.add(grant.id)

    # Rel1Ext IPR: refresh DPA move-lists and terminate grants still on them.
    from services.dpa_protection import grant_on_any_movelist, refresh_activation_movelists
    from services.propagation.errors import PropagationUnavailableError
    from services.terrain.exceptions import TerrainError

    try:
        refresh_activation_movelists(db, commit=False)
        for grant in grants:
            if grant.id in decided_pks or grant.terminated:
                continue
            if grant_on_any_movelist(db, grant.grant_id):
                decisions.append(
                    CpasDecision(
                        grant_pk=grant.id,
                        grant_id=grant.grant_id,
                        cbsd_id=grant.cbsd_id,
                        reason="dpa_movelist",
                        action="terminate",
                        explanation="dpa_movelist",
                    )
                )
                decided_pks.add(grant.id)
    except (PropagationUnavailableError, TerrainError, ValueError, TypeError, KeyError):
        # Do not invent terminations; peer/IAP decisions above still apply.
        pass

    if iap_points and iap_coupling is not None:
        decisions.extend(
            _evaluate_iap_decisions(
                db,
                grants,
                snapshot=snapshot,
                decided_pks=decided_pks,
                iap_points=iap_points,
                iap_coupling=iap_coupling,
            )
        )
    return decisions


def _local_grant_to_rf_info(db: Session, grant: Grant) -> Any | None:
    from services.iap import GrantRfInfo

    cbsd = db.query(Cbsd).filter_by(cbsd_id=grant.cbsd_id).first()
    if cbsd is None:
        return None
    install: dict[str, Any] = {}
    if cbsd.registration_json:
        try:
            reg = json.loads(cbsd.registration_json)
            if isinstance(reg, dict):
                raw_install = reg.get("installationParam") or {}
                if isinstance(raw_install, dict):
                    install = raw_install
        except (TypeError, ValueError, json.JSONDecodeError):
            install = {}
    try:
        lat = float(install.get("latitude"))
        lon = float(install.get("longitude"))
    except (TypeError, ValueError):
        return None
    eirp = float(grant.max_eirp if grant.max_eirp is not None else 0.0)
    height = float(install.get("height") or 0.0)
    height_type = install.get("heightType") or "AGL"
    return GrantRfInfo(
        grant_id=grant.grant_id,
        cbsd_id=grant.cbsd_id,
        latitude=lat,
        longitude=lon,
        height_m=height,
        height_is_agl=height_type != "AMSL",
        indoor=bool(install.get("indoorDeployment")),
        low_hz=int(grant.low_frequency),
        high_hz=int(grant.high_frequency),
        max_eirp_dbm_mhz=eirp,
        is_managing_sas=True,
        grant_pk=grant.id,
        source_sas_id=None,
    )


def _evaluate_iap_decisions(
    db: Session,
    grants: list[Grant],
    *,
    snapshot: CpasSnapshot,
    decided_pks: set[int],
    iap_points: list[Any],
    iap_coupling: Any,
) -> list[CpasDecision]:
    from services.iap import run_iap
    from services.iap.peer_fad import grant_rf_infos_from_frozen_peer_cbsds

    rf_grants: list[Any] = []
    for grant in grants:
        if grant.terminated or grant.id in decided_pks:
            continue
        info = _local_grant_to_rf_info(db, grant)
        if info is not None:
            rf_grants.append(info)

    # Peer FAD grants from the frozen snapshot only (never live PeerFadRecord).
    peer_rf = grant_rf_infos_from_frozen_peer_cbsds(_frozen_peer_cbsd_rows(snapshot))
    rf_grants.extend(peer_rf)

    # Deterministic order: local managing grants first (by pk), then peers.
    rf_grants.sort(
        key=lambda g: (
            0 if g.is_managing_sas else 1,
            g.grant_pk if g.grant_pk is not None else 10**18,
            g.source_sas_id or "",
            g.grant_id,
        )
    )

    if not any(g.is_managing_sas for g in rf_grants):
        return []
    run = run_iap(list(iap_points), rf_grants, coupling=iap_coupling)
    out: list[CpasDecision] = []
    for item in run.merged_decisions:
        # Peer grants never produce local CPAS mutations.
        if not item.grant_pk:
            continue
        if item.action == "keep":
            continue
        out.append(
            CpasDecision(
                grant_pk=item.grant_pk,
                grant_id=item.grant_id,
                cbsd_id=item.cbsd_id,
                reason="iap",
                action=item.action,
                authorized_eirp_dbm_mhz=item.authorized_eirp_dbm_mhz,
                explanation=item.explanation,
            )
        )
    return out


def apply_cpas_decisions(db: Session, decisions: list[CpasDecision]) -> int:
    """Apply CPAS decisions via lifecycle / EIRP updates (no commit)."""
    from services.lifecycle import GrantEvent, apply_grant_event, lock_grant_row

    changed = 0
    for decision in decisions:
        # Peer / non-local decisions must never mutate the local grant table.
        if decision.grant_pk is None:
            logger.warning(
                "CPAS skip grant_id=%s: missing grant_pk (peer or invalid)",
                decision.grant_id,
            )
            continue
        grant = lock_grant_row(db, decision.grant_id, decision.cbsd_id)
        if grant is None or grant.id != decision.grant_pk:
            query = db.query(Grant).filter_by(id=decision.grant_pk)
            bind = db.get_bind()
            if bind is not None and bind.dialect.name != "sqlite":
                query = query.with_for_update()
            grant = query.first()
        if grant is None or grant.terminated:
            continue
        # Refuse peer-namespaced grant ids even if a PK somehow matched.
        if str(decision.grant_id).startswith("peer/"):
            logger.warning(
                "CPAS skip grant_pk=%s grant_id=%s: peer grant is immutable locally",
                decision.grant_pk,
                decision.grant_id,
            )
            continue

        action = decision.action or "terminate"
        if action == "reduce_power":
            if decision.authorized_eirp_dbm_mhz is None:
                continue
            if grant.max_eirp is not None and float(grant.max_eirp) <= float(
                decision.authorized_eirp_dbm_mhz
            ) + 1e-9:
                continue
            grant.max_eirp = float(decision.authorized_eirp_dbm_mhz)
            changed += 1
            continue
        if action == "suspend":
            event = GrantEvent.SUSPEND
        elif action == "terminate":
            event = GrantEvent.TERMINATE
        else:
            logger.warning(
                "CPAS skip grant_pk=%s grant_id=%s unknown action=%s",
                decision.grant_pk,
                decision.grant_id,
                action,
            )
            continue
        outcome = apply_grant_event(
            grant,
            event,
            payload={
                "cbsdId": grant.cbsd_id,
                "grantId": grant.grant_id,
                "reason": decision.reason,
                "explanation": decision.explanation,
            },
        )
        if not outcome.ok:
            logger.warning(
                "CPAS skip grant_pk=%s grant_id=%s action=%s lifecycle=%s",
                decision.grant_pk,
                decision.grant_id,
                action,
                outcome.detail or outcome.response_code,
            )
            continue
        changed += 1
    if changed:
        db.flush()
    return changed


def apply_peer_conflict_to_local_grants(db: Session) -> None:
    """Terminate local grants that conflict with peer FAD (same CBSD, PPA, or ESC).

    Convenience wrapper used by older call sites/tests. Prefer the staged
    pipeline in ``execute_cpas_pipeline`` for daily activities.
    """
    snapshot = freeze_cpas_snapshot(db)
    decisions = evaluate_cpas_protections(db, snapshot)
    if apply_cpas_decisions(db, decisions):
        db.commit()


def _dialect_name(db: Session) -> str:
    bind = db.get_bind()
    if bind is None:
        return ""
    return bind.dialect.name


def _run_pipeline_critical_section(
    db: Session, snapshot: CpasSnapshot
) -> tuple[int, int, list[CpasDecision]]:
    """Re-evaluate under lock, apply decisions, publish FAD — one durable outcome."""
    acquire_cpas_pipeline_xact_lock(db)
    # Recompute under coordination so TOCTOU after freeze cannot widen the set;
    # still constrained to snapshot.active_grant_pks.
    decisions = evaluate_cpas_protections(db, snapshot)
    terminated = apply_cpas_decisions(db, decisions)
    dump = create_full_activity_dump(db)
    return terminated, int(dump.id), decisions


def execute_cpas_pipeline(db: Session) -> dict[str, Any]:
    """Run the transactional CPAS pipeline; return a structured stage report.

    Peer/database sync may commit durable inputs. Grant terminations and the new
    local FAD are applied in one critical section so a failed FAD publish rolls
    back the grant decisions. Schedule success is marked only after full success.
    """
    from services.cpas_schedule_service import mark_scheduled_success_if_applicable
    from services.database_sync_service import sync_injected_database_urls

    result: dict[str, Any] = {
        "ok": False,
        "stages": [],
        "dump_id": None,
        "terminated_grants": 0,
        "decisions": [],
    }

    def _stage(name: str, **extra: Any) -> None:
        result["stages"].append({"name": name, "ok": True, **extra})

    try:
        sync_injected_database_urls(db)
        _stage("sync_databases")

        peer_report = run_peer_fad_sync(db)
        _stage(
            "sync_peer_fads",
            peers=peer_report.get("peers"),
            ok_peers=peer_report.get("ok"),
            failed_peers=peer_report.get("failed"),
        )

        snapshot = freeze_cpas_snapshot(db, peer_report)
        _stage(
            "freeze_snapshot",
            frozen_at=snapshot.frozen_at,
            active_grants=len(snapshot.active_grant_pks),
            peer_records=snapshot.peer_record_count,
        )

        # Preview outside the lock (observability); authoritative set is recomputed inside.
        preview = evaluate_cpas_protections(db, snapshot)
        _stage("evaluate_protections", decision_count=len(preview))

        if _dialect_name(db) == "sqlite":
            with _cpas_pipeline_lock:
                terminated, dump_id, decisions = _run_pipeline_critical_section(
                    db, snapshot
                )
        else:
            terminated, dump_id, decisions = _run_pipeline_critical_section(
                db, snapshot
            )

        result["decisions"] = [
            {
                "grant_id": d.grant_id,
                "cbsd_id": d.cbsd_id,
                "reason": d.reason,
            }
            for d in decisions
        ]
        result["terminated_grants"] = terminated
        result["dump_id"] = dump_id
        _stage(
            "apply_decisions_and_generate_fad",
            dump_id=dump_id,
            terminated=terminated,
            decision_count=len(decisions),
        )

        mark_scheduled_success_if_applicable(db)
        _append_cpas_audit(
            db,
            "cpas_completed",
            {
                "dumpId": dump_id,
                "terminatedGrants": terminated,
                "stages": [s["name"] for s in result["stages"]],
                "decisions": result["decisions"],
            },
        )
        db.commit()
        result["ok"] = True
        _stage("finalize_status_audit")
        logger.info(
            "CPAS pipeline completed dump_id=%s terminated=%s decisions=%s",
            dump_id,
            terminated,
            len(decisions),
        )
        return result
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            logger.exception("CPAS pipeline rollback failed")
        try:
            _append_cpas_audit(
                db,
                "cpas_failed",
                {
                    "error": f"{type(exc).__name__}: {exc}",
                    "stages": result.get("stages") or [],
                },
            )
            db.commit()
        except Exception:
            logger.exception("CPAS failure audit could not be persisted")
        logger.exception("CPAS pipeline failed")
        raise


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


def peer_has_grant_for_cbsd(
    db: Session,
    cbsd: Cbsd,
    *,
    peer_cbsd_records: list[dict[str, Any]] | None = None,
) -> bool:
    """True when any peer FAD CBSD record matches this local CBSD and has an active grant."""
    target_id = fad_cbsd_id(cbsd.fcc_id, cbsd.cbsd_serial_number)
    records = (
        peer_cbsd_records
        if peer_cbsd_records is not None
        else _peer_cbsd_records(db)
    )
    for record in records:
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


def _grant_conflicts_peer_ppa(
    db: Session,
    cbsd: Cbsd,
    grant: Grant,
    peer_zones: list[dict[str, Any]] | None = None,
) -> bool:
    """True when CBSD is in/near a peer PPA and the grant overlaps the PPA PAL band."""
    from services.geometry import within_geojson_buffer_m

    lat, lon = _cbsd_lat_lon(cbsd)
    if lat is None or lon is None:
        return False
    buffer_m = _peer_ppa_buffer_m()
    zones = peer_zones if peer_zones is not None else _peer_records_of_type(db, "zone")
    for record in zones:
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


def _grant_conflicts_peer_esc(
    db: Session,
    cbsd: Cbsd,
    grant: Grant,
    peer_esc_records: list[dict[str, Any]] | None = None,
) -> bool:
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
    sensors = (
        peer_esc_records
        if peer_esc_records is not None
        else _peer_records_of_type(db, "esc_sensor")
    )
    for record in sensors:
        inst = record.get("installationParam") or {}
        esc_lat, esc_lon = inst.get("latitude"), inst.get("longitude")
        if esc_lat is None or esc_lon is None:
            continue
        if haversine_m(lat, lon, float(esc_lat), float(esc_lon)) <= esc_radius_m:
            return True
    return False
