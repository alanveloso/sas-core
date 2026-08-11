"""FIX-04: NTIA EXZ protection_zones.kml resolves via protection-data root."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.models import Base
from protection_data.loader import get_data_root, set_data_root
from services.exclusion_zone_service import (
    ExclusionZoneUnavailable,
    _repo_ntia_kml,
    enable_ntia_exclusion_zones,
    load_ntia_coastal_geojson,
)

# Minimal KML with one coastal contour name required by the loader.
_MIN_COASTAL_KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>West Combined Contour</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -122.0,37.0,0 -122.0,38.0,0 -121.0,38.0,0 -121.0,37.0,0 -122.0,37.0,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>
"""


@pytest.fixture
def memory_db():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    SessionLocal = sessionmaker(bind=eng)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _reset_data_root():
    set_data_root(None)
    yield
    set_data_root(None)


def _assert_no_codigo_symlink_masking():
    """B: external ~/Código/data/ntia symlink must not be required / masking."""
    legacy = Path.home() / "Código" / "data" / "ntia"
    # Also the exact parents[2] path used by the old bug when running from this repo.
    repo = Path(__file__).resolve().parents[2]
    legacy_parent = repo.parent / "data" / "ntia"
    for path in (legacy, legacy_parent):
        if path.is_symlink() or path.exists():
            pytest.fail(
                f"legacy NTIA path still present and may mask FIX-04: {path} "
                "(remove symlink before validating)"
            )


def test_a_canonical_root_loads_without_symlink(memory_db):
    """A: protection_zones.kml under get_data_root()/ntia → enable succeeds."""
    _assert_no_codigo_symlink_masking()
    root = get_data_root()
    kml = root / "ntia" / "protection_zones.kml"
    assert kml.is_file(), f"expected official KML at {kml}"
    assert _repo_ntia_kml().resolve() == kml.resolve()

    src = Path("services/exclusion_zone_service.py").read_text(encoding="utf-8")
    assert "parents[2]" not in src
    assert "get_data_root" in src

    features = load_ntia_coastal_geojson()["features"]
    assert len(features) >= 1
    enable_ntia_exclusion_zones(memory_db)


def test_b_legacy_symlink_absent_still_succeeds(memory_db):
    """B: with symlink absent, canonical root still works."""
    _assert_no_codigo_symlink_masking()
    enable_ntia_exclusion_zones(memory_db)


def test_c_missing_payload_fail_closed(memory_db, tmp_path: Path):
    """C: absent payload → ExclusionZoneUnavailable (fail-closed)."""
    empty_root = tmp_path / "data"
    (empty_root / "ntia").mkdir(parents=True)
    set_data_root(empty_root)
    assert not _repo_ntia_kml().is_file()
    assert load_ntia_coastal_geojson()["features"] == []
    with pytest.raises(ExclusionZoneUnavailable):
        enable_ntia_exclusion_zones(memory_db)


def test_d_overridden_data_root_used_not_repo_parents(memory_db, tmp_path: Path):
    """D: set_data_root(tmp) → loader reads override, not repository parents."""
    override = tmp_path / "alt_data"
    ntia = override / "ntia"
    ntia.mkdir(parents=True)
    (ntia / "protection_zones.kml").write_text(_MIN_COASTAL_KML, encoding="utf-8")
    set_data_root(override)

    resolved = _repo_ntia_kml().resolve()
    assert resolved == (override / "ntia" / "protection_zones.kml").resolve()
    # Must not resolve into the real repo data tree when override is set.
    repo_default = (
        Path(__file__).resolve().parents[2] / "data" / "ntia" / "protection_zones.kml"
    ).resolve()
    assert resolved != repo_default

    features = load_ntia_coastal_geojson()["features"]
    assert len(features) == 1
    assert features[0]["properties"]["name"] == "West Combined Contour"
    enable_ntia_exclusion_zones(memory_db)


def test_repo_ntia_path_never_uses_parent_of_repo():
    """Regression: resolved path stays under get_data_root(), not parents[2]."""
    set_data_root(None)
    path = _repo_ntia_kml().resolve()
    root = get_data_root().resolve()
    assert path == (root / "ntia" / "protection_zones.kml").resolve()
    assert path.is_relative_to(root)
    # Old bug landed under <repo_parent>/data/ntia/...
    wrong = Path(__file__).resolve().parents[2].parent / "data" / "ntia" / "protection_zones.kml"
    assert path != wrong.resolve()
