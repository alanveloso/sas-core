"""Admin PPA creation lifecycle (P4-003).

Implements TriggerPpaCreation / GetPpaCreationStatus semantics:

- validate PALs (known + VALID + shared holder);
- validate cluster CBSDs (registered, holder match);
- build or accept geometry (providedContour or cluster convex hull);
- reject overlap with an existing PPA on the same PAL channel;
- persist ZoneData for FAD export;
- status progresses to completed with withError only after a real failure.

Census-tract clip against official county polygons is deferred when PAL records
lack an injectable service-area GeoJSON (full PCR.1 geometry fidelity → RF/data
phases). When ``license.licenseArea`` / ``serviceArea`` GeoJSON is present on
every PAL, CBSDs and the contour are checked against that union.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from models.models import AdminInjectedData, Cbsd
from services.fad_service import rewrite_zone_id
from services.geometry import geojson_areas_overlap, iter_geojson_rings, point_in_geojson
from services.meas_report import set_admin_flag
from services.pal_service import load_pal_records

KIND_STATUS = "ppa_creation_status"
KIND_ZONE = "zone"
KIND_AUDIT = "ppa_audit"


class PpaCreationError(Exception):
    """Domain failure that must surface as withError=true after completion."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _append_audit(db: Session, event: str, detail: dict[str, Any]) -> None:
    db.add(
        AdminInjectedData(
            kind=KIND_AUDIT,
            data_json=json.dumps(
                {"event": event, "at": _utc_now_iso(), **detail},
                default=str,
            ),
        )
    )


def set_ppa_creation_status(
    db: Session,
    *,
    completed: bool,
    with_error: bool,
    reason: str | None = None,
    ppa_id: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "completed": completed,
        "withError": with_error,
        "updatedAt": _utc_now_iso(),
    }
    if reason is not None:
        payload["reason"] = reason
    if ppa_id is not None:
        payload["ppaId"] = ppa_id
    set_admin_flag(db, KIND_STATUS, payload)


def get_ppa_creation_status(db: Session) -> dict[str, bool]:
    """Return harness status object; unfinished/absent → completed=false."""
    row = db.query(AdminInjectedData).filter_by(kind=KIND_STATUS).first()
    if not row:
        return {"completed": False, "withError": False}
    try:
        status = json.loads(row.data_json or "{}")
    except json.JSONDecodeError:
        return {"completed": False, "withError": False}
    if not isinstance(status, dict):
        return {"completed": False, "withError": False}
    return {
        "completed": bool(status.get("completed", False)),
        "withError": bool(status.get("withError", False)),
    }


def _cbsd_location(cbsd: Cbsd) -> tuple[float, float] | None:
    try:
        reg = json.loads(cbsd.registration_json or "{}")
    except json.JSONDecodeError:
        return None
    inst = reg.get("installationParam") or {}
    lat, lon = inst.get("latitude"), inst.get("longitude")
    if lat is None or lon is None:
        return None
    try:
        return float(lat), float(lon)
    except (TypeError, ValueError):
        return None


def _is_valid_feature_collection(contour: Any) -> bool:
    if not isinstance(contour, dict) or contour.get("type") != "FeatureCollection":
        return False
    features = contour.get("features")
    if not isinstance(features, list) or not features:
        return False
    return bool(iter_geojson_rings(contour))


def _convex_hull_lonlat(points: list[tuple[float, float]]) -> list[list[float]]:
    """Andrew's monotone chain; points are (lat, lon); ring is GeoJSON [lon, lat]."""
    unique = sorted({(lon, lat) for lat, lon in points})
    if len(unique) == 1:
        lon, lat = unique[0]
        d = 0.001
        return [
            [lon - d, lat - d],
            [lon - d, lat + d],
            [lon + d, lat + d],
            [lon + d, lat - d],
            [lon - d, lat - d],
        ]
    if len(unique) == 2:
        (lon1, lat1), (lon2, lat2) = unique
        pad = 0.0005
        return [
            [lon1 - pad, lat1 - pad],
            [lon1 - pad, lat1 + pad],
            [lon2 + pad, lat2 + pad],
            [lon2 + pad, lat2 - pad],
            [lon1 - pad, lat1 - pad],
        ]

    def cross(
        o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]
    ) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for p in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[tuple[float, float]] = []
    for p in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    ring = [[lon, lat] for lon, lat in hull]
    if ring[0] != ring[-1]:
        ring.append(list(ring[0]))
    return ring


def _geometry_from_cluster(locations: list[tuple[float, float]]) -> dict[str, Any]:
    ring = _convex_hull_lonlat(locations)
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            }
        ],
    }


