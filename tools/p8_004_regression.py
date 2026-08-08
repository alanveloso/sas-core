"""P8-004 sequential local regression runner.

Runs the full pytest suite N times with a clean on-disk SQLite residue between
runs, optional timezone overrides, and an RSA/ECC security subset. Writes a
machine-readable JSON summary for evidence (no WInnForum PASS claims).

Usage::

    .venv/bin/python -m tools.p8_004_regression --runs 3 \\
        --outdir artifacts/winnforum/p8_004_regression_<stamp>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

_SUMMARY_RE = re.compile(
    r"(?P<passed>\d+)\s+passed"
    r"(?:,\s*(?P<skipped>\d+)\s+skipped)?"
    r"(?:,\s*(?P<failed>\d+)\s+failed)?"
    r"(?:,\s*(?P<errors>\d+)\s+error(?:s)?)?"
)

# Residue files that can leak across sequential full-suite runs on the host.
_CLEAN_GLOBS = (
    "sas_mvp.db",
    ".pytest_engine_restore.db",
    "*.db-journal",
)


@dataclass(frozen=True)
class RunResult:
    label: str
    exit_code: int
    passed: int | None
    skipped: int | None
    failed: int | None
    errors: int | None
    duration_s: float
    summary_line: str
    tz: str
    log_path: str


def parse_pytest_summary(text: str) -> tuple[int | None, int | None, int | None, int | None, str]:
    """Return (passed, skipped, failed, errors, last_matching_line)."""
    last = ""
    passed = skipped = failed = errors = None
    for line in text.splitlines():
        m = _SUMMARY_RE.search(line)
        if not m:
            continue
        last = line.strip()
        passed = int(m.group("passed"))
        skipped = int(m.group("skipped") or 0)
        failed = int(m.group("failed") or 0)
        errors = int(m.group("errors") or 0)
    return passed, skipped, failed, errors, last


def clean_host_db_residue(root: Path) -> list[str]:
    """Remove common leftover SQLite files; returns removed paths (relative)."""
    removed: list[str] = []
    for pattern in _CLEAN_GLOBS:
        for path in root.glob(pattern):
            if path.is_file():
                path.unlink()
                removed.append(str(path.relative_to(root)))
    return removed


def _python() -> str:
    venv = _ROOT / ".venv" / "bin" / "python"
    return str(venv) if venv.is_file() else sys.executable


def run_pytest(
    *,
    label: str,
    outdir: Path,
    args: list[str],
    env_extra: dict[str, str] | None = None,
) -> RunResult:
    outdir.mkdir(parents=True, exist_ok=True)
    log_path = outdir / f"{label}.log"
    env = os.environ.copy()
    env.setdefault("SAS_SCHEMA_VIA_CREATE_ALL", "1")
    if env_extra:
        env.update(env_extra)
    tz = env.get("TZ", "")
    cmd = [_python(), "-m", "pytest", "-q", "--tb=no", *args]
    t0 = time.monotonic()
    proc = subprocess.run(
        cmd,
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    duration = time.monotonic() - t0
    output = (proc.stdout or "") + (proc.stderr or "")
    log_path.write_text(output, encoding="utf-8")
    passed, skipped, failed, errors, summary = parse_pytest_summary(output)
    return RunResult(
        label=label,
        exit_code=proc.returncode,
        passed=passed,
        skipped=skipped,
        failed=failed,
        errors=errors,
        duration_s=round(duration, 2),
        summary_line=summary,
        tz=tz,
        log_path=str(log_path.relative_to(_ROOT)),
    )


def analyze_flakes(runs: list[RunResult]) -> dict[str, object]:
    """Compare sequential full-suite counts; flag divergence as possible flakes.

    Only ``full_<n>`` labels (the N sequential UTC runs) participate. Timezone
    probes and subsets must not dilute or inflate the 3-run stability claim.
    """
    full = [r for r in runs if re.fullmatch(r"full_\d+", r.label)]
    if len(full) < 2:
        return {"comparable_full_runs": len(full), "stable": True, "notes": []}
    keys = {(r.passed, r.skipped, r.failed, r.errors, r.exit_code) for r in full}
    notes: list[str] = []
    stable = len(keys) == 1
    if not stable:
        notes.append(
            "Full-suite (passed, skipped, failed, errors, exit) diverged across runs: "
            + ", ".join(
                f"{r.label}={(r.passed, r.skipped, r.failed, r.errors, r.exit_code)}"
                for r in full
            )
        )
    else:
        notes.append(
            f"Full-suite counts stable across {len(full)} sequential runs: "
            f"passed={full[0].passed} skipped={full[0].skipped} "
            f"failed={full[0].failed} errors={full[0].errors}"
        )
    return {
        "comparable_full_runs": len(full),
        "stable": stable,
        "notes": notes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3, help="Sequential full-suite runs")
    parser.add_argument(
        "--outdir",
        type=Path,
        default=None,
        help="Artifact directory (default under artifacts/winnforum/)",
    )
    parser.add_argument(
        "--skip-tz-alt",
        action="store_true",
        help="Skip the extra America/Los_Angeles full-suite probe",
    )
    parser.add_argument(
        "--skip-rsa-ecc",
        action="store_true",
        help="Skip RSA/ECC security subset",
    )
    args = parser.parse_args(argv)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outdir = args.outdir or (_ROOT / "artifacts" / "winnforum" / f"p8_004_regression_{stamp}")
    if not outdir.is_absolute():
        outdir = _ROOT / outdir

    results: list[RunResult] = []
    cleaned_all: list[list[str]] = []

    for i in range(1, max(1, args.runs) + 1):
        cleaned_all.append(clean_host_db_residue(_ROOT))
        results.append(
            run_pytest(
                label=f"full_{i}",
                outdir=outdir,
                args=[],
                env_extra={"TZ": "UTC"},
            )
        )

    if not args.skip_rsa_ecc:
        cleaned_all.append(clean_host_db_residue(_ROOT))
        results.append(
            run_pytest(
                label="rsa_ecc",
                outdir=outdir,
                args=[
                    "tests/security/test_tls_matrix.py",
                    "tests/unit/test_cbsd_auth.py",
                    "tests/unit/test_certificate_policy.py",
                    "tests/security/test_certs_and_doctor.py",
                ],
                env_extra={"TZ": "UTC"},
            )
        )

    if not args.skip_tz_alt:
        cleaned_all.append(clean_host_db_residue(_ROOT))
        results.append(
            run_pytest(
                label="full_tz_america_los_angeles",
                outdir=outdir,
                args=[],
                env_extra={"TZ": "America/Los_Angeles"},
            )
        )

    # Ephemeral Docker PostgreSQL integrations (skip gracefully if docker missing).
    cleaned_all.append(clean_host_db_residue(_ROOT))
    results.append(
        run_pytest(
            label="postgres_integrations",
            outdir=outdir,
            args=[
                "tests/integration/test_startup.py",
                "tests/integration/test_fad_publish_postgres.py",
                "tests/integration/test_cpas_multi_sas_postgres.py",
                "tests/integration/test_concurrency_postgres.py",
            ],
            env_extra={"TZ": "UTC"},
        )
    )

    flake = analyze_flakes(results)
    any_fail = any(
        (r.exit_code != 0)
        or (r.failed or 0) > 0
        or (r.errors or 0) > 0
        for r in results
        if r.label.startswith("full_") or r.label == "rsa_ecc"
    )
    # postgres_integrations may skip concurrency — treat hard failures only.
    pg = next((r for r in results if r.label == "postgres_integrations"), None)
    if pg and ((pg.failed or 0) > 0 or (pg.errors or 0) > 0):
        any_fail = True

    payload = {
        "task": "P8-004",
        "at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "uut_commit": _git_head(),
        "outdir": str(outdir.relative_to(_ROOT)),
        "cleaned_residue": cleaned_all,
        "runs": [asdict(r) for r in results],
        "flake_analysis": flake,
        "docker_compose_full_stack": {
            "status": "NOT_RUN",
            "reason": "Requires ./certs (gitignored) and optional .env; "
            "ephemeral PG covered by postgres_integrations instead.",
        },
        "official_harness": {
            "status": "NOT_RUN",
            "reason": "P8-004 local regression only; Rel1Ext harness remains ENV-gated.",
        },
        "verdict": "FAIL" if any_fail or not flake["stable"] else "PASS_LOCAL",
    }
    summary_path = outdir / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 1 if payload["verdict"] != "PASS_LOCAL" else 0


def _git_head() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_ROOT,
            text=True,
        )
        return out.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


if __name__ == "__main__":
    # Allow ``python -m tools.p8_004_regression``.
    raise SystemExit(main())
