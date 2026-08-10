"""G1-002 characterization: assignment grid ≠ RF aggregation + pure RF math.

Freezes observables that generalization must preserve (G0-005 D13 / D18 / D21).
Does not change product behavior.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from services.iap.aggregate import (
    IAPBW_HZ,
    dbm_to_mw,
    grant_overlaps_channel,
    mw_to_dbm,
    overlapping_iap_channels,
    resolve_iap_band_origin_hz,
    sum_interference_mw,
)
from services.iap.models import FrequencyChannel, GrantRfInfo
from services.spectrum_inquiry_service import CHANNEL_HZ, _split_10mhz
from spectrum_profiles.context import (
    clear_profile_override,
    get_active_profile,
    set_active_profile,
)
from spectrum_profiles.loader import clear_profile_cache, set_profiles_dir


@pytest.fixture(autouse=True)
def _reset_profile_state():
    clear_profile_override()
    clear_profile_cache()
    set_profiles_dir(None)
    yield
    clear_profile_override()
    clear_profile_cache()
    set_profiles_dir(None)


def test_assignment_and_aggregation_channel_widths_are_independent():
    """D13: SIQ assignment grid (10 MHz) ≠ IAP aggregation resolution (5 MHz)."""
    assert CHANNEL_HZ == 10_000_000
    assert IAPBW_HZ == 5_000_000
    assert CHANNEL_HZ != IAPBW_HZ

    assignment = _split_10mhz(3_550_000_000, 3_570_000_000)
    full_width = [ch for ch in assignment if ch[1] - ch[0] == CHANNEL_HZ]
    assert full_width == [
        (3_550_000_000, 3_560_000_000),
        (3_560_000_000, 3_570_000_000),
    ]

    aggregation = overlapping_iap_channels(
        3_550_000_000,
        3_560_000_000,
        channel_hz=IAPBW_HZ,
        band_origin_hz=3_550_000_000,
    )
    assert [c.high_hz - c.low_hz for c in aggregation] == [IAPBW_HZ, IAPBW_HZ]
    assert aggregation[0].low_hz == 3_550_000_000
    assert aggregation[-1].high_hz == 3_560_000_000

    # Custom IAP resolution must not mutate the SIQ assignment constant.
    custom = overlapping_iap_channels(
        3_550_000_000,
        3_560_000_000,
        channel_hz=2_500_000,
        band_origin_hz=3_550_000_000,
    )
    assert all(c.high_hz - c.low_hz == 2_500_000 for c in custom)
    assert CHANNEL_HZ == 10_000_000
    assert IAPBW_HZ == 5_000_000


def test_dbm_mw_round_trip_and_non_positive_floor():
    assert dbm_to_mw(30.0) == pytest.approx(1000.0)
    assert mw_to_dbm(1000.0) == pytest.approx(30.0)
    assert mw_to_dbm(dbm_to_mw(-10.0)) == pytest.approx(-10.0)
    assert mw_to_dbm(0.0) == float("-inf")
    assert mw_to_dbm(-1.0) == float("-inf")
    assert math.isinf(mw_to_dbm(0.0)) and mw_to_dbm(0.0) < 0


def test_sum_interference_mw_clamps_negatives():
    assert sum_interference_mw([1.0, -2.0, 3.0]) == 4.0
    assert sum_interference_mw([]) == 0.0


def test_grant_overlaps_channel_partial_true_touching_false():
    grant = GrantRfInfo(
        grant_id="g1",
        cbsd_id="c1",
        latitude=39.0,
        longitude=-77.0,
        low_hz=3_550_000_000,
        high_hz=3_560_000_000,
        max_eirp_dbm_mhz=20.0,
    )
    overlapping = FrequencyChannel(low_hz=3_555_000_000, high_hz=3_565_000_000)
    touching = FrequencyChannel(low_hz=3_560_000_000, high_hz=3_565_000_000)
    assert grant_overlaps_channel(grant, overlapping) is True
    assert grant_overlaps_channel(grant, touching) is False


def test_iap_band_origin_follows_active_profile_low_hz(tmp_path: Path):
    assert resolve_iap_band_origin_hz() == get_active_profile().band_plan.low_hz
    assert resolve_iap_band_origin_hz() == 3_550_000_000

    (tmp_path / "shifted.yaml").write_text(
        """
id: shifted
version: "0.0.1"
rule_applied: characterization_origin
band_plan:
  low_hz: 3560000000
  high_hz: 3700000000
  unit: Hz
protections: []
entities: []
""".lstrip(),
        encoding="utf-8",
    )
    set_profiles_dir(tmp_path)
    set_active_profile("shifted")
    assert resolve_iap_band_origin_hz() == 3_560_000_000

    # Default path (band_origin_hz=None) realigns to the active profile origin.
    chans = overlapping_iap_channels(3_560_000_000, 3_570_000_000)
    assert chans[0].low_hz == 3_560_000_000
    assert all(c.high_hz - c.low_hz == IAPBW_HZ for c in chans)
