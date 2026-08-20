"""G10-001: TVWS §15.711 holdout map integrity (no design contamination)."""

from __future__ import annotations

from pathlib import Path

import yaml

from primitives.registry import builtin_mechanism_registry
from providers.contract import DATA_CAPABILITIES

_REPO = Path(__file__).resolve().parents[2]
_MATRIX_YAML = _REPO / "compliance" / "fcc" / "tvws_15_711_holdout_map.yaml"
_MATRIX_MD = _REPO / "compliance" / "fcc" / "G10-001_TVWS_HOLDOUT_MAP.md"

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


def _load() -> dict:
    payload = yaml.safe_load(_MATRIX_YAML.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_holdout_files_exist() -> None:
    assert _MATRIX_YAML.is_file()
    assert _MATRIX_MD.is_file()
    md = _MATRIX_MD.read_text(encoding="utf-8")
    assert "G10-001" in md
    assert "15.711" in md or "§15.711" in md
    assert "contamination" in md.lower() or "contaminação" in md.lower()
    assert "us_tvws_15_711" in md


def test_document_shape() -> None:
    doc = _load()
    assert doc["version"] == 1
    assert doc["matrix_id"] == "G10-001"
    assert doc["challenge_id"] == "us_tvws_15_711"
    assert doc["holdout"] is True
    assert doc["profile_id_target"] is None
    assert doc["audit_mode"] == "holdout_map_only"
    assert doc["implement_profile_in_this_task"] is False
    assert doc["implement_query_assignment_in_this_task"] is False
    assert doc["core_redesign_required"] is False
    assert doc["design_contamination"] is False
    assert doc["primary_instrument"]["id"] == "CFR_47_15_711"
    assert "15.711" in doc["primary_instrument"]["url"]
    assert len(doc["requirements"]) >= 15


def test_requirement_rows_complete_and_unique() -> None:
    doc = _load()
    source_ids = {item["id"] for item in doc["sources"]}
    allowed_status = set(doc["allowed_statuses"])
    allowed_fit = set(doc["allowed_fit_verdicts"])
    seen: set[str] = set()
    for row in doc["requirements"]:
        assert _REQUIRED_REQ_KEYS <= set(row)
        rid = row["id"]
        assert rid.startswith("TVWS-")
        assert rid not in seen
        seen.add(rid)
        assert row["source"] in source_ids
        assert row["status"] in allowed_status
        assert row["fit_verdict"] in allowed_fit
        assert isinstance(row["mechanisms"], list)


def test_mechanisms_are_builtin_catalog_ids() -> None:
    catalog = builtin_mechanism_registry().ids()
    doc = _load()
    for row in doc["requirements"]:
        for mid in row["mechanisms"]:
            assert mid in catalog, f"{row['id']}: unknown mechanism {mid!r}"
        for mid in row.get("deferred_mechanisms") or ():
            assert isinstance(mid, str) and mid.strip()


def test_no_new_primitive_invented_from_holdout() -> None:
    catalog = builtin_mechanism_registry().ids()
    assert "query_assignment" not in catalog
    doc = _load()
    assert doc["contamination_summary"]["new_primitives_invented_from_holdout"] == 0
    assert doc["contamination_summary"]["design_contamination"] is False
    gap_prim = [r for r in doc["requirements"] if r["status"] == "GAP_PRIMITIVE"]
    assert len(gap_prim) == 1
    assert gap_prim[0]["id"] == "TVWS-002"
    assert "query_assignment" in (gap_prim[0].get("deferred_mechanisms") or ())


def test_query_assignment_not_registered_and_not_implemented() -> None:
    doc = _load()
    assert doc["implement_query_assignment_in_this_task"] is False
    for row in doc["requirements"]:
        assert "query_assignment" not in row["mechanisms"]


def test_no_tvws_profile_yaml() -> None:
    profile = _REPO / "spectrum_profiles" / "profiles" / "v2" / "us_tvws_15_711.yaml"
    assert not profile.exists()


def test_data_capabilities_are_canonical() -> None:
    doc = _load()
    for row in doc["requirements"]:
        for cap in row.get("data_capabilities") or ():
            assert cap in DATA_CAPABILITIES


def test_markdown_lists_every_requirement_id() -> None:
    doc = _load()
    md = _MATRIX_MD.read_text(encoding="utf-8")
    for row in doc["requirements"]:
        assert row["id"] in md, row["id"]


def test_fit_summary_matches_row_statuses() -> None:
    doc = _load()
    summary = doc["fit_summary"]
    counts = {key: 0 for key in _STATUS_TO_SUMMARY.values()}
    for row in doc["requirements"]:
        counts[_STATUS_TO_SUMMARY[row["status"]]] += 1
    for status, key in _STATUS_TO_SUMMARY.items():
        assert summary[key] == counts[key], f"{status}: {summary[key]} != {counts[key]}"
    assert summary["overall_holdout_verdict"] in set(doc["allowed_fit_verdicts"])


def test_forbid_grant_cbsd() -> None:
    doc = _load()
    forbid_rows = [r for r in doc["requirements"] if r.get("forbid_domain_nouns")]
    assert any("Grant" in r["forbid_domain_nouns"] for r in forbid_rows)
    assert any("CBSD" in r["forbid_domain_nouns"] for r in forbid_rows)


def test_distinct_from_afc_challenge() -> None:
    doc = _load()
    row = next(r for r in doc["requirements"] if r["id"] == "TVWS-017")
    blob = (row["summary"] + " " + (row["profile_field"] or "")).lower()
    assert "afc_6ghz" in blob or "afc" in blob
    assert row["status"] == "FIT_EXISTING"
