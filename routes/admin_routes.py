"""Admin / test-control routes expected by the WINNF harness."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from database import get_db, reset_db
from models.models import (
    AdminInjectedData,
    ConditionalRegistration,
    CpiUser,
    EscSensor,
    FccIdRecord,
    PeerSas,
    UserIdRecord,
)
from schemas.admin import (
    BlacklistFccIdRequest,
    BlacklistFccIdSerialRequest,
    ConditionalRegistrationRequest,
    InjectCpiUserRequest,
    InjectFccIdRequest,
    InjectUserIdRequest,
)
from services.blacklist_service import add_fcc_id_blacklist, add_fcc_id_serial_blacklist
from services.cpas_service import (
    get_daily_activities_completed,
    trigger_daily_activities,
)
from services.fad_service import (
    create_full_activity_dump,
    rewrite_esc_sensor_id,
    rewrite_zone_id,
)
from services.mtls_auth import require_admin_certificate

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_certificate)],
)

def _empty_ok() -> Response:
    return Response(status_code=200, content=b"", media_type="application/json")


async def _read_json_object(request: Request) -> dict[str, Any]:
    """Parse JSON object body; invalid/non-object payloads become {} (harness inject)."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return {}
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _store_injection(db: Session, kind: str, payload: Any) -> None:
    db.add(
        AdminInjectedData(
            kind=kind,
            data_json=json.dumps(payload if payload is not None else {}),
        )
    )
    db.commit()


@router.post("/reset")
def admin_reset():
    reset_db()
    return _empty_ok()


@router.post("/injectdata/fcc_id")
def inject_fcc_id(body: InjectFccIdRequest, db: Session = Depends(get_db)):
    existing = db.query(FccIdRecord).filter_by(fcc_id=body.fccId).first()
    if existing:
        existing.fcc_max_eirp = body.fccMaxEirp
    else:
        db.add(FccIdRecord(fcc_id=body.fccId, fcc_max_eirp=body.fccMaxEirp))
    db.commit()
    return _empty_ok()


@router.post("/injectdata/user_id")
def inject_user_id(body: InjectUserIdRequest, db: Session = Depends(get_db)):
    if not db.query(UserIdRecord).filter_by(user_id=body.userId).first():
        db.add(UserIdRecord(user_id=body.userId))
        db.commit()
    return _empty_ok()


@router.post("/injectdata/conditional_registration")
def inject_conditional_registration(
    body: ConditionalRegistrationRequest, db: Session = Depends(get_db)
):
    for item in body.registrationData:
        fcc_id = item.get("fccId")
        serial = item.get("cbsdSerialNumber")
        if not fcc_id or not serial:
            continue
        existing = (
            db.query(ConditionalRegistration)
            .filter_by(fcc_id=fcc_id, cbsd_serial_number=serial)
            .first()
        )
        payload = json.dumps(item)
        if existing:
            existing.data_json = payload
        else:
            db.add(
                ConditionalRegistration(
                    fcc_id=fcc_id,
                    cbsd_serial_number=serial,
                    data_json=payload,
                )
            )
    db.commit()
    return _empty_ok()


@router.post("/injectdata/cpi_user")
def inject_cpi_user(body: InjectCpiUserRequest, db: Session = Depends(get_db)):
    existing = db.query(CpiUser).filter_by(cpi_id=body.cpiId).first()
    if existing:
        existing.cpi_name = body.cpiName
        existing.cpi_public_key = body.cpiPublicKey
    else:
        db.add(
            CpiUser(
                cpi_id=body.cpiId,
                cpi_name=body.cpiName,
                cpi_public_key=body.cpiPublicKey,
            )
        )
    db.commit()
    return _empty_ok()


@router.post("/injectdata/blacklist_fcc_id")
def blacklist_fcc_id(body: BlacklistFccIdRequest, db: Session = Depends(get_db)):
    add_fcc_id_blacklist(db, body.fccId)
    return _empty_ok()


@router.post("/trigger/meas_report_in_registration_response")
def trigger_meas_report_in_registration(db: Session = Depends(get_db)):
    from services.meas_report import FLAG_MEAS_REG, set_admin_flag

    set_admin_flag(db, FLAG_MEAS_REG)
    return _empty_ok()


@router.post("/trigger/meas_report_in_heartbeat_response")
def trigger_meas_report_in_heartbeat(db: Session = Depends(get_db)):
    from services.meas_report import FLAG_MEAS_HBT, set_admin_flag

    set_admin_flag(db, FLAG_MEAS_HBT)
    return _empty_ok()


@router.post("/injectdata/fss")
async def inject_fss(request: Request, db: Session = Depends(get_db)):
    body: Any = {}
    try:
        body = await request.json()
    except Exception:
        pass
    _store_injection(db, "fss", body)
    return _empty_ok()


