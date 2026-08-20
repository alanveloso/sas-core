"""G5-008: local behavioral comparison after CBRS recomposition.

Not an official WInnForum harness campaign (that is G5-009).
"""

from __future__ import annotations

from spectrum_profiles.loader import load_profile
from spectrum_profiles.v2.parse import load_profile_v2
from services.grant_service import DEFAULT_GRANT_DURATION_SEC, HEARTBEAT_INTERVAL_SEC
from services.spectrum_inquiry_service import CBRS_HIGH_HZ, CBRS_LOW_HZ, CHANNEL_HZ


def test_runtime_cbrs_constants_match_v2_composition():
    v1 = load_profile("cbrs_winnforum")
    v2 = load_profile_v2("cbrs_winnforum")
    rng = v2.spectrum.ranges[0]
    ch = v2.spectrum.channelization
    assert ch is not None
    assert v2.authorization is not None
    assert v2.temporal is not None
    assert v2.temporal.reevaluation is not None

    assert v1.band_plan.low_hz == rng.low_hz == CBRS_LOW_HZ == 3_550_000_000
    assert v1.band_plan.high_hz == rng.high_hz == CBRS_HIGH_HZ == 3_700_000_000
    assert ch.width_hz == CHANNEL_HZ == 10_000_000
    assert ch.origin_hz == CBRS_LOW_HZ
    assert v2.authorization.duration_s == DEFAULT_GRANT_DURATION_SEC == 900
    assert v2.temporal.reevaluation.interval_s == HEARTBEAT_INTERVAL_SEC == 60
    assert v1.version == "1.0.0"
    assert v2.metadata.version == "2.0.0"
    assert v1.get_entity("esc") is not None
