"""Packaging: editable install exposes protection_data + spectrum profile assets."""

from __future__ import annotations

from importlib import resources

import spectrum_profiles
import protection_data


def test_spectrum_profiles_package_ships_default_yaml():
    root = resources.files(spectrum_profiles)
    profiles = root.joinpath("profiles")
    assert profiles.joinpath("cbrs_winnforum.yaml").is_file()
    assert profiles.joinpath("v2").joinpath("cbrs_winnforum.yaml").is_file()


def test_protection_data_package_ships_default_manifest():
    root = resources.files(protection_data)
    manifests = root.joinpath("manifests")
    assert manifests.joinpath("cbrs_winnforum_protection.yaml").is_file()
