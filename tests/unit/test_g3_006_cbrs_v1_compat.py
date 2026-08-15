"""G3-006: v1 cbrs_winnforum loader stays; optional projection onto Profile v2."""

from __future__ import annotations

from pathlib import Path

import pytest

from spectrum_profiles.loader import ProfileValidationError, load_profile
from spectrum_profiles.v2.context import profile_context_from_v2
from spectrum_profiles.v2.migrate import project_v1_to_v2_document
from spectrum_profiles.v2.parse import parse_profile_v2_spectrum


def test_v1_loader_still_returns_cbrs_band_plan():
    profile = load_profile("cbrs_winnforum")
    assert profile.id == "cbrs_winnforum"
    assert profile.band_plan.low_hz == 3_550_000_000
    assert profile.band_plan.high_hz == 3_700_000_000
    assert profile.get_entity("esc") is not None


def test_v1_projects_to_parseable_v2_spectrum_without_entity_nouns():
    v1 = load_profile("cbrs_winnforum")
    raw = project_v1_to_v2_document(v1)
    parsed = parse_profile_v2_spectrum(raw)
    assert parsed.metadata.id == "cbrs_winnforum"
    assert parsed.metadata.status == "reference"
    rng = parsed.spectrum.ranges[0]
    assert rng.low_hz == v1.band_plan.low_hz
    assert rng.high_hz == v1.band_plan.high_hz
    assert parsed.spectrum.channelization is not None
    assert parsed.spectrum.channelization.role == "assignment"
    assert parsed.spectrum.channelization.width_hz == 10_000_000
    assert parsed.access is None
    ctx = profile_context_from_v2(parsed)
    assert ctx.profile_id == "cbrs_winnforum"
    blob = str(raw).lower()
    assert "esc" not in blob
    assert "ppa" not in blob
    assert "pal" not in blob


def test_v1_loader_rejects_v2_documents(tmp_path: Path):
    v2_file = tmp_path / "demo.yaml"
    v2_file.write_text(
        "\n".join(
            [
                "api_version: spectrum-access/v2",
                "kind: SpectrumProfile",
                "metadata:",
                "  id: demo",
                "  version: '1.0.0'",
                "spectrum:",
                "  ranges:",
                "    - id: main",
                "      low_hz: 1000",
                "      high_hz: 2000",
            ]
        ),
        encoding="utf-8",
    )
    from spectrum_profiles.loader import set_profiles_dir, clear_profile_cache

    set_profiles_dir(tmp_path)
    try:
        with pytest.raises(ProfileValidationError, match="Profile v2"):
            load_profile("demo")
    finally:
        set_profiles_dir(None)
        clear_profile_cache()
