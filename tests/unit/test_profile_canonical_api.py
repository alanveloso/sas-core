"""Canonical profile API aliases, shared errors, and root package exports."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

import spectrum_profiles
from spectrum_profiles import errors as shared_errors
from spectrum_profiles.errors import (
    ProfileError,
    ProfileNotFoundError,
    ProfilePathError,
    ProfileValidationError,
)
from spectrum_profiles.v2 import (
    ProfileDocument,
    ProfileV2SpectrumDocument,
    load_profile as v2_load_profile,
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
    profile_hash as v2_profile_hash,
    profile_hash_v2,
)
from spectrum_profiles.v2.trust import ProfileTrustTier, builtin_v2_profiles_dir

_ROOT_INIT = Path(__file__).resolve().parents[2] / "spectrum_profiles" / "__init__.py"


def test_shared_error_classes_from_errors_module() -> None:
    assert ProfileError is shared_errors.ProfileError
    assert ProfileNotFoundError is shared_errors.ProfileNotFoundError
    assert ProfileValidationError is shared_errors.ProfileValidationError
    assert ProfilePathError is shared_errors.ProfilePathError


def test_profile_document_alias_and_canonical_loads() -> None:
    assert ProfileDocument is ProfileV2SpectrumDocument
    for profile_id in (
        "cbrs_winnforum",
        "br_anatel_slp_3700",
        "eu_elsa",
        "us_tvws_15_711",
    ):
        doc = v2_load_profile(profile_id)
        assert isinstance(doc, ProfileDocument)
        assert doc.metadata.id == profile_id


def test_canonical_api_equivalent_to_legacy_v2_names() -> None:
    left = v2_load_profile("cbrs_winnforum")
    right = load_profile_v2("cbrs_winnforum")
    assert left == right
    assert v2_profile_hash(left) == profile_hash_v2(right)
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
        v2_load_profile("../etc/passwd")
    with pytest.raises(ProfileNotFoundError):
        v2_load_profile("does_not_exist_profile_xyz")
    with pytest.raises(ProfileValidationError):
        parse_profile_document({"not": "a profile"})
    missing = Path("/tmp/spectrum_access_missing_profile_step1a.yaml")
    with pytest.raises(ProfileNotFoundError):
        load_profile_document(missing)


def test_root_load_profile_returns_canonical_document() -> None:
    doc = spectrum_profiles.load_profile("cbrs_winnforum")
    assert isinstance(doc, spectrum_profiles.ProfileDocument)
    assert doc.metadata.id == "cbrs_winnforum"
    assert doc.metadata.version == "2.0.0"
    assert spectrum_profiles.primary_spectrum_range(doc).low_hz == 3_550_000_000


def test_root_load_profile_matches_v2_namespace() -> None:
    root_doc = spectrum_profiles.load_profile("cbrs_winnforum")
    ns_doc = v2_load_profile("cbrs_winnforum")
    assert root_doc.metadata.id == ns_doc.metadata.id
    assert root_doc.metadata.version == ns_doc.metadata.version
    assert spectrum_profiles.profile_hash(root_doc) == v2_profile_hash(ns_doc)


def test_root_exports_canonical_symbols() -> None:
    for name in (
        "ProfileDocument",
        "ProfileError",
        "ProfileValidationError",
        "DEFAULT_PROFILE_ID",
        "active_profile_id",
        "get_active_profile_document",
        "set_active_profile_document",
        "reload_active_profile_document",
        "primary_spectrum_range",
        "canonical_profile_json",
        "profile_hash",
        "parse_profile_document",
    ):
        assert hasattr(spectrum_profiles, name), name
        assert name in spectrum_profiles.__all__


def test_root_does_not_export_v1_symbols() -> None:
    banned = (
        "SpectrumProfile",
        "BandPlan",
        "ProtectionRule",
        "EntityParams",
        "get_active_profile",
        "set_active_profile",
        "reload_active_profile",
        "project_v1_to_v2_document",
        "DEFAULT_PROFILES_DIR",
        "get_profiles_dir",
        "set_profiles_dir",
        "clear_profile_cache",
        "load_profile_v2",
        "ProfileV2SpectrumDocument",
    )
    for name in banned:
        assert not hasattr(spectrum_profiles, name), name
        assert name not in spectrum_profiles.__all__


def test_root_init_does_not_import_deleted_v1_modules() -> None:
    tree = ast.parse(_ROOT_INIT.read_text(encoding="utf-8"))
    forbidden = {
        "spectrum_profiles.schema",
        "spectrum_profiles.loader",
        "spectrum_profiles.context",
        "spectrum_profiles.v2.migrate",
    }
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    assert not (found & forbidden)


def test_root_import_smoke_subprocess() -> None:
    script = (
        "import spectrum_profiles as sp\n"
        "doc = sp.load_profile('cbrs_winnforum')\n"
        "assert isinstance(doc, sp.ProfileDocument)\n"
        "assert doc.metadata.id == 'cbrs_winnforum'\n"
        "assert sp.get_active_profile_document().metadata.id\n"
        "print('PASS')\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[2]),
    )
    assert proc.returncode == 0, proc.stderr
    assert "PASS" in proc.stdout
