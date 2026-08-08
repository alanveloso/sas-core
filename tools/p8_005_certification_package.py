"""P8-005 — build the local certification evidence package.

Populates ``certification-package/`` from the repository HEAD, lockfiles,
profiles, compliance matrix, and optional P8-004 regression summary.

Does **not** invent WInnForum PASS / PASS_OFFICIAL claims.

Usage::

    .venv/bin/python -m tools.p8_005_certification_package \\
        --outdir certification-package
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "README.md",
    "target-specifications.md",
    "uut-commit.txt",
    "harness-commit.txt",
    "datasets-manifest.json",
    "compliance-matrix.yaml",
    "compliance-matrix.NOTES.md",
    "known-deviations.md",
    "security-review.md",
)

REQUIRED_DIRS = (
    "dependency-locks",
    "profiles",
    "configs",
    "results",
    "junit",
    "logs",
)


def _git_rev(path: Path, *, short: bool = False) -> str | None:
    if not path.exists():
        return None
    try:
        args = ["git", "rev-parse"]
        if short:
            args.append("--short")
        args.append("HEAD")
        out = subprocess.check_output(args, cwd=path, text=True)
        return out.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def build_datasets_manifest(root: Path) -> dict[str, object]:
    ned = (root / "data" / "geo" / "ned" / "VERSION").read_text(encoding="utf-8").strip()
    ntia = (root / "data" / "ntia" / "VERSION").read_text(encoding="utf-8").strip()
    protection = root / "protection_data" / "manifests" / "cbrs_winnforum_protection.yaml"
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "spectrum_profile": "cbrs_winnforum",
        "ned_version_file": ned,
        "ntia_version_file": ntia,
        "protection_manifest": str(protection.relative_to(root)),
        "notes": [
            "NED/NTIA payload tiles/KML may be absent locally (VERSION-only checkouts).",
            "Do not treat this manifest as evidence of official harness PASS.",
        ],
    }


def _latest_p8_004_summary(root: Path) -> Path | None:
    base = root / "artifacts" / "winnforum"
    if not base.is_dir():
        return None
    matches = sorted(base.glob("p8_004_regression_*/summary.json"))
    return matches[-1] if matches else None


def build_package(*, outdir: Path, root: Path = _ROOT) -> dict[str, object]:
    outdir = outdir if outdir.is_absolute() else root / outdir
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)

    uut = _git_rev(root) or "UNKNOWN"
    uut_short = _git_rev(root, short=True) or "UNKNOWN"
    harness_root = root.parent / "winnforum-sas-harness"
    harness = _git_rev(harness_root)
    harness_short = _git_rev(harness_root, short=True)
    if harness is None:
        harness = "NOT_AVAILABLE"
        harness_short = "NOT_AVAILABLE"
        harness_note = (
            "Sibling ../winnforum-sas-harness not found or not a git checkout. "
            "Historical evidence pins often cite 928c315 — verify before campaigns."
        )
    else:
        harness_note = f"Resolved from {harness_root}"

    _write(outdir / "uut-commit.txt", uut)
    _write(
        outdir / "harness-commit.txt",
        f"{harness}\n# short={harness_short}\n# {harness_note}\n",
    )

    # Locks
    for name in ("requirements.lock.txt", "requirements.txt", "requirements-dev.txt"):
        src = root / name
        if src.is_file():
            _copy_file(src, outdir / "dependency-locks" / name)

    # Profile
    profile = root / "spectrum_profiles" / "profiles" / "cbrs_winnforum.yaml"
    _copy_file(profile, outdir / "profiles" / "cbrs_winnforum.yaml")

    # Configs (no secrets)
    _copy_file(root / ".env.example", outdir / "configs" / "env.example")
    _write(
        outdir / "configs" / "execution-mode.md",
        """# Execution mode notes

- `SAS_EXECUTION_MODE=certification`: CPAS inline; rate limiting forced OFF.
- `SAS_EXECUTION_MODE=production`: Celery/RabbitMQ path for daily activities.
- Inject secrets via environment / secret manager — never commit real `.env`.
- App-layer CRL re-reads on disk; TLS handshake context needs process restart
  after cert/CRL replace (see `services/trust_reload.py`).
""",
    )

    # Matrix snapshot + honesty note (case-level passing rows need external evidence).
    _copy_file(root / "compliance" / "matrix.yaml", outdir / "compliance-matrix.yaml")
    _write(
        outdir / "compliance-matrix.NOTES.md",
        """# Compliance matrix snapshot — read before treating `passing` as proven

This file is a **byte copy** of `compliance/matrix.yaml` at package build time.

## Rules

