"""P8-005 certification-package layout and honesty checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.p8_005_certification_package import (
    REQUIRED_DIRS,
    REQUIRED_FILES,
    build_package,
    validate_package,
)

_ROOT = Path(__file__).resolve().parents[2]


def test_build_package_creates_required_layout(tmp_path: Path):
    out = tmp_path / "certification-package"
    meta = build_package(outdir=out, root=_ROOT)
    assert meta["required_files_ok"] is True
    assert meta["required_dirs_ok"] is True
    errs = validate_package(out, root=_ROOT)
    assert errs == []
    for rel in REQUIRED_FILES:
        assert (out / rel).is_file()
    for rel in REQUIRED_DIRS:
        assert (out / rel).is_dir()
    assert (out / "dependency-locks" / "requirements.lock.txt").is_file()
    assert (out / "profiles" / "cbrs_winnforum.yaml").is_file()
    assert (out / "compliance-matrix.NOTES.md").is_file()
    notes = (out / "compliance-matrix.NOTES.md").read_text(encoding="utf-8")
    assert "PASS_OFFICIAL" in notes
    assert "does **not** create new" in notes or "does not create new" in notes.lower()
    manifest = json.loads((out / "datasets-manifest.json").read_text(encoding="utf-8"))
    assert manifest["spectrum_profile"] == "cbrs_winnforum"
    deviations = (out / "known-deviations.md").read_text(encoding="utf-8")
    assert "PASS_OFFICIAL" in deviations  # discussed as non-claim
    assert "not" in deviations.lower()
    assert "Rel1Ext" in deviations or "REL1EXT" in deviations.upper()


def test_validate_detects_missing_file(tmp_path: Path):
    out = tmp_path / "pkg"
    build_package(outdir=out, root=_ROOT)
    (out / "security-review.md").unlink()
    errs = validate_package(out, root=_ROOT)
    assert any("security-review.md" in e for e in errs)


def test_repo_certification_package_if_present():
    """When a package matching HEAD exists, it must validate; stale preview is skipped."""
    pkg = _ROOT / "certification-package"
    if not pkg.is_dir():
        pytest.skip("certification-package not generated yet")
    uut_path = pkg / "uut-commit.txt"
    if uut_path.is_file():
        import subprocess

        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=_ROOT, text=True
        ).strip()
        uut = uut_path.read_text(encoding="utf-8").strip()
        if uut != head:
            pytest.skip(
                "certification-package is PREVIEW/STALE (uut-commit != HEAD); "
                "rebuild after P8-004 for FINAL"
            )
    errs = validate_package(pkg, root=_ROOT)
    assert errs == [], errs