@router.post("/injectdata/wisp")
async def inject_wisp(request: Request, db: Session = Depends(get_db)):
    body: Any = {}
    try:
        body = await request.json()
    except Exception:
        pass
    _store_injection(db, "wisp", body)
    return _empty_ok()


@router.post("/injectdata/pal_database_record")
async def inject_pal_database_record(request: Request, db: Session = Depends(get_db)):
    from services.pal_service import upsert_pal_records

    body: Any = {}
    try:
        body = await request.json()
    except Exception:
        pass
    upsert_pal_records(db, body)
    return _empty_ok()


@router.post("/injectdata/zone")
async def inject_zone(request: Request, db: Session = Depends(get_db)):
    body: dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        pass
    record = body.get("record") or {}
    if isinstance(record, dict):
        zone_id = rewrite_zone_id(record.get("id"))
        record = dict(record)
        record["id"] = zone_id
        body = dict(body)
        body["record"] = record
    else:
        zone_id = rewrite_zone_id(None)
    _store_injection(db, "zone", body)
    return JSONResponse(zone_id)


@router.post("/injectdata/exclusion_zone")
async def inject_exclusion_zone(request: Request, db: Session = Depends(get_db)):
    """Persist GeoJSON exclusion zone + frequencyRanges (EXZ_1)."""
    from services.exclusion_zone_service import persist_exclusion_zone

    body: dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        pass
    persist_exclusion_zone(db, body if isinstance(body, dict) else {})
    return _empty_ok()


@router.post("/trigger/enable_ntia_15_517")
def trigger_enable_ntia_15_517(db: Session = Depends(get_db)):
    """Enable NTIA TR 15-517 coastal exclusion zones (EXZ_2)."""
    from services.exclusion_zone_service import enable_ntia_exclusion_zones

    enable_ntia_exclusion_zones(db)
    return _empty_ok()


@router.post("/injectdata/peer_sas")
async def inject_peer_sas(request: Request, db: Session = Depends(get_db)):
    """Persist peer SAS certificateHash + url for SAS↔SAS authorization."""
    body: dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        pass
    cert_hash = (body.get("certificateHash") or "").strip()
    url = (body.get("url") or "").strip()
    if cert_hash:
        existing = db.query(PeerSas).filter_by(certificate_hash=cert_hash).first()
        if existing:
            existing.url = url
        else:
            db.add(PeerSas(certificate_hash=cert_hash, url=url))
        db.commit()
    return _empty_ok()


@router.post("/injectdata/esc_sensor")
async def inject_esc_sensor(request: Request, db: Session = Depends(get_db)):
    """Persist EscSensorRecord for inclusion in Full Activity Dump."""
    body: dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        pass
    record = body.get("record") or body
    if not isinstance(record, dict):
        return _empty_ok()
    record = dict(record)
    record_id = rewrite_esc_sensor_id(record.get("id"))
    record["id"] = record_id
    existing = db.query(EscSensor).filter_by(record_id=record_id).first()
    payload = json.dumps(record)
    if existing:
        existing.data_json = payload
    else:
        db.add(EscSensor(record_id=record_id, data_json=payload))
    db.commit()
    return _empty_ok()


@router.post("/trigger/create_full_activity_dump")
def trigger_create_full_activity_dump(db: Session = Depends(get_db)):
    """Generate FullActivityDump manifesto + activity dump files."""
    create_full_activity_dump(db)
    return _empty_ok()


@router.post("/trigger/daily_activities_immediately")
def trigger_daily_activities_immediately(db: Session = Depends(get_db)):
    """Start CPAS: pull peer FADs and apply conflict resolution."""
    trigger_daily_activities(db)
    return _empty_ok()


@router.post("/get_daily_activities_status")
def get_daily_activities_status(db: Session = Depends(get_db)):
    """Return completed=true only after peer FAD sync / conflict application finishes."""
    return JSONResponse({"completed": get_daily_activities_completed(db)})


@router.post("/trigger/load_dpas")
def trigger_load_dpas(db: Session = Depends(get_db)):
    """Load ESC-monitored DPA catalogue from KML and activate all channels."""
    from services.dpa_service import load_dpas

    load_dpas(db)
    return _empty_ok()


@router.post("/trigger/dpa_activation")
async def trigger_dpa_activation(request: Request, db: Session = Depends(get_db)):
    """Activate one catalogue DPA on one validated channel."""
    from services.dpa_service import activate_dpa

    body = await _read_json_object(request)
    activate_dpa(db, body)
    return _empty_ok()


