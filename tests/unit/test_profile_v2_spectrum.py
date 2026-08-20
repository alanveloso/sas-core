"""G3-001: Profile v2 spectrum ranges, segments, optional assignment channelization."""

from __future__ import annotations

import pytest

from primitives.registry import builtin_mechanism_registry
from spectrum_profiles.loader import ProfileValidationError, load_profile
from spectrum_profiles.v2.parse import parse_profile_v2_spectrum


def _doc(**spectrum_extra: object) -> dict:
    spectrum = {
        "ranges": [
            {
                "id": "main",
                "low_hz": 3_550_000_000,
                "high_hz": 3_700_000_000,
                "segments": [
                    {
                        "id": "lower",
                        "low_hz": 3_550_000_000,
                        "high_hz": 3_650_000_000,
                    }
                ],
            }
        ]
    }
    spectrum.update(spectrum_extra)
    return {
        "api_version": "spectrum-access/v2",
        "kind": "SpectrumProfile",
        "metadata": {"id": "example_multi", "version": "1.0.0", "status": "custom"},
        "spectrum": spectrum,
    }


def test_parses_multiple_ranges_and_optional_channelization():
    doc = _doc(
        ranges=[
            {"id": "a", "low_hz": 1000, "high_hz": 2000},
            {"id": "b", "low_hz": 3000, "high_hz": 4000},
        ],
        channelization={
            "mechanism": "fixed_width_channelization",
            "width_hz": 100,
            "origin_hz": 1000,
            "role": "assignment",
        },
    )
    parsed = parse_profile_v2_spectrum(doc)
    assert len(parsed.spectrum.ranges) == 2
    assert parsed.spectrum.channelization is not None
    assert parsed.spectrum.channelization.origin_hz == 1000
    assert parse_profile_v2_spectrum(_doc()).spectrum.channelization is None


def test_rejects_overlap_bad_segment_and_unregistered_mechanism():
    with pytest.raises(ProfileValidationError):
        parse_profile_v2_spectrum(
            _doc(
                ranges=[
                    {"id": "a", "low_hz": 1000, "high_hz": 2000},
                    {"id": "b", "low_hz": 1500, "high_hz": 2500},
                ]
            )
        )
    with pytest.raises(ProfileValidationError):
        parse_profile_v2_spectrum(
            _doc(
                ranges=[
                    {
                        "id": "main",
                        "low_hz": 1000,
                        "high_hz": 2000,
                        "segments": [{"id": "out", "low_hz": 1500, "high_hz": 3000}],
                    }
                ]
            )
        )
    bad = _doc(
        channelization={
            "mechanism": "not_a_grid",
            "width_hz": 10,
            "origin_hz": 0,
        }
    )
    with pytest.raises(ProfileValidationError):
        parse_profile_v2_spectrum(bad)
    registry = builtin_mechanism_registry()
    assert "fixed_width_channelization" in registry.ids()


def test_rejects_expressions_and_does_not_break_v1_cbrs_loader():
    with pytest.raises(ProfileValidationError):
        parse_profile_v2_spectrum(
            {
                "api_version": "spectrum-access/v2",
                "kind": "SpectrumProfile",
                "metadata": {"id": "x", "version": "1"},
                "spectrum": {"ranges": []},
            }
        )
    extra = _doc()
    extra["spectrum"]["if"] = "low_hz > 1"
    with pytest.raises(ProfileValidationError):
        parse_profile_v2_spectrum(extra)
    v1 = load_profile("cbrs_winnforum")
    assert v1.band_plan.low_hz == 3_550_000_000