1. **Family rollups** (`FAMILY.*`) must remain non-`passing` until official evidence
   policy says otherwise — see `DEV-MATRIX-ROLLUPS` in `known-deviations.md`.
2. Individual rows with `status: passing` are **historical case claims** that are
   only valid together with the `evidence:` path named in that row (often under
   `docs/compliance/evidence/` or `artifacts/winnforum/`, **not** fully bundled here).
3. Shipping this YAML inside `certification-package/` does **not** create new
   WInnForum PASS / PASS_OFFICIAL claims and does not replace harness JUnit.
4. Before citing any `passing` row in an audit, open the linked evidence artifact
   and confirm the harness command/output still matches the UUT commit in
   `uut-commit.txt`.
""",
    )
    if (root / "compliance" / "rel1ext_delta.yaml").is_file():
        _copy_file(
            root / "compliance" / "rel1ext_delta.yaml",
            outdir / "configs" / "rel1ext_delta.yaml",
        )

    # Datasets
    manifest = build_datasets_manifest(root)
    _write(
        outdir / "datasets-manifest.json",
        json.dumps(manifest, indent=2) + "\n",
    )

    # Results — latest P8-004 summary if present under artifacts/
    summary_src = _latest_p8_004_summary(root)
    results_note = outdir / "results" / "README.md"
    if summary_src is not None and summary_src.is_file():
        _copy_file(summary_src, outdir / "results" / "p8_004_regression_summary.json")
        _write(
            results_note,
            f"Local P8-004 regression summary copied from `{summary_src.relative_to(root)}` "
            "(gitignored source tree). Verdict is PASS_LOCAL only — not official harness PASS.\n",
        )
    else:
        _write(
            results_note,
            "No P8-004 summary found under artifacts/winnforum/p8_004_regression_*/. "
            "Run `python -m tools.p8_004_regression` then rebuild this package.\n",
        )

    _write(
        outdir / "junit" / "README.md",
        "Official harness JUnit XML is not bundled here. "
        "Place campaign outputs under artifacts/winnforum/ and reference them "
        "from evidence — do not invent PASS.\n",
    )
    _write(
        outdir / "logs" / "README.md",
        "Operational / harness logs are not copied into git. "
        "See gitignored `artifacts/winnforum/` for local runs.\n",
    )

    _write(
        outdir / "target-specifications.md",
        f"""# Target specifications

| Item | Value |
|------|-------|
| UUT commit | `{uut_short}` (`{uut}`) |
| Harness commit | `{harness_short}` (`{harness}`) |
| Spectrum profile | `cbrs_winnforum` |
| SAS-SAS version default | v1.3 (config) |
| Selected suites | Release 1 FT.S families + Rel1Ext delta (see matrix / rel1ext_delta) |

## Normative pointers (local docs)

- `docs/compliance/AUDITORIA_SAS_WINNFORUM_2026-08-05.md`
- `docs/compliance/PLANO_CURSOR_SAS_WINNFORUM.md`
- `docs/compliance/MATRIZ_SUITES_SAS_WINNFORUM.csv`
- `compliance/matrix.yaml` (snapshot in this package)

Official WInnForum TS documents remain external to this repository.
""",
    )

    _write(
        outdir / "known-deviations.md",
        f"""# Known deviations / ENV gaps

Generated for UUT `{uut_short}` — **not** an official waiver list.

| ID | Classification | Description |
|----|----------------|-------------|
| DEV-CERTS | ENV | `./certs` often absent locally; doctor FAIL; Compose api/worker mTLS not exercised |
| DEV-REL1EXT-HARNESS | HARNESS | Rel1Ext/TS-4010 suite files missing at common pin `928c315` |
| DEV-ITM | ENV | Official ITM / `reference_models` may be absent in UUT venv |
| DEV-PG-CONCURRENCY | ENV | `tests/integration/test_concurrency_postgres.py` skips without `SAS_TEST_DATABASE_URL` / `:55432` |
| DEV-COMPOSE-STACK | ENV | Full Docker Compose (api+worker+RabbitMQ+certs) not required for local pytest PASS_LOCAL |
| DEV-OCSP | TARGET | OCSP network validation disabled (`SAS_SSL_OCSP_MODE=disabled`); CRL PEM target |
| DEV-PEER-INJECT-HTTP | LEGACY | Invalid peer inject URL returns empty Admin 200 without persistence |
| DEV-MATRIX-ROLLUPS | EVIDENCE | Family rollups remain `failing` until official evidence is migrated — no invented `passing` |
| DEV-MATRIX-SNAPSHOT | EVIDENCE | `compliance-matrix.yaml` may contain historical case-level `passing` rows; see `compliance-matrix.NOTES.md` — not re-proven by this package alone |

## Non-claims

