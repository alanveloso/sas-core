"""Profile YAML v2 (incremental). G3-001: spectrum/ranges/channelization/segments."""

from spectrum_profiles.v2.parse import parse_profile_v2_spectrum
from spectrum_profiles.v2.semantics import validate_profile_v2_semantics
from spectrum_profiles.v2.schema import (
    AccessSection,
    AuthorizationSection,
    FixedWidthChannelization,
    GeographySection,
    PowerSection,
    ProfileMetadata,
    ProfileV2SpectrumDocument,
    ProtectionSection,
    RfSection,
    SpectrumRange,
    SpectrumSection,
    SpectrumSegment,
    TemporalSection,
)

__all__ = [
    "AccessSection",
    "AuthorizationSection",
    "FixedWidthChannelization",
    "GeographySection",
    "PowerSection",
    "ProfileMetadata",
    "ProfileV2SpectrumDocument",
    "ProtectionSection",
    "RfSection",
    "SpectrumRange",
    "SpectrumSection",
    "SpectrumSegment",
    "TemporalSection",
    "parse_profile_v2_spectrum",
    "validate_profile_v2_semantics",
]
