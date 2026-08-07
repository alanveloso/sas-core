"""Convert frozen peer FAD CBSD records into IAP ``GrantRfInfo`` inputs."""

from __future__ import annotations

from typing import Any

from services.iap.models import GrantRfInfo


def peer_grant_rf_id(source_sas_id: str | int, grant_id: str) -> str:
    """Stable namespaced id so peer grant ids cannot collide across SAS."""
    return f"peer/{source_sas_id}/{grant_id}"


def grant_rf_infos_from_peer_cbsd_record(
    record: dict[str, Any],
    *,
    source_sas_id: str | int,
) -> list[GrantRfInfo]:
    """Parse one FAD CBSD record into peer ``GrantRfInfo`` rows (may be empty)."""
    src = str(source_sas_id)
    cbsd_id = str(record.get("id") or "").strip()
    if not cbsd_id:
        return []
    install = record.get("installationParam")
    if not isinstance(install, dict):
        return []
    try:
        lat = float(install["latitude"])
        lon = float(install["longitude"])
    except (KeyError, TypeError, ValueError):
        return []
    height = float(install.get("height") or 0.0)
    height_type = install.get("heightType") or "AGL"
    indoor = bool(install.get("indoorDeployment"))
    grants_raw = record.get("grants")
    if not isinstance(grants_raw, list):
        return []

    out: list[GrantRfInfo] = []
    for grant in grants_raw:
        if not isinstance(grant, dict):
            continue
        if grant.get("terminated") is True:
            continue
        raw_id = str(grant.get("id") or "").strip()
        if not raw_id:
            continue
        op = grant.get("operationParam")
        if not isinstance(op, dict):
            continue
        try:
            eirp = float(op["maxEirp"])
            freq = op["operationFrequencyRange"]
            low_hz = int(freq["lowFrequency"])
            high_hz = int(freq["highFrequency"])
        except (KeyError, TypeError, ValueError):
            continue
        if high_hz <= low_hz:
            continue
        out.append(
            GrantRfInfo(
                grant_id=peer_grant_rf_id(src, raw_id),
                cbsd_id=cbsd_id,
                latitude=lat,
                longitude=lon,
                height_m=height,
                height_is_agl=height_type != "AMSL",
                indoor=indoor,
                low_hz=low_hz,
                high_hz=high_hz,
                max_eirp_dbm_mhz=eirp,
                is_managing_sas=False,
                grant_pk=None,
                source_sas_id=src,
            )
        )
    return out


def grant_rf_infos_from_frozen_peer_cbsds(
    peer_cbsd_rows: list[tuple[str | int, dict[str, Any]]],
) -> list[GrantRfInfo]:
    """Build peer RF grants from frozen ``(source_sas_id, cbsd_record)`` rows.

    Output is sorted by ``(source_sas_id, grant_id)`` so peer order is irrelevant.
    """
    collected: list[GrantRfInfo] = []
    for source_sas_id, record in peer_cbsd_rows:
        if not isinstance(record, dict):
            continue
        collected.extend(
            grant_rf_infos_from_peer_cbsd_record(record, source_sas_id=source_sas_id)
        )
    collected.sort(key=lambda g: (g.source_sas_id or "", g.grant_id))
    return collected
