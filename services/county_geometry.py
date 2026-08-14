"""Generic county GeoJSON lookup by PAL licenseAreaIdentifier (FIPS).

Operational files live under ``data/geo/county/<FIPS>.json`` (or SAS_COUNTY_DIR).
Does not fetch over the network and does not import harness paths.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_COUNTY_DIR = _REPO_ROOT / "data" / "geo" / "county"


class CountyGeometryError(Exception):
    """County file missing, malformed, or not a usable polygon."""


def canonicalize_fips(identifier: Any) -> str | None:
    """Return a safe filename stem, or None if the identifier is unusable."""
    if identifier is None:
        return None
    text = str(identifier).strip()
    # ASCII digits only: blocks ``../``, extensions, and non-Latin digit tricks.
    if not text or not text.isascii() or not text.isdigit():
        return None
    return text


def resolve_county_dir(explicit: Path | str | None = None) -> Path:
    """explicit → SAS_COUNTY_DIR → settings.sas_county_dir → repo data/geo/county."""
    if explicit is not None:
        return Path(explicit)
    env = os.environ.get("SAS_COUNTY_DIR")
    if env:
        return Path(env).expanduser()
    try:
        from config import get_settings

        configured = get_settings().sas_county_dir
        if configured is not None:
            return Path(configured)
    except Exception:
        pass
    return _DEFAULT_COUNTY_DIR


def _geometry_from_payload(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    kind = payload.get("type")
    if kind in {"Polygon", "MultiPolygon"}:
        return payload
    if kind == "Feature":
        geom = payload.get("geometry")
        return geom if isinstance(geom, dict) else None
    if kind == "FeatureCollection":
        features = payload.get("features")
        if not isinstance(features, list) or not features:
            return None
        geoms = [
            f.get("geometry")
            for f in features
            if isinstance(f, dict) and isinstance(f.get("geometry"), dict)
        ]
        areal = [
            g
            for g in geoms
            if isinstance(g, dict) and g.get("type") in {"Polygon", "MultiPolygon"}
        ]
        if not areal:
            return None
        if len(areal) == 1:
            return areal[0]
        return {"type": "GeometryCollection", "geometries": areal}
    return None


def load_county_geometry(
    identifier: Any, *, county_dir: Path | str | None = None
) -> dict[str, Any]:
    """Load Polygon/MultiPolygon GeoJSON for a FIPS-like identifier."""
    fips = canonicalize_fips(identifier)
    if fips is None:
        raise CountyGeometryError("invalid_county_identifier")
    root = resolve_county_dir(county_dir).resolve()
    path = (root / f"{fips}.json").resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise CountyGeometryError("invalid_county_identifier") from exc
    if path.name != f"{fips}.json":
        raise CountyGeometryError("invalid_county_identifier")
    if not path.is_file():
        raise CountyGeometryError("county_file_missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CountyGeometryError("county_file_unreadable") from exc
    geom = _geometry_from_payload(payload)
    if geom is None:
        raise CountyGeometryError("county_geometry_invalid")
    from services.ppa_geometry import geojson_to_shapely, shapely_to_geojson

    try:
        shape = geojson_to_shapely(geom)
    except Exception as exc:
        raise CountyGeometryError("county_geometry_invalid") from exc
    if shape is None or shape.is_empty:
        raise CountyGeometryError("county_geometry_empty")
    out = shapely_to_geojson(shape)
    if out is None:
        raise CountyGeometryError("county_geometry_invalid")
    return out
