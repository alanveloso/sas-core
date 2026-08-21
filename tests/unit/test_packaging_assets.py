"""Packaging: editable install exposes protection_data + spectrum profile assets."""

from __future__ import annotations

from importlib import resources

import protection_data
import spectrum_profiles


def test_spectrum_profiles_package_ships_canonical_yaml() -> None:
    root = resources.files(spectrum_profiles)
    profiles = root.joinpath("profiles").joinpath("v2")
    for name in (
        "cbrs_winnforum.yaml",
        "br_anatel_slp_3700.yaml",
        "eu_elsa.yaml",
        "us_tvws_15_711.yaml",
    ):
        assert profiles.joinpath(name).is_file(), name


def test_protection_data_package_ships_default_manifest() -> None:
    root = resources.files(protection_data)
    manifests = root.joinpath("manifests")
    assert manifests.joinpath("cbrs_winnforum_protection.yaml").is_file()