def _pal_service_area(pal: dict[str, Any]) -> dict[str, Any] | None:
    license_obj = pal.get("license") if isinstance(pal.get("license"), dict) else {}
    for key in ("licenseArea", "serviceArea", "licenseAreaGeometry"):
        geo = pal.get(key) or license_obj.get(key)
        if isinstance(geo, dict) and iter_geojson_rings(geo):
            return geo
    return None


def _union_service_areas(pals: list[dict[str, Any]]) -> dict[str, Any] | None:
    features: list[dict[str, Any]] = []
    for pal in pals:
        area = _pal_service_area(pal)
        if area is None:
            return None
        if area.get("type") == "FeatureCollection":
            features.extend(
                f for f in (area.get("features") or []) if isinstance(f, dict)
            )
        elif area.get("type") == "Feature":
            features.append(area)
        else:
            features.append(
                {"type": "Feature", "properties": {}, "geometry": area}
            )
    if not features:
        return None
    return {"type": "FeatureCollection", "features": features}


def _points_within(zone: dict[str, Any], locations: list[tuple[float, float]]) -> bool:
    return all(point_in_geojson(lat, lon, zone) for lat, lon in locations)


def _contour_within_service_area(
    contour: dict[str, Any], service_area: dict[str, Any]
) -> bool:
    """Approximate: every contour vertex must lie inside the service area."""
    for ring in iter_geojson_rings(contour):
        for lon, lat, *_rest in ring:
            if not point_in_geojson(float(lat), float(lon), service_area):
                return False
    return True


def _existing_ppa_records(db: Session) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in db.query(AdminInjectedData).filter_by(kind=KIND_ZONE).all():
        try:
            payload = json.loads(row.data_json or "{}")
        except json.JSONDecodeError:
            continue
        record = payload.get("record") or payload
        if not isinstance(record, dict):
            continue
        if record.get("usage") != "PPA" and "ppaInfo" not in record:
            continue
        out.append(record)
    return out


def _geometries_overlap(a: dict[str, Any] | None, b: dict[str, Any] | None) -> bool:
    """Admin PPA conflict: True when polygon interiors intersect.

    Delegates to :func:`services.geometry.geojson_areas_overlap` (edge crossings
    and containment; boundary-only touch is not a conflict).
    """
    return geojson_areas_overlap(a, b)


def _pal_freq(pal: dict[str, Any]) -> tuple[int, int] | None:
    assignment = (pal.get("channelAssignment") or {}).get("primaryAssignment") or {}
    low, high = assignment.get("lowFrequency"), assignment.get("highFrequency")
    if low is None or high is None:
        block = pal.get("palBlock") or {}
        low, high = block.get("lowFrequency"), block.get("highFrequency")
    if low is None or high is None:
        return None
    try:
        return int(low), int(high)
    except (TypeError, ValueError):
        return None


def _freqs_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and a[1] > b[0]


