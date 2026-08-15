"""Profile YAML v2 (incremental). G3-001: spectrum/ranges/channelization/segments."""

from spectrum_profiles.v2.context import profile_context_from_v2, profile_hash_v2
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
    "profile_context_from_v2",
    "profile_hash_v2",
    "validate_profile_v2_semantics",
]
