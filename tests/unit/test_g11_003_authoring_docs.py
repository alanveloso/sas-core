"""G11-003: reference/custom/plugin authoring docs exist and stay aligned."""

from __future__ import annotations

from pathlib import Path

import yaml

from adapters.discovery import (
    GROUP_DATA_PROVIDERS,
    GROUP_DEVICE_ADAPTERS,
    GROUP_MECHANISMS,
    GROUP_NETWORK_ADAPTERS,
    GROUP_PROTOCOL_ADAPTERS,
    GROUP_RF_MODELS,
)

_REPO = Path(__file__).resolve().parents[2]
_MATRIX = _REPO / "compliance" / "generalization" / "g11_003_authoring_docs.yaml"
_MD = _REPO / "compliance" / "generalization" / "G11-003_AUTHORING_DOCS.md"
_INDEX = _REPO / "docs" / "profiles" / "README.md"
_ARCH = _REPO / "docs" / "profiles" / "architecture_overview.md"
_REF = _REPO / "docs" / "profiles" / "reference_and_custom.md"
_PLUGINS = _REPO / "docs" / "plugins" / "creating_plugins.md"


def _load_matrix() -> dict:
    payload = yaml.safe_load(_MATRIX.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_evidence_and_doc_paths() -> None:
    assert _MATRIX.is_file()
    assert _MD.is_file()
    doc = _load_matrix()
    assert doc["matrix_id"] == "G11-003"
    assert doc["core_country_profile_branches"] is False
    assert doc["yaml_dsl_introduced"] is False
    for row in doc["documents"]:
        assert (_REPO / row["path"]).is_file(), row["path"]


def test_architecture_overview_invariants() -> None:
    text = _ARCH.read_text(encoding="utf-8")
    assert "BandProfile" in text
    assert "Coordination Core" in text
    assert "if country" in text
    assert "capabilities" in text.lower()
    assert "query_assignment" in text
    assert "CONDITIONAL" in text
    assert "builtin_v2" in text
    assert "operator_explicit" in text


def test_reference_custom_authoring_guide() -> None:
    text = _REF.read_text(encoding="utf-8")
    assert "status: custom" in text or "`custom`" in text
    assert "reference" in text
    assert "tools.profile_doctor" in text
    assert "based_on" in text
    assert "PASS_OFFICIAL" in text
    assert "custom_profile.template.yaml" in text
    assert "BandProfile" in text


def test_index_links_plugin_guide() -> None:
    text = _INDEX.read_text(encoding="utf-8")
    assert "creating_plugins.md" in text
    assert "architecture_overview.md" in text
    assert "reference_and_custom.md" in text
    assert "G11-003" in text


def test_plugin_guide_still_lists_groups_and_g11_trust() -> None:
    text = _PLUGINS.read_text(encoding="utf-8")
    assert "G6-003" in text
    assert "G11-003" in text or "G11-001" in text
    for group in (
        GROUP_DEVICE_ADAPTERS,
        GROUP_NETWORK_ADAPTERS,
        GROUP_PROTOCOL_ADAPTERS,
        GROUP_DATA_PROVIDERS,
        GROUP_RF_MODELS,
        GROUP_MECHANISMS,
    ):
        assert group in text
    assert "reservado" in text.lower() or "reserved" in text.lower()
    assert "[a-z][a-z0-9_]*" in text
    assert "data.required_capabilities" in text


def test_readme_points_to_profile_docs() -> None:
    readme = (_REPO / "README.md").read_text(encoding="utf-8")
    assert "docs/profiles/README.md" in readme
    assert "tools.profile_doctor" in readme