def _validate_and_build(
    db: Session, body: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    pal_ids = body.get("palIds")
    cbsd_ids = body.get("cbsdIds")
    provided = body.get("providedContour")

    if not isinstance(pal_ids, list) or not pal_ids:
        raise PpaCreationError("missing_palIds")
    if not all(isinstance(p, str) and p.strip() for p in pal_ids):
        raise PpaCreationError("invalid_palIds")
    pal_ids = [p.strip() for p in pal_ids]
    if len(set(pal_ids)) != len(pal_ids):
        raise PpaCreationError("duplicate_palIds")

    if not isinstance(cbsd_ids, list) or not cbsd_ids:
        raise PpaCreationError("missing_cbsdIds")
    if not all(isinstance(c, str) and c.strip() for c in cbsd_ids):
        raise PpaCreationError("invalid_cbsdIds")
    cbsd_ids = [c.strip() for c in cbsd_ids]
    if len(set(cbsd_ids)) != len(cbsd_ids):
        raise PpaCreationError("duplicate_cbsdIds")

    pals_by_id = {
        p["palId"]: p
        for p in load_pal_records(db, active_only=False)
        if p.get("palId")
    }
    selected: list[dict[str, Any]] = []
    for pal_id in pal_ids:
        pal = pals_by_id.get(pal_id)
        if pal is None:
            raise PpaCreationError("unknown_palId")
        status = str(pal.get("licenseStatus") or "").upper()
        if status != "VALID":
            raise PpaCreationError("inactive_pal")
        selected.append(pal)

    holders = {str(p.get("userId") or "") for p in selected}
    if len(holders) != 1 or not next(iter(holders)):
        raise PpaCreationError("pal_holder_mismatch")
    holder = next(iter(holders))

    cbsds: list[Cbsd] = []
    for cid in cbsd_ids:
        row = db.query(Cbsd).filter_by(cbsd_id=cid).first()
        if row is None:
            raise PpaCreationError("unknown_cbsdId")
        if str(row.user_id or "") != holder:
            raise PpaCreationError("cbsd_not_pal_holder")
        cbsds.append(row)

    locations: list[tuple[float, float]] = []
    for cbsd in cbsds:
        loc = _cbsd_location(cbsd)
        if loc is None:
            raise PpaCreationError("cbsd_missing_location")
        locations.append(loc)

    service_area = _union_service_areas(selected)
    if service_area is not None and not _points_within(service_area, locations):
        raise PpaCreationError("cbsd_outside_service_area")

    if provided is not None:
        if not _is_valid_feature_collection(provided):
            raise PpaCreationError("invalid_providedContour")
        contour = provided
        if not _points_within(contour, locations):
            raise PpaCreationError("cbsd_outside_providedContour")
        if service_area is not None and not _contour_within_service_area(
            contour, service_area
        ):
            raise PpaCreationError("contour_outside_service_area")
    else:
        contour = _geometry_from_cluster(locations)
        if service_area is not None and not _contour_within_service_area(
            contour, service_area
        ):
            raise PpaCreationError("contour_outside_service_area")

    selected_freqs = [_pal_freq(p) for p in selected]
    selected_freqs_ok = [f for f in selected_freqs if f is not None]
    for existing in _existing_ppa_records(db):
        info = existing.get("ppaInfo") or {}
        existing_pal_ids = list(info.get("palId") or [])
        existing_pals = [pals_by_id[p] for p in existing_pal_ids if p in pals_by_id]
        existing_freqs = [f for f in (_pal_freq(p) for p in existing_pals) if f]
        freq_clash = any(
            _freqs_overlap(a, b) for a in selected_freqs_ok for b in existing_freqs
        )
        if not freq_clash and not set(existing_pal_ids).intersection(pal_ids):
            continue
        if _geometries_overlap(contour, existing.get("zone")):
            raise PpaCreationError("overlaps_existing_ppa")

    token = uuid.uuid4().hex
    raw_id = f"zone/ppa/pending/{pal_ids[0]}/{token}"
    ppa_id = rewrite_zone_id(raw_id, fallback_suffix=f"{pal_ids[0]}/{token}")

    rings = iter_geojson_rings(contour)
    if len(rings) == 1:
        zone_geom: dict[str, Any] = {"type": "Polygon", "coordinates": [rings[0]]}
    else:
        zone_geom = contour

    begin = _utc_now_iso()[:10]
    expiration = None
    for pal in selected:
        lic = pal.get("license") if isinstance(pal.get("license"), dict) else {}
        expiration = lic.get("licenseExpiration") or pal.get("licenseExpiration")
        if expiration:
            break
    if not expiration:
        expiration = begin

    record = {
        "id": ppa_id,
        "name": f"PPA-{pal_ids[0]}",
        "creator": ppa_id.split("/")[2] if len(ppa_id.split("/")) > 2 else "sas",
        "usage": "PPA",
        "terminated": False,
        "zone": zone_geom,
        "ppaInfo": {
            "palId": pal_ids,
            "cbsdReferenceId": list(cbsd_ids),
            "ppaBeginDate": begin,
            "ppaExpirationDate": expiration,
        },
    }
    return ppa_id, record


def _persist_zone(db: Session, record: dict[str, Any]) -> None:
    db.add(
        AdminInjectedData(
            kind=KIND_ZONE,
            data_json=json.dumps({"record": record}),
        )
    )


def create_ppa(db: Session, body: dict[str, Any]) -> str:
    """Run PPA creation; return ppa id string or empty string on failure.

    Always leaves ``ppa_creation_status`` with completed=true when finished.
    ``withError`` is true only after a caught domain failure (never silent success).
    """
    if not isinstance(body, dict):
        body = {}

    set_ppa_creation_status(db, completed=False, with_error=False)

    try:
        ppa_id, record = _validate_and_build(db, body)
        _persist_zone(db, record)
        set_ppa_creation_status(
            db, completed=True, with_error=False, ppa_id=ppa_id
        )
        _append_audit(db, "create_ppa_ok", {"ppaId": ppa_id})
        db.commit()
        return ppa_id
    except PpaCreationError as exc:
        set_ppa_creation_status(
            db, completed=True, with_error=True, reason=exc.reason
        )
        _append_audit(db, "create_ppa_error", {"reason": exc.reason})
        db.commit()
        return ""
    except Exception as exc:  # noqa: BLE001 — must not leave status=incomplete forever
        # Protocol failure path (empty id + withError), not success catch-all.
        set_ppa_creation_status(
            db,
            completed=True,
            with_error=True,
            reason=f"internal_error:{type(exc).__name__}",
        )
        _append_audit(
            db,
            "create_ppa_internal_error",
            {"errorType": type(exc).__name__},
        )
        db.commit()
        return ""
