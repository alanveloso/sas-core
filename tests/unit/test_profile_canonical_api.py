"""Canonical profile API aliases and shared error identity (STEP 1A)."""

from __future__ import annotations

from pathlib import Path

import pytest

from spectrum_profiles import errors as shared_errors
from spectrum_profiles.errors import (
    ProfileError,
    ProfileNotFoundError,
    ProfilePathError,
    ProfileValidationError,
)
from spectrum_profiles.loader import (
    ProfileError as LoaderProfileError,
)
from spectrum_profiles.loader import (
    ProfileNotFoundError as LoaderProfileNotFoundError,
)
from spectrum_profiles.loader import (
    ProfilePathError as LoaderProfilePathError,
)
from spectrum_profiles.loader import (
    ProfileValidationError as LoaderProfileValidationError,
)
from spectrum_profiles.v2 import (
    ProfileDocument,
    ProfileV2SpectrumDocument,
    load_profile,
    load_profile_document,
    load_profile_document_with_provenance,
    load_profile_v2,
    load_profile_v2_document,
    load_profile_v2_with_provenance,
    load_profile_with_provenance,
    parse_profile_document,
    parse_profile_v2_spectrum,
    profile_context_from_document,
    profile_context_from_v2,
    profile_hash,
    profile_hash_v2,
)
from spectrum_profiles.v2.trust import ProfileTrustTier, builtin_v2_profiles_dir


def test_shared_error_classes_are_identical_through_loader() -> None:
    assert ProfileError is shared_errors.ProfileError
    assert ProfileNotFoundError is shared_errors.ProfileNotFoundError
    assert ProfileValidationError is shared_errors.ProfileValidationError
    assert ProfilePathError is shared_errors.ProfilePathError
    assert LoaderProfileError is ProfileError
    assert LoaderProfileNotFoundError is ProfileNotFoundError
    assert LoaderProfileValidationError is ProfileValidationError
    assert LoaderProfilePathError is ProfilePathError


def test_profile_document_alias_and_canonical_loads() -> None:
    assert ProfileDocument is ProfileV2SpectrumDocument
    for profile_id in (
        "cbrs_winnforum",
        "br_anatel_slp_3700",
        "eu_elsa",
        "us_tvws_15_711",
    ):
        doc = load_profile(profile_id)
        assert isinstance(doc, ProfileDocument)
        assert doc.metadata.id == profile_id


def test_canonical_api_equivalent_to_legacy_v2_names() -> None:
    left = load_profile("cbrs_winnforum")
    right = load_profile_v2("cbrs_winnforum")
    assert left == right
    assert profile_hash(left) == profile_hash_v2(right)
    assert profile_context_from_document(left) == profile_context_from_v2(right)

    payload = left.model_dump(mode="json", exclude_none=True)
    assert parse_profile_document(payload) == parse_profile_v2_spectrum(payload)

    path = builtin_v2_profiles_dir() / "cbrs_winnforum.yaml"
    assert load_profile_document(path) == load_profile_v2_document(path)
    with_prov = load_profile_with_provenance("cbrs_winnforum")
    legacy_prov = load_profile_v2_with_provenance("cbrs_winnforum")
    assert with_prov[0] == legacy_prov[0]
    assert with_prov[1] == legacy_prov[1]
    assert with_prov[1].trust_tier is ProfileTrustTier.BUILTIN_V2

    path_prov = load_profile_document_with_provenance(path)
    assert path_prov[0].metadata.id == "cbrs_winnforum"
    assert path_prov[1].trust_tier is ProfileTrustTier.OPERATOR_EXPLICIT


def test_canonical_load_fail_closed_shared_errors() -> None:
    with pytest.raises(ProfileValidationError):
        load_profile("../etc/passwd")
    with pytest.raises(ProfileNotFoundError):
        load_profile("does_not_exist_profile_xyz")
    with pytest.raises(ProfileValidationError):
        parse_profile_document({"not": "a profile"})
    missing = Path("/tmp/spectrum_access_missing_profile_step1a.yaml")
    with pytest.raises(ProfileNotFoundError):
        load_profile_document(missing)
