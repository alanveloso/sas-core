"""G9-003: EU WBB-LMP fit-audit matrix integrity (gaps only)."""

from __future__ import annotations

from pathlib import Path

import yaml

from primitives.registry import builtin_mechanism_registry
from providers.contract import DATA_CAPABILITIES

_REPO = Path(__file__).resolve().parents[2]
_MATRIX_YAML = _REPO / "compliance" / "eu" / "eu_wbb_lmp_3800_fit_audit.yaml"
_MATRIX_MD = _REPO / "compliance" / "eu" / "G9-003_EU_WBB_LMP_FIT_AUDIT.md"

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
    assert "G9-003" in md
    assert "eu_wbb_lmp_3800" in md
    assert "2025/2425" in md or "2425" in md
    assert "low" in md.lower() and "medium" in md.lower()
    assert "not created" in md.lower() or "profile_id_target: null" in md.lower()


def test_matrix_document_shape() -> None:
    doc = _load_matrix()
    assert doc["version"] == 1
    assert doc["matrix_id"] == "G9-003"
    assert doc["challenge_id"] == "eu_wbb_lmp_3800"
    assert doc["profile_id_target"] is None
    assert doc["audit_mode"] == "fit_gap_only"
    assert doc["implement_profile_in_this_task"] is False
    assert doc["core_redesign_required"] is False
    assert doc["primary_instrument"]["id"] == "EU_2025_2425"
    assert "eur-lex.europa.eu" in doc["primary_instrument"]["url"]
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
        assert rid.startswith("EU-WBB-")
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


def test_lp_mp_power_rows_cite_rule_table() -> None:
    doc = _load_matrix()
    lp = next(row for row in doc["requirements"] if row["id"] == "EU-WBB-004")
    mp = next(row for row in doc["requirements"] if row["id"] == "EU-WBB-005")
    assert lp["status"] == "FIT_EXISTING"
    assert mp["status"] == "FIT_EXISTING"
    assert "rule_table" in lp["mechanisms"] and "max_power" in lp["mechanisms"]
    assert "rule_table" in mp["mechanisms"] and "max_power" in mp["mechanisms"]


def test_same_band_not_collapsed_with_uk_or_elsa() -> None:
    doc = _load_matrix()
    row = next(r for r in doc["requirements"] if r["id"] == "EU-WBB-018")
    assert row["status"] == "FIT_EXISTING"
    blob = (row["summary"] + " " + (row.get("notes") or "") + " " + (row["profile_field"] or "")).lower()
    assert "uk_shared_access" in blob or "ofcom" in blob or "uk" in blob
    assert "eu_elsa" in blob or "elsa" in blob


def test_no_eu_profile_yaml_shipped_by_this_task() -> None:
    profile = _REPO / "spectrum_profiles" / "profiles" / "v2" / "eu_wbb_lmp_3800.yaml"
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


def test_static_authorization_cited_without_grant_as_universal() -> None:
    doc = _load_matrix()
    static_rows = [
        row for row in doc["requirements"] if "static_authorization" in row["mechanisms"]
    ]
    assert static_rows
    forbid_rows = [
        row for row in doc["requirements"] if row.get("forbid_domain_nouns")
    ]
    assert any("Grant" in row["forbid_domain_nouns"] for row in forbid_rows)
    assert any("CBSD" in row["forbid_domain_nouns"] for row in forbid_rows)


def test_gap_primitive_count_is_zero() -> None:
    doc = _load_matrix()
    assert doc["fit_summary"]["gap_primitive"] == 0
    assert not any(row["status"] == "GAP_PRIMITIVE" for row in doc["requirements"])


def test_protection_coexistence_rows_present() -> None:
    doc = _load_matrix()
    by_id = {row["id"]: row for row in doc["requirements"]}
    assert by_id["EU-WBB-010"]["status"] == "GAP_DATA"  # FSS
    assert by_id["EU-WBB-011"]["status"] == "GAP_DATA"  # FS
    assert by_id["EU-WBB-013"]["status"] == "GAP_DATA"  # altimeters
    assert by_id["EU-WBB-015"]["status"] == "PROCESS"  # peer coexistence
    forbid = set(by_id["EU-WBB-015"].get("forbid_mechanisms_for_semantics") or ())
    assert "ordered_classes" in forbid and "preemption" in forbid
