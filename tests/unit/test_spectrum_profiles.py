"""Tests for spectrum profile loading, validation, cache and overrides."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from spectrum_profiles.context import (
    clear_profile_override,
    get_active_profile,
    set_active_profile,
)
from spectrum_profiles.loader import (
    ProfileNotFoundError,
    ProfilePathError,
    ProfileValidationError,
    clear_profile_cache,
    load_profile,
    set_profiles_dir,
)


@pytest.fixture(autouse=True)
def _reset_profile_state(tmp_path: Path):
    """Isolate each test from shared cache / override / directory state."""
    clear_profile_override()
    clear_profile_cache()
    set_profiles_dir(None)
    yield
    clear_profile_override()
    clear_profile_cache()
    set_profiles_dir(None)


def _write_profile(directory: Path, profile_id: str, body: str, suffix: str = ".yaml") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{profile_id}{suffix}"
    path.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
    return path


VALID_OVERRIDE = """
id: lab_override
version: "0.1.0"
description: Temporary override profile for tests
rule_applied: test_override_rule
band_plan:
  low_hz: 3550000000
  high_hz: 3650000000
  unit: Hz
protections:
  - name: peer_esc
    enabled: false
    params:
      radius_m: 1000
entities: []
"""


def test_load_default_cbrs_winnforum_profile():
    profile = load_profile("cbrs_winnforum")
    assert profile.id == "cbrs_winnforum"
    assert profile.version == "1.0.0"
    assert profile.rule_applied == "winnforum_cbrs_baseline_v1"
    assert profile.band_plan.low_hz == 3_550_000_000
    assert profile.band_plan.high_hz == 3_700_000_000
    assert profile.band_plan.unit == "Hz"
    esc = profile.get_protection("peer_esc")
    assert esc is not None and esc.enabled
    assert esc.params["radius_m"] == 40_000
    ppa = profile.get_protection("peer_ppa")
    assert ppa is not None and ppa.params["buffer_m"] == 1_000


def test_load_profile_uses_cache():
    first = load_profile("cbrs_winnforum")
    second = load_profile("cbrs_winnforum")
    assert first is second


def test_missing_profile_raises(tmp_path: Path):
    set_profiles_dir(tmp_path)
    with pytest.raises(ProfileNotFoundError, match="not found"):
        load_profile("does_not_exist")


def test_malformed_yaml_raises(tmp_path: Path):
    _write_profile(tmp_path, "broken", "id: [unterminated\n")
    set_profiles_dir(tmp_path)
    with pytest.raises(ProfileValidationError, match="malformed"):
        load_profile("broken")


def test_invalid_band_plan_raises(tmp_path: Path):
    _write_profile(
        tmp_path,
        "bad_band",
        """
        id: bad_band
        version: "0.0.1"
        rule_applied: invalid
        band_plan:
          low_hz: 3700000000
          high_hz: 3550000000
          unit: Hz
        """,
    )
    set_profiles_dir(tmp_path)
    with pytest.raises(ProfileValidationError, match="failed validation"):
        load_profile("bad_band")


def test_invalid_frequency_unit_raises(tmp_path: Path):
    _write_profile(
        tmp_path,
        "bad_unit",
        """
        id: bad_unit
        version: "0.0.1"
        rule_applied: invalid
        band_plan:
          low_hz: 3550000000
          high_hz: 3700000000
          unit: MHz
        """,
    )
    set_profiles_dir(tmp_path)
    with pytest.raises(ProfileValidationError, match="failed validation"):
        load_profile("bad_unit")


def test_non_numeric_protection_quantity_raises(tmp_path: Path):
    _write_profile(
        tmp_path,
        "bad_params",
        """
        id: bad_params
        version: "0.0.1"
        rule_applied: invalid
        band_plan:
          low_hz: 3550000000
          high_hz: 3700000000
          unit: Hz
        protections:
          - name: peer_esc
            enabled: true
            params:
              radius_m: not-a-number
        """,
    )
    set_profiles_dir(tmp_path)
    with pytest.raises(ProfileValidationError, match="failed validation"):
        load_profile("bad_params")


def test_protection_frequency_outside_band_raises(tmp_path: Path):
    _write_profile(
        tmp_path,
        "outside_band",
        """
        id: outside_band
        version: "0.0.1"
        rule_applied: invalid
        band_plan:
          low_hz: 3550000000
          high_hz: 3700000000
          unit: Hz
        protections:
          - name: peer_esc
            enabled: true
            params:
              low_hz: 3400000000
              high_hz: 3700000000
        """,
    )
    set_profiles_dir(tmp_path)
    with pytest.raises(ProfileValidationError, match="failed validation"):
        load_profile("outside_band")


def test_id_mismatch_raises(tmp_path: Path):
    _write_profile(
        tmp_path,
        "requested",
        """
        id: other_id
        version: "0.0.1"
        rule_applied: mismatch
        band_plan:
          low_hz: 3550000000
          high_hz: 3700000000
          unit: Hz
        """,
    )
    set_profiles_dir(tmp_path)
    with pytest.raises(ProfileValidationError, match="id mismatch"):
        load_profile("requested")


def test_path_traversal_profile_id_rejected():
    with pytest.raises(ProfilePathError, match="invalid profile id"):
        load_profile("../etc/passwd")


def test_set_active_profile_override(tmp_path: Path):
    _write_profile(tmp_path, "lab_override", VALID_OVERRIDE)
    set_profiles_dir(tmp_path)
    profile = set_active_profile("lab_override")
    assert profile.id == "lab_override"
    assert get_active_profile().rule_applied == "test_override_rule"
    assert get_active_profile().band_plan.high_hz == 3_650_000_000
    clear_profile_override()


def test_loaded_profile_models_are_frozen():
    """G1-002: ProfileContext seed objects must be immutable at runtime (D4)."""
    from pydantic import ValidationError

    profile = load_profile("cbrs_winnforum")
    with pytest.raises(ValidationError):
        profile.id = "mutated"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        profile.band_plan.low_hz = 3_600_000_000  # type: ignore[misc]
    esc = profile.get_protection("peer_esc")
    assert esc is not None
    with pytest.raises(ValidationError):
        esc.enabled = False  # type: ignore[misc]
    # Default YAML observables frozen for extraction regressions.
    assert esc.params["radius_m"] == 40_000
    assert profile.get_protection("peer_ppa").params["buffer_m"] == 1_000
