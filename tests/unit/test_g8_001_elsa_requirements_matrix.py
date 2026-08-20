"""G8-001: ETSI eLSA requirements matrix integrity (network + availability focus)."""

from __future__ import annotations

from pathlib import Path

import yaml

from primitives.registry import builtin_mechanism_registry
from providers.contract import DATA_CAPABILITIES

_REPO = Path(__file__).resolve().parents[2]
_MATRIX_YAML = _REPO / "compliance" / "etsi" / "elsa_requirements_matrix.yaml"
_MATRIX_MD = _REPO / "compliance" / "etsi" / "G8-001_ELSA_REQUIREMENTS_MATRIX.md"

_REQUIRED_REQ_KEYS = {
    "id",
    "source",
    "section",
    "summary",
    "profile_field",
    "mechanisms",
    "code_plugin",
    "test",
    "status",
}

_FOCUS_VALUES = {"network_centric", "availability"}


def _load_matrix() -> dict:
    payload = yaml.safe_load(_MATRIX_YAML.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_matrix_files_exist() -> None:
    assert _MATRIX_YAML.is_file()
    assert _MATRIX_MD.is_file()
    md = _MATRIX_MD.read_text(encoding="utf-8")
    assert "G8-001" in md
    assert "ETSI_TS_103_652_1" in md
    assert "eu_elsa" in md
    assert "availability" in md.lower()
    assert "network" in md.lower()


def test_matrix_document_shape() -> None:
    doc = _load_matrix()
    assert doc["version"] == 1
    assert doc["matrix_id"] == "G8-001"
    assert doc["profile_id_target"] == "eu_elsa"
    assert doc["primary_instrument"]["id"] == "ETSI_TS_103_652_1"
    assert "10365201" in doc["primary_instrument"]["url"]
    assert isinstance(doc["requirements"], list)
    assert len(doc["requirements"]) >= 20


def test_requirement_rows_complete_and_unique() -> None:
    doc = _load_matrix()
    source_ids = {item["id"] for item in doc["sources"]}
    allowed = set(doc["allowed_statuses"])
    seen: set[str] = set()
    for row in doc["requirements"]:
        assert _REQUIRED_REQ_KEYS <= set(row)
        rid = row["id"]
        assert rid.startswith("ELSA-")
        assert rid not in seen
        seen.add(rid)
        assert row["source"] in source_ids
        assert row["status"] in allowed
        assert isinstance(row["section"], str) and row["section"].strip()
        assert isinstance(row["summary"], str) and len(row["summary"]) > 10
        assert isinstance(row["mechanisms"], list)
        assert row.get("focus") in _FOCUS_VALUES


def test_mechanisms_are_builtin_catalog_ids() -> None:
    catalog = builtin_mechanism_registry().ids()
    doc = _load_matrix()
    for row in doc["requirements"]:
        for mid in row["mechanisms"]:
            assert mid in catalog, f"{row['id']}: unknown mechanism {mid!r}"
        for mid in row.get("forbid_mechanisms_as_keepalive") or ():
            assert mid in catalog
        for mid in row.get("forbid_mechanisms_for_semantics") or ():
            assert mid in catalog


def test_deferred_availability_constraint_not_yet_in_catalog() -> None:
    """G8-003 owns registration; matrix may only name it under deferred_mechanisms."""
    catalog = builtin_mechanism_registry().ids()
    assert "availability_constraint" not in catalog
    doc = _load_matrix()
    deferred_hits = 0
    for row in doc["requirements"]:
        deferred = row.get("deferred_mechanisms") or []
        assert "availability_constraint" not in row["mechanisms"]
        if "availability_constraint" in deferred:
            deferred_hits += 1
    assert deferred_hits >= 5


def test_data_capabilities_are_canonical() -> None:
    doc = _load_matrix()
    for row in doc["requirements"]:
        for cap in row.get("data_capabilities") or ():
            assert cap in DATA_CAPABILITIES, f"{row['id']}: bad capability {cap!r}"


def test_markdown_lists_every_requirement_id() -> None:
    doc = _load_matrix()
    md = _MATRIX_MD.read_text(encoding="utf-8")
    for row in doc["requirements"]:
        assert row["id"] in md, row["id"]


def test_planned_yaml_rows_map_to_mechanisms_or_explicit_rules() -> None:
    doc = _load_matrix()
    for row in doc["requirements"]:
        if row["status"] != "PLANNED_YAML":
            continue
        has_mech = bool(row["mechanisms"])
        has_omit = bool(row.get("omit_profile_sections"))
        has_forbid_ka = bool(row.get("forbid_mechanisms_as_keepalive"))
        has_forbid_model = bool(row.get("forbid_modeling"))
        has_forbid_nouns = bool(row.get("forbid_domain_nouns"))
        has_explicit = bool(row.get("explicit_profile_fields"))
        assert (
            has_mech
            or has_omit
            or has_forbid_ka
            or has_forbid_model
            or has_forbid_nouns
            or has_explicit
        ), row["id"]


def test_focus_coverage_indexes_match_rows() -> None:
    doc = _load_matrix()
    by_id = {row["id"]: row for row in doc["requirements"]}
    coverage = doc["focus_coverage"]
    for rid in coverage["network_centric_requirement_ids"]:
        assert by_id[rid]["focus"] == "network_centric", rid
    for rid in coverage["availability_requirement_ids"]:
        assert by_id[rid]["focus"] == "availability", rid
    assert len(coverage["network_centric_requirement_ids"]) >= 8
    assert len(coverage["availability_requirement_ids"]) >= 12


def test_g0_hypothesis_updates_present() -> None:
    doc = _load_matrix()
    updates = doc.get("g0_hypothesis_updates") or []
    assert any(u.get("by") == "ELSA-007" and u.get("verdict") == "confirmed" for u in updates)
    assert any(u.get("by") == "ELSA-018" and u.get("verdict") == "rejected" for u in updates)
    assert any(u.get("by") == "ELSA-001" and u.get("verdict") == "rejected" for u in updates)


def test_no_cbrs_grant_vocabulary_in_planned_core_mapping() -> None:
    """Planned YAML rows must not prescribe Grant/CBSD as profile mechanisms."""
    doc = _load_matrix()
    for row in doc["requirements"]:
        if row["status"] != "PLANNED_YAML":
            continue
        field = (row.get("profile_field") or "").lower()
        assert "cbsd" not in field, row["id"]
        # Allow explicit forbid lists naming Grant/CBSD.
        if "grant" in field and "without grant" not in field:
            assert False, row["id"]
