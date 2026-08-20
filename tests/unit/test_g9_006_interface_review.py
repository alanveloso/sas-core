"""G9-006: challenge-set interface review integrity (≥2-regime gate)."""

from __future__ import annotations

from pathlib import Path

import yaml

from primitives.registry import builtin_mechanism_registry

_REPO = Path(__file__).resolve().parents[2]
_REVIEW_YAML = _REPO / "compliance" / "generalization" / "g9_006_interface_review.yaml"
_REVIEW_MD = _REPO / "compliance" / "generalization" / "G9-006_INTERFACE_REVIEW.md"

_REQUIRED_DECISION_KEYS = {
    "id",
    "topic",
    "decision",
    "justifying_regimes",
    "regime_count",
    "gate_satisfied",
    "implement_now",
    "notes",
}

_DECISION_TO_SUMMARY = {
    "OPEN_FOR_LATER_DESIGN": "open_for_later_design",
    "REJECT": "reject",
    "DEFER_NO_CORE": "defer_no_core",
    "CONFIRM_INVARIANT": "confirm_invariant",
}


def _load() -> dict:
    payload = yaml.safe_load(_REVIEW_YAML.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_review_files_exist() -> None:
    assert _REVIEW_YAML.is_file()
    assert _REVIEW_MD.is_file()
    md = _REVIEW_MD.read_text(encoding="utf-8")
    assert "G9-006" in md
    assert "query_assignment" in md
    assert "OPEN_FOR_LATER_DESIGN" in md
    assert "IF-001" in md


def test_document_shape() -> None:
    doc = _load()
    assert doc["version"] == 1
    assert doc["matrix_id"] == "G9-006"
    assert doc["review_mode"] == "interface_gate_only"
    assert doc["implement_changes_in_this_task"] is False
    assert doc["register_query_assignment_in_this_task"] is False
    assert doc["core_files_modified"] is False
    assert len(doc["challenge_evidence"]) == 5
    assert len(doc["decisions"]) >= 8


def test_challenge_evidence_matrices_exist_and_match_flags() -> None:
    doc = _load()
    for item in doc["challenge_evidence"]:
        path = _REPO / item["matrix"]
        assert path.is_file(), item["matrix"]
        matrix = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert matrix["challenge_id"] == item["challenge_id"]
        assert matrix["core_redesign_required"] is False
        assert matrix["fit_summary"]["overall_challenge_verdict"] == item[
            "overall_challenge_verdict"
        ]
        cited = False
        for row in matrix["requirements"]:
            if "query_assignment" in (row.get("deferred_mechanisms") or ()):
                cited = True
                break
            if "query_assignment" in (row.get("mechanisms") or ()):
                cited = True
                break
        assert cited is item["cites_query_assignment"], item["challenge_id"]


def test_decisions_complete_and_unique() -> None:
    doc = _load()
    allowed = set(doc["allowed_decisions"])
    seen: set[str] = set()
    for row in doc["decisions"]:
        assert _REQUIRED_DECISION_KEYS <= set(row)
        assert row["id"] not in seen
        seen.add(row["id"])
        assert row["id"].startswith("IF-")
        assert row["decision"] in allowed
        assert isinstance(row["justifying_regimes"], list)
        assert row["regime_count"] == len(row["justifying_regimes"])
        assert isinstance(row["implement_now"], bool)
        assert row["implement_now"] is False


def test_open_decisions_require_ge_2_regimes_or_boundary() -> None:
    doc = _load()
    for row in doc["decisions"]:
        if row["decision"] != "OPEN_FOR_LATER_DESIGN":
            continue
        assert row["gate_satisfied"] is True
        assert row["regime_count"] >= 2
        assert row.get("pre_existing_boundary")


def test_query_assignment_opened_but_not_registered() -> None:
    catalog = builtin_mechanism_registry().ids()
    assert "query_assignment" not in catalog
    doc = _load()
    if001 = next(r for r in doc["decisions"] if r["id"] == "IF-001")
    assert if001["topic"] == "query_assignment"
    assert if001["decision"] == "OPEN_FOR_LATER_DESIGN"
    assert if001["implement_now"] is False
    ids = {r["challenge_id"] for r in if001["justifying_regimes"]}
    assert "afc_6ghz" in ids
    assert "uk_shared_access" in ids
    assert doc["summary"]["query_assignment_gate"] == "OPEN_FOR_LATER_DESIGN"
    assert doc["summary"]["isolated_case_redesign_avoided"] is True


def test_reject_grant_siq_overload_and_bandprofile() -> None:
    doc = _load()
    by_id = {r["id"]: r for r in doc["decisions"]}
    assert by_id["IF-002"]["decision"] == "REJECT"
    assert by_id["IF-003"]["decision"] == "REJECT"
    assert by_id["IF-004"]["decision"] == "REJECT"
    assert by_id["IF-006"]["decision"] == "REJECT"


def test_same_band_invariant_confirmed() -> None:
    doc = _load()
    row = next(r for r in doc["decisions"] if r["id"] == "IF-005")
    assert row["decision"] == "CONFIRM_INVARIANT"
    ids = {r["challenge_id"] for r in row["justifying_regimes"]}
    assert "de_bnetza_local_3700" in ids
    assert "eu_wbb_lmp_3800" in ids


def test_summary_matches_decision_counts() -> None:
    doc = _load()
    summary = doc["summary"]
    counts = {key: 0 for key in _DECISION_TO_SUMMARY.values()}
    for row in doc["decisions"]:
        counts[_DECISION_TO_SUMMARY[row["decision"]]] += 1
    for decision, key in _DECISION_TO_SUMMARY.items():
        assert summary[key] == counts[key], f"{decision}: {summary[key]} != {counts[key]}"
    assert summary["next_candidate_phase_task"] == "G10-001"
    assert summary["phase_g9_challenge_fit_complete"] is True


def test_markdown_lists_every_decision_id() -> None:
    doc = _load()
    md = _REVIEW_MD.read_text(encoding="utf-8")
    for row in doc["decisions"]:
        assert row["id"] in md, row["id"]
