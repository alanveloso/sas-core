"""Profile YAML v2 (incremental). G3-001: spectrum/ranges/channelization/segments."""

from spectrum_profiles.v2.parse import parse_profile_v2_spectrum
from spectrum_profiles.v2.schema import (
    FixedWidthChannelization,
    ProfileMetadata,
    ProfileV2SpectrumDocument,
    SpectrumRange,
    SpectrumSection,
    SpectrumSegment,
)

__all__ = [
    "FixedWidthChannelization",
    "ProfileMetadata",
    "ProfileV2SpectrumDocument",
    "SpectrumRange",
    "SpectrumSection",
    "SpectrumSegment",
    "parse_profile_v2_spectrum",
]
