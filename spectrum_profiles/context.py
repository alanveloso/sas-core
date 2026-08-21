"""Active spectrum profile selection via SAS_PROFILE (v1 document load)."""

from __future__ import annotations

from spectrum_profiles.loader import clear_profile_cache, load_profile
from spectrum_profiles.schema import SpectrumProfile
from spectrum_profiles.selection import (
    DEFAULT_PROFILE_ID,
    active_profile_id,
    clear_profile_override as clear_selection_override,
    set_profile_override,
)

__all__ = [
    "DEFAULT_PROFILE_ID",
    "active_profile_id",
    "clear_profile_override",
    "get_active_profile",
    "reload_active_profile",
    "set_active_profile",
]


def get_active_profile() -> SpectrumProfile:
    return load_profile(active_profile_id())


def set_active_profile(profile_id: str) -> SpectrumProfile:
    """Force-select a profile (tests / admin). Clears loader cache for that id."""
    set_profile_override(profile_id)
    clear_profile_cache()
    return get_active_profile()


def reload_active_profile() -> SpectrumProfile:
    clear_profile_cache()
    return get_active_profile()


def clear_profile_override() -> None:
    clear_selection_override()
    clear_profile_cache()
