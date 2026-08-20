"""G7-005: multi-profile coexistence proof + CBRS non-regression (local).

Does not claim WInnForum PASS_OFFICIAL. Official harness remains G5-009 / G11-005.
"""

from __future__ import annotations

from pathlib import Path

from spectrum_profiles.context import (
    DEFAULT_PROFILE_ID,
    active_profile_id,
    clear_profile_override,
    get_active_profile,
)
from spectrum_profiles.loader import load_profile
from spectrum_profiles.v2.context import profile_context_from_v2, profile_hash_v2
from spectrum_profiles.v2.cost import measure_profile_cost
from spectrum_profiles.v2.doctor import run_profile_doctor
from spectrum_profiles.v2.parse import load_profile_v2

_REPO = Path(__file__).resolve().parents[2]


def test_default_active_profile_remains_cbrs_v1() -> None:
    clear_profile_override()
    assert DEFAULT_PROFILE_ID == "cbrs_winnforum"
    assert active_profile_id() == "cbrs_winnforum"
    active = get_active_profile()
    assert active.id == "cbrs_winnforum"
    assert active.version == "1.0.0"
    assert active.band_plan.low_hz == 3_550_000_000
    assert active.band_plan.high_hz == 3_700_000_000


def test_load_br_v2_does_not_mutate_cbrs_v1_active_or_band() -> None:
    clear_profile_override()
    before = load_profile("cbrs_winnforum")
    br = load_profile_v2("br_anatel_slp_3700")
    after = load_profile("cbrs_winnforum")
    assert br.metadata.id == "br_anatel_slp_3700"
    assert before.band_plan.low_hz == after.band_plan.low_hz == 3_550_000_000
    assert before.band_plan.high_hz == after.band_plan.high_hz == 3_700_000_000
    assert get_active_profile().id == "cbrs_winnforum"
    # BR must not be selectable via v1 active profile loader.
    assert br.metadata.id != active_profile_id()


def test_multi_profile_contexts_are_isolated() -> None:
    cbrs = load_profile_v2("cbrs_winnforum")
    br = load_profile_v2("br_anatel_slp_3700")
    ctx_cbrs = profile_context_from_v2(cbrs)
    ctx_br = profile_context_from_v2(br)
    assert ctx_cbrs.profile_id == "cbrs_winnforum"
    assert ctx_br.profile_id == "br_anatel_slp_3700"
    assert ctx_cbrs.profile_hash != ctx_br.profile_hash
    assert ctx_cbrs.profile_hash == profile_hash_v2(cbrs)
    assert ctx_br.profile_hash == profile_hash_v2(br)
    # Distinct regime shapes
    assert cbrs.access is not None
    assert br.access is None
    assert cbrs.authorization is not None and cbrs.authorization.mechanism == "dynamic_lease"
    assert br.authorization is not None and br.authorization.mechanism == "static_authorization"
    assert cbrs.rf is not None and cbrs.rf.required is True
    assert br.rf is not None and br.rf.required is False
    assert cbrs.constraints == ()
    assert len(br.constraints) >= 4


def test_both_reference_profiles_pass_doctor() -> None:
    for profile_id in ("cbrs_winnforum", "br_anatel_slp_3700"):
        report = run_profile_doctor(profile_id=profile_id)
        assert report.ok, profile_id + ": " + "; ".join(
            f"{f.name}={f.detail}" for f in report.findings if not f.ok
        )


def test_mechanism_reuse_full_catalog_for_both_profiles() -> None:
    for profile_id in ("cbrs_winnforum", "br_anatel_slp_3700"):
        cost = measure_profile_cost(profile_id=profile_id, repo_root=_REPO)
        assert cost.mechanism_reuse_pct == 100.0, profile_id
        assert cost.mechanisms_novel == ()
        assert cost.profile_python_loc == 0


def test_cbrs_v1_request_path_profile_dir_ignores_v2_br_file() -> None:
    """v1 loader catalogs only profiles/*.yaml — not profiles/v2/."""
    from spectrum_profiles.loader import get_profiles_dir

    v1_dir = get_profiles_dir()
    assert (v1_dir / "cbrs_winnforum.yaml").is_file()
    assert not (v1_dir / "br_anatel_slp_3700.yaml").exists()
    assert (v1_dir / "v2" / "br_anatel_slp_3700.yaml").is_file()
    # v1 load of BR id must fail (not on v1 path)
    from spectrum_profiles.loader import ProfileNotFoundError

    try:
        load_profile("br_anatel_slp_3700")
        raise AssertionError("v1 loader must not resolve BR v2-only profile")
    except ProfileNotFoundError:
        pass


def test_interleaved_loads_preserve_invariants() -> None:
    """Alternate loads; CBRS band and BR constraints remain stable."""
    for _ in range(3):
        cbrs = load_profile_v2("cbrs_winnforum")
        br = load_profile_v2("br_anatel_slp_3700")
        v1 = load_profile("cbrs_winnforum")
        assert v1.band_plan.high_hz == 3_700_000_000
        assert cbrs.spectrum.ranges[0].high_hz == 3_700_000_000
        assert br.spectrum.ranges[0].low_hz == 3_700_000_000
        assert [c.mechanism for c in br.constraints][0] == "duplex_mode"
