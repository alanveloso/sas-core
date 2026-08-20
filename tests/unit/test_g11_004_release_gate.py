"""G11-004: release gate package — reproducible local release, limited claims."""

from __future__ import annotations

from pathlib import Path

import yaml

from tools.g11_004_release_gate import _load_matrix, current_uut_head, verify

_REPO = Path(__file__).resolve().parents[2]
_MATRIX = _REPO / "compliance" / "generalization" / "g11_004_release_gate.yaml"
_MD = _REPO / "compliance" / "generalization" / "G11-004_RELEASE_GATE.md"


def test_release_package_files_exist() -> None:
    assert _MATRIX.is_file()
    assert _MD.is_file()
    assert (_REPO / "tools" / "g11_004_release_gate.py").is_file()


def test_verify_passes_and_denies_pass_official() -> None:
    lines = verify()
    assert any("current HEAD:" in line for line in lines)
    doc = _load_matrix()
    assert doc["official_harness"]["pass_official_claim_supported_by_this_package"] is False
    assert "PASS_OFFICIAL" in doc["claims_forbidden"]
    md = _MD.read_text(encoding="utf-8")
    assert "PASS_OFFICIAL" in md
    assert "NÃO" in md
    assert "/run-winnforum-gate G11-005" in md
    assert "CONDITIONAL" in md


def test_holdout_conditional_not_rewritten() -> None:
    doc = _load_matrix()
    assert doc["architecture_invariants"]["tvws_holdout_verdict"] == "CONDITIONAL"
    holdout = yaml.safe_load(
        (_REPO / "compliance" / "fcc" / "g10_002_holdout_verdict.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert holdout["verdict"] == "CONDITIONAL"


def test_inventory_and_local_gates_present() -> None:
    doc = _load_matrix()
    for row in doc["local_evidence_inventory"]:
        assert (_REPO / row["path"]).is_file(), row["path"]
    for rel in doc["local_gate_tests"]:
        assert (_REPO / rel).is_file(), rel


def test_uut_head_readable() -> None:
    head = current_uut_head()
    assert len(head) == 40
    assert all(c in "0123456789abcdef" for c in head)
