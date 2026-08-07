"""P6-001: versioned protection-data packaging and validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from config import clear_settings_cache
from protection_data.loader import (
    DatasetNotFoundError,
    DatasetValidationError,
    assert_protection_data_ready,
    clear_dataset_bundle_cache,
    load_dataset_bundle,
    set_data_root,
    set_manifests_dir,
    validate_dataset_bundle,
)
from tools.doctor import run_doctor


def _write_bundle(manifests: Path, *, bundle_id: str = "test_bundle") -> Path:
    payload = {
        "id": bundle_id,
        "version": "9.9.9",
        "description": "test",
        "slots": [
            {
                "id": "itm_wf",
                "kind": "itm",
                "version": "1.0.0",
                "relative_path": "models/itm",
                "required": True,
                "presence": "version_marker",
            },
            {
                "id": "terrain_ned",
                "kind": "terrain_ned",
                "version": "1.0.0",
                "relative_path": "geo/ned",
                "required": True,
                "presence": "version_marker",
            },
            {
                "id": "ned_payload",
                "kind": "terrain_ned",
                "version": "1.0.0",
                "relative_path": "geo/ned",
                "required": True,
                "presence": "files_glob",
                "file_glob": "*.flt",
                "min_files": 1,
                "payload_optional_unless_strict": True,
            },
            {
                "id": "nlcd_clutter",
                "kind": "nlcd",
                "version": "1.0.0",
                "relative_path": "geo/nlcd",
                "required": True,
                "presence": "version_marker",
            },
            {
                "id": "antenna_patterns",
                "kind": "antenna",
                "version": "1.0.0",
                "relative_path": "models/antenna",
                "required": True,
                "presence": "version_marker",
            },
            {
                "id": "dpa_definitions",
                "kind": "dpa",
                "version": "1.0.0",
                "relative_path": "ntia",
                "required": True,
                "presence": "version_marker",
            },
            {
                "id": "fss_sites",
                "kind": "fss",
                "version": "1.0.0",
                "relative_path": "federal/fss",
                "required": True,
                "presence": "version_marker",
            },
            {
                "id": "gwbl",
                "kind": "gwbl",
                "version": "1.0.0",
                "relative_path": "federal/gwbl",
                "required": True,
                "presence": "version_marker",
            },
            {
                "id": "zones_reference",
                "kind": "zones",
                "version": "1.0.0",
                "relative_path": "geo/zones",
                "required": True,
                "presence": "version_marker",
            },
            {
                "id": "census_tracts",
                "kind": "census",
                "version": "1.0.0",
                "relative_path": "geo/census",
                "required": True,
                "presence": "version_marker",
            },
        ],
    }
    path = manifests / f"{bundle_id}.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def _seed_markers(root: Path) -> None:
    for rel, ver in [
        ("models/itm", "1.0.0"),
        ("geo/ned", "1.0.0"),
        ("geo/nlcd", "1.0.0"),
        ("models/antenna", "1.0.0"),
        ("ntia", "1.0.0"),
        ("federal/fss", "1.0.0"),
        ("federal/gwbl", "1.0.0"),
        ("geo/zones", "1.0.0"),
        ("geo/census", "1.0.0"),
    ]:
        d = root / rel
        d.mkdir(parents=True, exist_ok=True)
        (d / "VERSION").write_text(f"{ver}\n", encoding="utf-8")


@pytest.fixture(autouse=True)
def _reset_protection_data_overrides():
    clear_dataset_bundle_cache()
    set_manifests_dir(None)
    set_data_root(None)
    clear_settings_cache()
    yield
    clear_dataset_bundle_cache()
    set_manifests_dir(None)
    set_data_root(None)
    clear_settings_cache()


def test_default_bundle_loads_and_has_core_kinds():
    bundle = load_dataset_bundle("cbrs_winnforum_protection")
    assert bundle.version == "1.0.0"
    kinds = {s.kind for s in bundle.slots}
    for kind in (
        "itm",
        "terrain_ned",
        "nlcd",
        "antenna",
        "dpa",
        "fss",
        "gwbl",
        "zones",
        "census",
    ):
        assert kind in kinds


def test_validate_default_bundle_non_strict_with_repo_markers():
    report = validate_dataset_bundle(
        "cbrs_winnforum_protection", strict=False
    )
    assert report.ok is True
    # Payload may be absent locally; soft gaps are allowed when not strict.
    soft = [s for s in report.slots if s.soft_payload_gap]
    assert soft  # NED/DPA payload slots exist in the default manifest


def test_missing_bundle_raises(tmp_path: Path):
    set_manifests_dir(tmp_path)
    with pytest.raises(DatasetNotFoundError):
        load_dataset_bundle("no_such_bundle")


def test_invalid_manifest_missing_kind(tmp_path: Path):
    set_manifests_dir(tmp_path)
    bad = {
        "id": "broken",
        "version": "1",
        "slots": [
            {
                "id": "only_itm",
                "kind": "itm",
                "version": "1",
                "relative_path": "models/itm",
                "required": True,
                "presence": "version_marker",
            }
        ],
    }
    (tmp_path / "broken.yaml").write_text(yaml.safe_dump(bad), encoding="utf-8")
    with pytest.raises(DatasetValidationError, match="missing required dataset kinds"):
        load_dataset_bundle("broken")


def test_validate_fails_without_version_marker(tmp_path: Path):
    manifests = tmp_path / "manifests"
    data = tmp_path / "data"
    manifests.mkdir()
    data.mkdir()
    _write_bundle(manifests)
    set_manifests_dir(manifests)
    set_data_root(data)
    report = validate_dataset_bundle("test_bundle", data_root=data, strict=False)
    assert report.ok is False
    assert any(s.slot_id == "itm_wf" and not s.ok for s in report.slots)


def test_validate_passes_with_markers_non_strict(tmp_path: Path):
    manifests = tmp_path / "manifests"
    data = tmp_path / "data"
    manifests.mkdir()
    _write_bundle(manifests)
    _seed_markers(data)
    set_manifests_dir(manifests)
    report = validate_dataset_bundle("test_bundle", data_root=data, strict=False)
    assert report.ok is True
    # No .flt payload → soft gap
    ned_payload = next(s for s in report.slots if s.slot_id == "ned_payload")
    assert ned_payload.ok is False
    assert ned_payload.soft_payload_gap is True


def test_strict_mode_requires_payload_files(tmp_path: Path):
    manifests = tmp_path / "manifests"
    data = tmp_path / "data"
    manifests.mkdir()
    _write_bundle(manifests)
    _seed_markers(data)
    set_manifests_dir(manifests)
    report = validate_dataset_bundle("test_bundle", data_root=data, strict=True)
    assert report.ok is False
    with pytest.raises(DatasetValidationError, match="incomplete"):
        assert_protection_data_ready("test_bundle", data_root=data, strict=True)

    (data / "geo" / "ned" / "tile.flt").write_bytes(b"ned")
    report2 = validate_dataset_bundle("test_bundle", data_root=data, strict=True)
    assert report2.ok is True
    assert_protection_data_ready("test_bundle", data_root=data, strict=True)


def test_version_mismatch_fails(tmp_path: Path):
    manifests = tmp_path / "manifests"
    data = tmp_path / "data"
    manifests.mkdir()
    _write_bundle(manifests)
    _seed_markers(data)
    (data / "models" / "itm" / "VERSION").write_text("0.0.1\n", encoding="utf-8")
    set_manifests_dir(manifests)
    report = validate_dataset_bundle("test_bundle", data_root=data, strict=False)
    assert report.ok is False
    itm = next(s for s in report.slots if s.slot_id == "itm_wf")
    assert "VERSION mismatch" in itm.detail


def test_doctor_reports_protection_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from tests.security.test_certs_and_doctor import _write_dummy_certs
    from protection_data.loader import get_data_root

    certs = tmp_path / "certs"
    _write_dummy_certs(certs)
    monkeypatch.setenv("CERTS_DIR", str(certs))
    monkeypatch.setenv("SAS_PROTECTION_DATA_STRICT", "false")
    clear_settings_cache()
    before = get_data_root()
    report = run_doctor()
    pdata = next(item for item in report.findings if item.name == "protection_data")
    assert pdata.ok is True
    assert "cbrs_winnforum_protection" in pdata.detail
    assert get_data_root() == before


def test_doctor_fails_when_strict_and_payload_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from tests.security.test_certs_and_doctor import _write_dummy_certs

    certs = tmp_path / "certs"
    _write_dummy_certs(certs)
    monkeypatch.setenv("CERTS_DIR", str(certs))
    monkeypatch.setenv("SAS_PROTECTION_DATA_STRICT", "true")
    # Point at a root that has VERSION markers but no .flt/.kml payloads.
    manifests = tmp_path / "manifests"
    data = tmp_path / "data"
    manifests.mkdir()
    _write_bundle(manifests, bundle_id="cbrs_winnforum_protection")
    # Rewrite id in file — _write_bundle already sets id from arg
    _seed_markers(data)
    monkeypatch.setenv("SAS_PROTECTION_DATA_ROOT", str(data))
    monkeypatch.setenv("SAS_PROTECTION_DATA_BUNDLE", "cbrs_winnforum_protection")
    set_manifests_dir(manifests)
    clear_settings_cache()
    report = run_doctor()
    pdata = next(item for item in report.findings if item.name == "protection_data")
    assert pdata.ok is False
    assert report.ok is False


def test_file_glob_path_escape_rejected_by_schema():
    from pydantic import ValidationError

    from protection_data.schema import DatasetSlot

    with pytest.raises(ValidationError, match="file_glob"):
        DatasetSlot(
            id="bad",
            kind="terrain_ned",
            version="1",
            relative_path="geo/ned",
            presence="files_glob",
            file_glob="../**/*",
            min_files=1,
        )


def test_assert_ready_default_is_non_strict(tmp_path: Path):
    """Default assert matches Settings (strict=False): markers OK without payloads."""
    manifests = tmp_path / "manifests"
    data = tmp_path / "data"
    manifests.mkdir()
    _write_bundle(manifests)
    _seed_markers(data)
    set_manifests_dir(manifests)
    # Would fail if default strict=True (missing .flt soft payload).
    assert_protection_data_ready("test_bundle", data_root=data)