@router.post("/trigger/bulk_dpa_activation")
async def trigger_bulk_dpa_activation(request: Request, db: Session = Depends(get_db)):
    """Bulk activate/deactivate all ESC-monitored DPAs on all catalogue channels."""
    from services.dpa_service import bulk_dpa_activation

    body = await _read_json_object(request)
    raw = body.get("activate") if isinstance(body, dict) else None
    activate = raw if isinstance(raw, bool) else None
    bulk_dpa_activation(db, activate=activate)
    return _empty_ok()


@router.post("/get_ppa_status")
def get_ppa_status(db: Session = Depends(get_db)):
    """WDB/PCR: poll until PPA creation finishes."""
    from services.ppa_service import get_ppa_creation_status

    return JSONResponse(get_ppa_creation_status(db))


@router.post("/trigger/create_ppa")
async def create_ppa(request: Request, db: Session = Depends(get_db)):
    """Create PPA zone from PAL + cluster (+ optional providedContour)."""
    from services.ppa_service import create_ppa as create_ppa_zone

    body = await _read_json_object(request)
    ppa_id = create_ppa_zone(db, body)
    return JSONResponse(ppa_id)


@router.post("/injectdata/database_url")
async def inject_database_url(request: Request, db: Session = Depends(get_db)):
    """FDB/WDB/IPR: accept external DB URL injection (FSS, GWBL, PAL, CPI, …)."""
    body: Any = {}
    try:
        body = await request.json()
    except Exception:
        pass
    _store_injection(db, "database_url", body)
    return _empty_ok()


@router.post("/trigger/enable_scheduled_daily_activities")
def trigger_enable_scheduled_daily_activities(db: Session = Depends(get_db)):
    """FDB_8: arm CPAS schedule (US/Pacific 02:00–04:00 by default)."""
    from fastapi import HTTPException

    from services.cpas_schedule_service import enable_scheduled_daily_activities

    try:
        enable_scheduled_daily_activities(db)
    except ValueError as exc:
        # Fail closed on bad SAS_CPAS_TIMEZONE — never empty-200 as if armed.
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _empty_ok()


@router.post("/injectdata/esc_zone")
async def inject_esc_zone(request: Request, db: Session = Depends(get_db)):
    """Persist ESC zone injection payload (harness InjectEscZone)."""
    body = await _read_json_object(request)
    _store_injection(db, "esc_zone", body)
    return _empty_ok()


@router.post("/injectdata/cluster_list")
async def inject_cluster_list(request: Request, db: Session = Depends(get_db)):
    """Persist PPA cluster list injection (harness InjectClusterList)."""
    body = await _read_json_object(request)
    _store_injection(db, "cluster_list", body)
    return _empty_ok()


@router.post("/injectdata/blacklist_fcc_id_and_serial_number")
def blacklist_fcc_id_and_serial_number(
    body: BlacklistFccIdSerialRequest, db: Session = Depends(get_db)
):
    """Blacklist a specific CBSD (fccId + cbsdSerialNumber); enforced on REG/SIQ/GRA/HBT."""
    add_fcc_id_serial_blacklist(db, body.fccId, body.cbsdSerialNumber)
    return _empty_ok()


@router.post("/injectdata/sas_admin")
async def inject_sas_admin(request: Request, db: Session = Depends(get_db)):
    """Persist SasAdministrator record injection."""
    body = await _read_json_object(request)
    _store_injection(db, "sas_admin", body)
    return _empty_ok()


@router.post("/trigger/esc_detection")
async def trigger_esc_detection(request: Request, db: Session = Depends(get_db)):
    from services.meas_report import set_admin_flag

    body = await _read_json_object(request)
    set_admin_flag(db, "esc_detection", body)
    return _empty_ok()


@router.post("/trigger/esc_reset")
def trigger_esc_reset(db: Session = Depends(get_db)):
    from services.meas_report import clear_admin_flags

    clear_admin_flags(db, "esc_detection")
    return _empty_ok()


@router.post("/trigger/dpa_deactivation")
async def trigger_dpa_deactivation(request: Request, db: Session = Depends(get_db)):
    """Deactivate one DPA on one channel (selective; harness TriggerDpaDeactivation)."""
    from services.dpa_service import deactivate_dpa

    body = await _read_json_object(request)
    deactivate_dpa(db, body)
    return _empty_ok()


@router.post("/trigger/disconnect_esc")
def trigger_disconnect_esc(db: Session = Depends(get_db)):
    from services.meas_report import set_admin_flag

    set_admin_flag(db, "esc_disconnected", {"disconnected": True})
    return _empty_ok()


@router.post("/query/propagation_and_antenna_model")
async def query_propagation_and_antenna_model(request: Request):
    """PAT admin query — not implemented; must not return a fake success body."""
    del request
    return JSONResponse(
        {
            "detail": (
                "Admin query/propagation_and_antenna_model is not implemented "
                "(PAT family pending)."
            )
        },
        status_code=501,
    )
