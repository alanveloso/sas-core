"""Build IAP ``ProtectionPoint`` lists from admin-injected entities (P7-005 MCP.1).

Thresholds are parameterized via ``IapThresholdProfile`` (R2-IPM-style defaults).
No harness fixture IDs or coordinates are hard-coded.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from services.data_injection_service import (
    KIND_FSS,
    KIND_WISP,
    KIND_ZONE,
    load_injected,
)
from services.iap.models import ProtectedEntityKind, ProtectionPoint

logger = logging.getLogger(__name__)

# Fallback only when spectrum profile is unavailable (tests / early import).
_DEFAULT_CBRS_LOW_HZ = 3_550_000_000
_DEFAULT_CBRS_HIGH_HZ = 3_700_000_000


def cbrs_band_hz() -> tuple[int, int]:
    """Active spectrum-profile band edges (not fixture-specific)."""
    try:
        from spectrum_profiles.context import get_active_profile

        plan = get_active_profile().band_plan
        return int(plan.low_hz), int(plan.high_hz)
    except (ImportError, AttributeError, RuntimeError, TypeError, ValueError):
        return _DEFAULT_CBRS_LOW_HZ, _DEFAULT_CBRS_HIGH_HZ


# Back-compat aliases for importers/tests.
CBRS_LOW_HZ = _DEFAULT_CBRS_LOW_HZ
CBRS_HIGH_HZ = _DEFAULT_CBRS_HIGH_HZ


@dataclass(frozen=True)
class IapThresholdProfile:
    """Default protection thresholds (dBm) and pre-IAP margin (dB).

    Values are profile defaults for local multi-constraint evaluation; official
    harness tolerances / entity-specific tables remain ENV-bound for PASS_OFFICIAL.
    """

    esc_dbm: float = -109.0
    fss_cochannel_dbm: float = -129.0
    ppa_dbm: float = -80.0
    gwpz_dbm: float = -80.0
    pre_iap_margin_db: float = 1.0


def clip_frequency_to_cbrs(
    low_hz: int,
    high_hz: int,
    *,
    band_low: int | None = None,
    band_high: int | None = None,
) -> tuple[int, int] | None:
    if band_low is None or band_high is None:
        default_low, default_high = cbrs_band_hz()
        band_low = default_low if band_low is None else band_low
        band_high = default_high if band_high is None else band_high
    low = max(int(low_hz), int(band_low))
    high = min(int(high_hz), int(band_high))
    if low >= high:
        return None
    return low, high


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _freq_pair(fr: Any) -> tuple[int, int] | None:
    if not isinstance(fr, dict):
        return None
    try:
        low = int(fr["lowFrequency"])
        high = int(fr["highFrequency"])
    except (KeyError, TypeError, ValueError):
        return None
    if low >= high:
        return None
    return low, high


def _geometry_from_zone_blob(zone: Any) -> dict[str, Any] | None:
    if not isinstance(zone, dict):
        return None
    ztype = zone.get("type")
    if ztype in {"Polygon", "MultiPolygon"}:
        return zone
    if ztype == "Feature":
        geom = zone.get("geometry")
        return geom if isinstance(geom, dict) else None
    if ztype == "FeatureCollection":
        features = zone.get("features") or []
        if isinstance(features, list) and features:
            first = features[0]
            if isinstance(first, dict):
                geom = first.get("geometry")
                return geom if isinstance(geom, dict) else None
    return None


def _point_from_installation(inst: Any) -> tuple[float, float] | None:
    if not isinstance(inst, dict):
        return None
    lat = _as_float(inst.get("latitude"))
    lon = _as_float(inst.get("longitude"))
    if lat is None or lon is None:
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    return lat, lon


def protection_point_from_fss_payload(
    payload: dict[str, Any],
    *,
    profile: IapThresholdProfile = IapThresholdProfile(),
) -> ProtectionPoint | None:
    record = payload.get("record") if isinstance(payload.get("record"), dict) else payload
    if not isinstance(record, dict):
        return None
    deps = record.get("deploymentParam")
    if not isinstance(deps, list) or not deps:
        return None
    first = deps[0] if isinstance(deps[0], dict) else None
    if first is None:
        return None
    loc = _point_from_installation(first.get("installationParam"))
    fr = _freq_pair((first.get("operationParam") or {}).get("operationFrequencyRange"))
    if loc is None or fr is None:
        return None
    clipped = clip_frequency_to_cbrs(fr[0], fr[1])
    if clipped is None:
        return None
    point_id = str(record.get("id") or "fss").strip() or "fss"
    return ProtectionPoint(
        point_id=f"fss:{point_id}",
        latitude=loc[0],
        longitude=loc[1],
        low_hz=clipped[0],
        high_hz=clipped[1],
        threshold_dbm=profile.fss_cochannel_dbm,
        entity_kind=ProtectedEntityKind.FSS_COCHANNEL,
        pre_iap_margin_db=profile.pre_iap_margin_db,
    )


def protection_point_from_wisp_payload(
    payload: dict[str, Any],
    *,
    profile: IapThresholdProfile = IapThresholdProfile(),
) -> ProtectionPoint | None:
    # Lazy import avoids services.iap ↔ dpa_protection cycle at package import.
    from services.dpa_protection import polygon_representative_point

    record = payload.get("record")
    zone = payload.get("zone")
    if not isinstance(record, dict):
        return None
    geom = _geometry_from_zone_blob(zone)
    loc = polygon_representative_point(geom)
    if loc is None:
        return None
    deps = record.get("deploymentParam")
    fr = None
    if isinstance(deps, list) and deps and isinstance(deps[0], dict):
        fr = _freq_pair((deps[0].get("operationParam") or {}).get("operationFrequencyRange"))
    if fr is None:
        fr = cbrs_band_hz()
    clipped = clip_frequency_to_cbrs(fr[0], fr[1])
    if clipped is None:
        return None
    point_id = str(record.get("id") or "gwpz").strip() or "gwpz"
    return ProtectionPoint(
        point_id=f"gwpz:{point_id}",
        latitude=loc[0],
        longitude=loc[1],
        low_hz=clipped[0],
        high_hz=clipped[1],
        threshold_dbm=profile.gwpz_dbm,
        entity_kind=ProtectedEntityKind.GWPZ,
        pre_iap_margin_db=profile.pre_iap_margin_db,
    )


def protection_point_from_zone_payload(
    payload: dict[str, Any],
    *,
    profile: IapThresholdProfile = IapThresholdProfile(),
) -> ProtectionPoint | None:
    from services.dpa_protection import polygon_representative_point

    record = payload.get("record") if isinstance(payload.get("record"), dict) else payload
    if not isinstance(record, dict):
        return None
    if record.get("terminated") is True:
        return None
    # Align with grant/PPA/CPAS consumers: only real PPAs become IAP points.
    if record.get("usage") != "PPA" and "ppaInfo" not in record:
        return None
    geom = _geometry_from_zone_blob(record.get("zone"))
    loc = polygon_representative_point(geom)
    if loc is None:
        return None
    # PPA frequency may be absent on ZoneData; protect full band until PAL binding exists.
    band_low, band_high = cbrs_band_hz()
    clipped = clip_frequency_to_cbrs(band_low, band_high)
    if clipped is None:
        return None
    point_id = str(record.get("id") or "ppa").strip() or "ppa"
    return ProtectionPoint(
        point_id=f"ppa:{point_id}",
        latitude=loc[0],
        longitude=loc[1],
        low_hz=clipped[0],
        high_hz=clipped[1],
        threshold_dbm=profile.ppa_dbm,
        entity_kind=ProtectedEntityKind.PPA,
        pre_iap_margin_db=profile.pre_iap_margin_db,
    )


def protection_point_from_esc_sensor_record(
    record: dict[str, Any],
    *,
    record_id: str,
    profile: IapThresholdProfile = IapThresholdProfile(),
) -> ProtectionPoint | None:
    loc = _point_from_installation(record.get("installationParam"))
    if loc is None:
        # Some ESC wraps nest installation under deploymentParam[0].
        deps = record.get("deploymentParam")
        if isinstance(deps, list) and deps and isinstance(deps[0], dict):
            loc = _point_from_installation(deps[0].get("installationParam"))
    if loc is None:
        return None
    fr = None
    for key in ("protectionFrequencyRange", "operationFrequencyRange"):
        fr = _freq_pair(record.get(key))
        if fr is not None:
            break
    if fr is None:
        band_low, band_high = cbrs_band_hz()
        # ESC default: lower portion of the active band when record omits a range.
        fr = (band_low, min(band_high, band_low + 100_000_000))
    clipped = clip_frequency_to_cbrs(fr[0], fr[1])
    if clipped is None:
        return None
    rid = str(record_id or record.get("id") or "esc").strip() or "esc"
    return ProtectionPoint(
        point_id=f"esc:{rid}",
        latitude=loc[0],
        longitude=loc[1],
        low_hz=clipped[0],
        high_hz=clipped[1],
        threshold_dbm=profile.esc_dbm,
        entity_kind=ProtectedEntityKind.ESC,
        pre_iap_margin_db=profile.pre_iap_margin_db,
    )


def build_protection_points_from_db(
    db: Session,
    *,
    profile: IapThresholdProfile | None = None,
) -> list[ProtectionPoint]:
    """Collect IAP points from injected FSS / WISP / PPA zones and ESC sensors."""
    thr = profile or IapThresholdProfile()
    points: list[ProtectionPoint] = []

    for payload in load_injected(db, KIND_FSS):
        pt = protection_point_from_fss_payload(payload, profile=thr)
        if pt is not None:
            points.append(pt)

    for payload in load_injected(db, KIND_WISP):
        pt = protection_point_from_wisp_payload(payload, profile=thr)
        if pt is not None:
            points.append(pt)

    for payload in load_injected(db, KIND_ZONE):
        pt = protection_point_from_zone_payload(payload, profile=thr)
        if pt is not None:
            points.append(pt)

    from models.models import EscSensor

    for row in db.query(EscSensor).order_by(EscSensor.id).all():
        try:
            data = json.loads(row.data_json or "{}")
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        pt = protection_point_from_esc_sensor_record(
            data, record_id=row.record_id, profile=thr
        )
        if pt is not None:
            points.append(pt)

    points.sort(key=lambda p: (p.entity_kind.value, p.point_id, p.low_hz, p.high_hz))
    logger.debug("Built %d IAP protection points from injections", len(points))
    return points
