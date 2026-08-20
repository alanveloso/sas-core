"""G11-004 — verify release-gate evidence package (claims limited to evidence).

Does not run the WInnForum official harness and never invents PASS_OFFICIAL.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[1]
_MATRIX = _REPO / "compliance" / "generalization" / "g11_004_release_gate.yaml"
_MD = _REPO / "compliance" / "generalization" / "G11-004_RELEASE_GATE.md"


def _load_matrix() -> dict:
    payload = yaml.safe_load(_MATRIX.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("g11_004_release_gate.yaml must be a mapping")
    return payload


def current_uut_head() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=_REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def verify(matrix: dict | None = None) -> list[str]:
    """Return human-readable OK lines; raise SystemExit on failure."""
    doc = matrix or _load_matrix()
    errors: list[str] = []
    oks: list[str] = []

    if not _MATRIX.is_file():
        errors.append(f"missing {_MATRIX}")
    if not _MD.is_file():
        errors.append(f"missing {_MD}")

    if doc.get("matrix_id") != "G11-004":
        errors.append("matrix_id must be G11-004")

    official = doc.get("official_harness") or {}
    if official.get("pass_official_claim_supported_by_this_package") is not False:
        errors.append("pass_official_claim_supported_by_this_package must be false")
    if official.get("g5_009_pass_official_claim_supported") is not False:
        errors.append("g5_009_pass_official_claim_supported must be false")

    forbidden = set(doc.get("claims_forbidden") or [])
    if "PASS_OFFICIAL" not in forbidden:
        errors.append("claims_forbidden must include PASS_OFFICIAL")

    md_text = _MD.read_text(encoding="utf-8") if _MD.is_file() else ""
    if "PASS_OFFICIAL" not in md_text:
        errors.append("release MD must mention PASS_OFFICIAL")
    if "NÃO" not in md_text:
        errors.append("release MD must explicitly deny PASS_OFFICIAL (NÃO)")
    if "/run-winnforum-gate G11-005" not in md_text:
        errors.append("release MD must point to /run-winnforum-gate G11-005")
    if "CONDITIONAL" not in md_text:
        errors.append("release MD must retain TVWS CONDITIONAL as evidence")
    for row in doc.get("local_evidence_inventory") or []:
        path = _REPO / str(row["path"])
        if not path.is_file():
            errors.append(f"missing evidence: {row['path']}")
        else:
            oks.append(f"evidence ok: {row['path']}")

    for rel in doc.get("local_gate_tests") or []:
        path = _REPO / str(rel)
        if not path.is_file():
            errors.append(f"missing local gate test: {rel}")
        else:
            oks.append(f"test ok: {rel}")

    for profile_id in (doc.get("uut") or {}).get("profile_v2_ids") or []:
        path = _REPO / "spectrum_profiles" / "profiles" / "v2" / f"{profile_id}.yaml"
        if not path.is_file():
            errors.append(f"missing profile v2: {profile_id}")
        else:
            oks.append(f"profile ok: {profile_id}")

    arch = doc.get("architecture_invariants") or {}
    if arch.get("core_country_profile_branches") is not False:
        errors.append("architecture_invariants.core_country_profile_branches must be false")
    if arch.get("yaml_dsl_introduced") is not False:
        errors.append("architecture_invariants.yaml_dsl_introduced must be false")
    if arch.get("query_assignment_registered") is not False:
        errors.append("architecture_invariants.query_assignment_registered must be false")
    if arch.get("tvws_holdout_verdict") != "CONDITIONAL":
        errors.append("tvws_holdout_verdict must remain CONDITIONAL")

    holdout = _REPO / "compliance" / "fcc" / "g10_002_holdout_verdict.yaml"
    if holdout.is_file():
        hv = yaml.safe_load(holdout.read_text(encoding="utf-8"))
        if isinstance(hv, dict) and hv.get("verdict") != "CONDITIONAL":
            errors.append("g10_002 holdout verdict must stay CONDITIONAL")

    g5 = _REPO / str(official.get("g5_009_evidence") or "")
    if g5.is_file():
        g5_text = g5.read_text(encoding="utf-8")
        if "PASS_OFFICIAL CLAIM SUPPORTED:** **NO**" not in g5_text and (
            "PASS_OFFICIAL CLAIM SUPPORTED:** **YES**" in g5_text
        ):
            errors.append("G5-009 evidence must not claim PASS_OFFICIAL YES")
        oks.append("G5-009 evidence present; PASS_OFFICIAL not YES")

    head = current_uut_head()
    oks.append(f"current HEAD: {head}")
    authoring = (doc.get("uut") or {}).get("package_authoring_head")
    if authoring:
        oks.append(f"package_authoring_head: {authoring}")

    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        raise SystemExit(1)
    return oks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.g11_004_release_gate",
        description="Verify G11-004 release evidence package (no PASS_OFFICIAL).",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Validate inventory, invariants, and claim limits",
    )
    parser.add_argument(
        "--print-head",
        action="store_true",
        help="Print current git HEAD (UUT SHA)",
    )
    args = parser.parse_args(argv)

    if args.print_head:
        print(current_uut_head())
        return 0

    if not args.verify:
        parser.print_help()
        return 2

    for line in verify():
        print(f"OK: {line}")
    print("G11-004 release gate verify: PASS")
    print("PASS_OFFICIAL: NOT SUPPORTED by this package")
    print("Next official campaign: /run-winnforum-gate G11-005")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