- This package does **not** assert WInnForum family PASS or PASS_OFFICIAL.
- Local pytest / P8-004 PASS_LOCAL is product hardening evidence only.
""",
    )

    _write(
        outdir / "security-review.md",
        f"""# Security review snapshot (P8-003)

UUT `{uut_short}`. Hardening delivered under Fase 8 / P8-003 (+ closure fixes):

| Control | Status |
|---------|--------|
| Canonical role OIDs | `services/winnf_role_oids.py` shared by mtls_auth + rbac |
| SSRF egress | `services/ssrf.py` (default fail-closed; lab paths opt-in) |
| Request body limits | ASGI incremental count + Content-Length early 413 |
| Rate limiting | Off in `SAS_EXECUTION_MODE=certification`; production keys from TLS peer cert (not spoofable headers) |
| Trust/CRL reload | Admin `/admin/security/trust_material` + reload |
| Secrets guidance | `.env.example` PRODUCTION SECRETS; empty DB_SYNC defaults |

## Residual risks

- Multi-worker in-process rate limit / metrics are not cluster-global.
- Body middleware retains at most `SAS_MAX_REQUEST_BODY_BYTES` for replay.
- Official mTLS campaigns still need provisioned `./certs`.

Evidence: `compliance/evidence/P8-003_security.md`.
""",
    )

    _write(
        outdir / "README.md",
        f"""# SAS Core — certification package (P8-005)

**Generated:** {datetime.now(timezone.utc).replace(microsecond=0).isoformat()}

**UUT:** `{uut_short}`

**Harness checkout:** `{harness_short}`

This directory is a **reproducible evidence bundle** for lab/certification prep.
It is **not** a claim that official WInnForum suites passed.

## Layout

See `docs/compliance/PLANO_CURSOR_SAS_WINNFORUM.md` task P8-005.

## Rebuild

```bash
.venv/bin/python -m tools.p8_005_certification_package --outdir certification-package
```

## Read first

1. `target-specifications.md`
2. `known-deviations.md`
3. `security-review.md`
4. `compliance-matrix.yaml` **with** `compliance-matrix.NOTES.md`
   (case-level `passing` rows need linked evidence outside this package)
5. `results/` (local regression summaries only)

## Gate note

Fase 8 product gate also requires P8-001…004 evidence and green local pytest.
Official Rel1Ext PASS×3 remains ENV/harness gated (see known-deviations).
""",
    )

    try:
        outdir_rel = str(outdir.relative_to(root))
    except ValueError:
        outdir_rel = str(outdir)

    return {
        "outdir": outdir_rel,
        "uut_commit": uut,
        "harness_commit": harness,
        "required_files_ok": all((outdir / p).is_file() for p in REQUIRED_FILES),
        "required_dirs_ok": all((outdir / p).is_dir() for p in REQUIRED_DIRS),
    }


def validate_package(outdir: Path, *, root: Path = _ROOT) -> list[str]:
    """Return a list of validation errors (empty = OK)."""
    outdir = outdir if outdir.is_absolute() else root / outdir
    errors: list[str] = []
    if not outdir.is_dir():
        return [f"missing package directory: {outdir}"]
    for rel in REQUIRED_FILES:
        if not (outdir / rel).is_file():
            errors.append(f"missing file: {rel}")
    for rel in REQUIRED_DIRS:
        if not (outdir / rel).is_dir():
            errors.append(f"missing dir: {rel}")
    locks = outdir / "dependency-locks" / "requirements.lock.txt"
    if not locks.is_file():
        errors.append("missing dependency-locks/requirements.lock.txt")
    # No invented unqualified "all families passing" claims.
    for name in ("known-deviations.md", "security-review.md", "README.md"):
        path = outdir / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if "all families passing" in text.lower():
            errors.append(f"{name}: forbidden unqualified all-families passing claim")
    uut_path = outdir / "uut-commit.txt"
    if uut_path.is_file():
        uut = uut_path.read_text(encoding="utf-8").strip().splitlines()[0]
        head = _git_rev(root)
        if head and uut != head and uut != "UNKNOWN":
            errors.append(f"uut-commit.txt ({uut}) != git HEAD ({head})")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("certification-package"),
        help="Output directory (default: certification-package)",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate an existing package",
    )
    args = parser.parse_args(argv)
    if args.validate_only:
        errs = validate_package(args.outdir)
        if errs:
            print(json.dumps({"ok": False, "errors": errs}, indent=2))
            return 1
        print(json.dumps({"ok": True, "errors": []}, indent=2))
        return 0

    meta = build_package(outdir=args.outdir)
    errs = validate_package(args.outdir)
    meta["validation_errors"] = errs
    print(json.dumps(meta, indent=2))
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
