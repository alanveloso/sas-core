"""G10-003: quantitative generalization metrics; retain CONDITIONAL as evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from primitives.registry import builtin_mechanism_registry

_REPO = Path(__file__).resolve().parents[2]
_REPORT_YAML = _REPO / "compliance" / "generalization" / "g10_003_quantitative_report.yaml"
_REPORT_MD = _REPO / "compliance" / "generalization" / "G10-003_QUANTITATIVE_GENERALIZATION_REPORT.md"
_HOLDOUT_VERDICT = _REPO / "compliance" / "fcc" / "g10_002_holdout_verdict.yaml"


def _content_loc(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    n = 0
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if path.suffix in {".yaml", ".yml"} and s.startswith("#"):
            continue
        n += 1
    return n


def _collect_mechanisms(obj: Any, out: set[str]) -> None:
    if isinstance(obj, dict):
        mechanism = obj.get("mechanism")
        if isinstance(mechanism, str):
            out.add(mechanism)
        mechanisms = obj.get("mechanisms")
        if isinstance(mechanisms, list):
            for item in mechanisms:
                if isinstance(item, str):
                    out.add(item)
        for value in obj.values():
            _collect_mechanisms(value, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_mechanisms(item, out)


def _load_report() -> dict[str, Any]:
    payload = yaml.safe_load(_REPORT_YAML.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_report_files_exist() -> None:
    assert _REPORT_YAML.is_file()
    assert _REPORT_MD.is_file()
    md = _REPORT_MD.read_text(encoding="utf-8")
    assert "G10-003" in md
    assert "CONDITIONAL" in md
    assert "evidência" in md.lower() or "evidence" in md.lower() or "retido" in md.lower()


def test_holdout_conditional_retained_not_rewritten() -> None:
    report = _load_report()
    holdout = yaml.safe_load(_HOLDOUT_VERDICT.read_text(encoding="utf-8"))
    assert holdout["verdict"] == "CONDITIONAL"
    assert report["architecture_targets"]["query_assignment_registered"] is False
    assert report["summary_assessment"]["holdout_conditional_retained_as_evidence"] is True
    assert report["methodology"]["conditional_policy"]

    tvws = next(p for p in report["profiles"] if p["profile_id"] == "us_tvws_15_711")
    assert tvws["representation_verdict"] == "CONDITIONAL"
    assert tvws["treat_conditional_as_defect"] is False
    assert report["totals_profiles_v2"]["holdout_conditional_count"] == 1

    evidence_rows = report["challenge_and_holdout_evidence"]
    g10_002 = next(r for r in evidence_rows if r["task"] == "G10-002")
    assert g10_002["overall_verdict"] == "CONDITIONAL"


def test_profile_metrics_match_recomputed_values() -> None:
    report = _load_report()
    registry = set(builtin_mechanism_registry().ids())
    assert report["registry"]["builtin_mechanism_count"] == len(registry)
    assert report["registry"]["query_assignment_in_registry"] is False
    assert "query_assignment" not in registry

    for row in report["profiles"]:
        path = _REPO / row["profile_path"]
        assert path.is_file()
        assert _content_loc(path) == row["yaml_loc"]
        assert row["profile_specific_python_loc"] == 0
        assert row["core_files_modified_for_profile_yaml"] == 0
        assert row["rf_port_changes_for_this_profile"] == 0
        assert row["mechanism_reuse_pct"] == 100.0

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        mechs: set[str] = set()
        _collect_mechanisms(raw, mechs)
        assert len(mechs) == row["mechanism_count"]
        assert mechs <= registry

        tests_loc = 0
        for rel in row["test_files"]:
            tpath = _REPO / rel
            assert tpath.is_file(), rel
            tests_loc += _content_loc(tpath)
        assert tests_loc == row["tests_loc"]


def test_totals_and_no_profile_python_under_profiles_tree() -> None:
    report = _load_report()
    totals = report["totals_profiles_v2"]
    profiles = report["profiles"]
    assert totals["profile_count"] == len(profiles)
    assert totals["yaml_loc_sum"] == sum(p["yaml_loc"] for p in profiles)
    assert totals["tests_loc_sum"] == sum(p["tests_loc"] for p in profiles)
    assert totals["profile_specific_python_loc_sum"] == 0
    assert totals["core_files_modified_for_profile_yaml_sum"] == 0
    assert totals["profiles_with_100pct_mechanism_reuse"] == 4
    py_under_profiles = list((_REPO / "spectrum_profiles" / "profiles").rglob("*.py"))
    assert py_under_profiles == []


def test_challenge_evidence_includes_partial_gap_conditional() -> None:
    report = _load_report()
    by_task = {row["task"]: row["overall_verdict"] for row in report["challenge_and_holdout_evidence"]}
    assert by_task["G9-001"] == "PARTIAL"
    assert by_task["G9-005"] == "GAP"
    assert by_task["G10-002"] == "CONDITIONAL"
    assert "PASS" not in {by_task["G9-005"], by_task["G10-002"]}


def test_markdown_states_conditional_is_evidence() -> None:
    md = _REPORT_MD.read_text(encoding="utf-8")
    assert "CONDITIONAL" in md
    assert "query_assignment" in md
    assert "G11-001" in md
