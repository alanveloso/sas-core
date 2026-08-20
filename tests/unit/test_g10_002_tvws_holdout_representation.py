"""G10-002: TVWS holdout representation without core changes (CONDITIONAL)."""

from __future__ import annotations

from pathlib import Path

import yaml

from primitives.registry import MechanismAxis, builtin_mechanism_registry
from spectrum_profiles.loader import ProfileValidationError
from spectrum_profiles.v2.doctor import run_profile_doctor
from spectrum_profiles.v2.parse import load_profile_v2, parse_profile_v2_spectrum

_REPO = Path(__file__).resolve().parents[2]
_PROFILE_ID = "us_tvws_15_711"
_PROFILE_PATH = _REPO / "spectrum_profiles" / "profiles" / "v2" / f"{_PROFILE_ID}.yaml"
_VERDICT_YAML = _REPO / "compliance" / "fcc" / "g10_002_holdout_verdict.yaml"
_VERDICT_MD = _REPO / "compliance" / "fcc" / "G10-002_TVWS_HOLDOUT_REPRESENTATION.md"
_HOLDOUT_MAP = _REPO / "compliance" / "fcc" / "tvws_15_711_holdout_map.yaml"


def _load_verdict() -> dict:
    payload = yaml.safe_load(_VERDICT_YAML.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_representation_files_exist() -> None:
    assert _PROFILE_PATH.is_file()
    assert _VERDICT_YAML.is_file()
    assert _VERDICT_MD.is_file()
    assert _HOLDOUT_MAP.is_file()
    md = _VERDICT_MD.read_text(encoding="utf-8")
    assert "G10-002" in md
    assert "CONDITIONAL" in md
    assert _PROFILE_ID in md


def test_verdict_is_conditional_without_core_changes() -> None:
    doc = _load_verdict()
    assert doc["matrix_id"] == "G10-002"
    assert doc["verdict"] == "CONDITIONAL"
    assert doc["verdict"] in set(doc["allowed_verdicts"])
    assert doc["core_changes"] is False
    assert doc["query_assignment_registered"] is False
    assert doc["profile_specific_python_loc"] == 0
    assert doc["design_contamination"] is False
    assert doc["profile_id"] == _PROFILE_ID


def test_query_assignment_still_unregistered() -> None:
    catalog = builtin_mechanism_registry()
    assert "query_assignment" not in catalog.ids()
    doc = _load_verdict()
    assert doc["query_assignment_registered"] is False


def test_profile_loads_and_omits_authorization() -> None:
    parsed = load_profile_v2(_PROFILE_ID)
    assert parsed.metadata.id == _PROFILE_ID
    assert parsed.authorization is None
    assert parsed.access is None
    assert parsed.geography is not None
    assert parsed.geography.mechanism == "point_radius"
    assert parsed.power is not None
    assert parsed.power.mechanism == "rule_table"
    assert parsed.temporal is not None
    assert parsed.temporal.availability is not None
    assert parsed.temporal.availability.mechanism == "availability_constraint"
    assert "geolocation" in (parsed.requirements.device_capabilities if parsed.requirements else ())


def test_profile_doctor_passes() -> None:
    report = run_profile_doctor(profile_id=_PROFILE_ID)
    assert report.ok, [f for f in report.findings if not f.ok]


def test_query_assignment_as_authorization_is_rejected_by_catalog() -> None:
    """CONDITIONAL proof: cannot select unregistered query_assignment without core change."""
    raw = yaml.safe_load(_PROFILE_PATH.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    raw["authorization"] = {"mechanism": "query_assignment"}
    try:
        parse_profile_v2_spectrum(raw)
        raised = False
    except (ProfileValidationError, ValueError, KeyError):
        raised = True
    assert raised is True
    # Explicit axis lookup also fails closed.
    catalog = builtin_mechanism_registry()
    try:
        catalog.on_axis(MechanismAxis.AUTHORIZATION, "query_assignment")
        axis_ok = True
    except Exception:
        axis_ok = False
    assert axis_ok is False


def test_device_classes_are_profile_data_not_core_mechanisms() -> None:
    parsed = load_profile_v2(_PROFILE_ID)
    classes = {rule.device_class for rule in parsed.power.rules}
    assert "fixed" in classes
    assert "mode_ii" in classes or "mode_i" in classes
    catalog = builtin_mechanism_registry().ids()
    assert "mode_ii" not in catalog
    assert "fixed" not in catalog


def test_markdown_states_conditional_and_profile_path() -> None:
    md = _VERDICT_MD.read_text(encoding="utf-8")
    assert "CONDITIONAL" in md
    assert "us_tvws_15_711.yaml" in md
    assert "query_assignment" in md
