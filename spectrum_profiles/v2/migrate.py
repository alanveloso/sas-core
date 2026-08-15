"""Project a v1 SpectrumProfile onto a Profile v2 spectrum document.

This does not replace ``load_profile``. CBRS entity packs and IAP/DPA stay on v1.
Assignment channel width is the current CBRS SIQ grid projected as profile data (D13).
"""

from __future__ import annotations

from spectrum_profiles.schema import SpectrumProfile

# CBRS v1 assignment grid (Hz). Not imported from services to avoid coupling.
_CBRS_ASSIGNMENT_CHANNEL_HZ = 10_000_000


def project_v1_to_v2_document(profile: SpectrumProfile) -> dict:
    """Return a v2 mapping with spectrum + assignment channelization only."""
    low_hz = int(profile.band_plan.low_hz)
    high_hz = int(profile.band_plan.high_hz)
    return {
        "api_version": "spectrum-access/v2",
        "kind": "SpectrumProfile",
        "metadata": {
            "id": profile.id,
            "version": profile.version,
            "status": "reference",
            "based_on": None,
        },
        "spectrum": {
            "ranges": [
                {
                    "id": "primary",
                    "low_hz": low_hz,
                    "high_hz": high_hz,
                }
            ],
            "channelization": {
                "mechanism": "fixed_width_channelization",
                "width_hz": _CBRS_ASSIGNMENT_CHANNEL_HZ,
                "origin_hz": low_hz,
                "role": "assignment",
            },
        },
    }
