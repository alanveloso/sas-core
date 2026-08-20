"""G9-005: Ofcom AFC 6 GHz fit-audit matrix integrity (query_assignment gap)."""

from __future__ import annotations

from pathlib import Path

import yaml

from primitives.registry import builtin_mechanism_registry
from providers.contract import DATA_CAPABILITIES

_REPO = Path(__file__).resolve().parents[2]
_MATRIX_YAML = _REPO / "compliance" / "ofcom" / "afc_6ghz_fit_audit.yaml"
_MATRIX_MD = _REPO / "compliance" / "ofcom" / "G9-005_AFC_6GHZ_FIT_AUDIT.md"

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
    "fit_verdict",
}

_STATUS_TO_SUMMARY = {
    "FIT_EXISTING": "fit_existing",
    "FIT_PARTIAL": "fit_partial",
    "GAP_PRIMITIVE": "gap_primitive",
    "GAP_DATA": "gap_data",
    "GAP_ADAPTER": "gap_adapter",
    "PROCESS": "process",
    "OUT_OF_SCOPE": "out_of_scope",
    "MATRIX_TEST": "matrix_test",
}


def _load_matrix() -> dict:
    payload = yaml.safe_load(_MATRIX_YAML.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_audit_files_exist() -> None:
    assert _MATRIX_YAML.is_file()
    assert _MATRIX_MD.is_file()
    md = _MATRIX_MD.read_text(encoding="utf-8")
    assert "G9-005" in md
    assert "afc_6ghz" in md
    assert "query_assignment" in md
    assert "not created" in md.lower() or "not registered" in md.lower()


def test_matrix_document_shape() -> None:
    doc = _load_matrix()
    assert doc["version"] == 1
    assert doc["matrix_id"] == "G9-005"
    assert doc["challenge_id"] == "afc_6ghz"
    assert doc["profile_id_target"] is None
    assert doc["audit_mode"] == "fit_gap_only"
    assert doc["implement_profile_in_this_task"] is False
    assert doc["implement_query_assignment_in_this_task"] is False
    assert doc["core_redesign_required"] is False
    assert doc["primary_instrument"]["id"] == "OFCOM_AFC_FRAMEWORK"
    assert "ofcom.org.uk" in doc["primary_instrument"]["url"]
    assert isinstance(doc["requirements"], list)
    assert len(doc["requirements"]) >= 20


def test_requirement_rows_complete_and_unique() -> None:
    doc = _load_matrix()
    source_ids = {item["id"] for item in doc["sources"]}
    allowed_status = set(doc["allowed_statuses"])
    allowed_fit = set(doc["allowed_fit_verdicts"])
    seen: set[str] = set()
    for row in doc["requirements"]:
        assert _REQUIRED_REQ_KEYS <= set(row)
        rid = row["id"]
        assert rid.startswith("AFC-")
        assert rid not in seen
        seen.add(rid)
        assert row["source"] in source_ids
        assert row["status"] in allowed_status
        assert row["fit_verdict"] in allowed_fit
        assert isinstance(row["section"], str) and row["section"].strip()
        assert isinstance(row["summary"], str) and len(row["summary"]) > 10
        assert isinstance(row["mechanisms"], list)


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
        for mid in row.get("deferred_mechanisms") or ():
            assert isinstance(mid, str) and mid.strip()


def test_query_assignment_deferred_and_unregistered() -> None:
    catalog = builtin_mechanism_registry().ids()
    assert "query_assignment" not in catalog
    doc = _load_matrix()
    cited = 0
    for row in doc["requirements"]:
        assert "query_assignment" not in row["mechanisms"]
        if "query_assignment" in (row.get("deferred_mechanisms") or ()):
            cited += 1
    assert cited >= 4
    assert doc["fit_summary"]["gap_primitive"] >= 1
    assert doc["fit_summary"]["overall_challenge_verdict"] == "GAP"


def test_availability_constraint_not_overloaded_as_afc_query() -> None:
    catalog = builtin_mechanism_registry().ids()
    assert "availability_constraint" in catalog
    doc = _load_matrix()
    row = next(r for r in doc["requirements"] if r["id"] == "AFC-005")
    assert "availability_constraint" in row["mechanisms"]
    assert "query_assignment" in (row.get("deferred_mechanisms") or ())
    assert row["status"] == "FIT_PARTIAL"


def test_no_afc_profile_yaml_shipped() -> None:
    profile = _REPO / "spectrum_profiles" / "profiles" / "v2" / "afc_6ghz.yaml"
    assert not profile.exists()


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


def test_fit_summary_matches_row_statuses() -> None:
    doc = _load_matrix()
    summary = doc["fit_summary"]
    counts = {key: 0 for key in _STATUS_TO_SUMMARY.values()}
    for row in doc["requirements"]:
        counts[_STATUS_TO_SUMMARY[row["status"]]] += 1
    for status, key in _STATUS_TO_SUMMARY.items():
        assert summary[key] == counts[key], f"{status}: summary {summary[key]} != {counts[key]}"
    assert summary["overall_challenge_verdict"] in set(doc["allowed_fit_verdicts"])
    assert sum(counts.values()) == len(doc["requirements"])


def test_forbid_grant_cbsd_as_universal() -> None:
    doc = _load_matrix()
    forbid_rows = [
        row for row in doc["requirements"] if row.get("forbid_domain_nouns")
    ]
    assert any("Grant" in row["forbid_domain_nouns"] for row in forbid_rows)
    assert any("CBSD" in row["forbid_domain_nouns"] for row in forbid_rows)


def test_cross_challenge_cites_g9_001() -> None:
    doc = _load_matrix()
    row = next(r for r in doc["requirements"] if r["id"] == "AFC-018")
    assert row["source"] == "G9_001_UK_SA"
    assert "query_assignment" in (row.get("deferred_mechanisms") or ())
    assert row["status"] == "FIT_EXISTING"
