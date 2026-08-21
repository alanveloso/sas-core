"""CLI: python -m tools.profile_doctor — Profile v2 doctor (G6-001)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from spectrum_profiles.v2.doctor import (
    render_profile_doctor_report,
    run_profile_doctor,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m tools.profile_doctor",
        description=(
            "Validate a Spectrum Profile v2 YAML: structure, semantics, "
            "plugin/capability discovery, and optional protection-data readiness. "
            "YAML is parsed as configuration, not executed as code."
        ),
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--id",
        dest="profile_id",
        default=None,
        help="Profile id under spectrum_profiles/profiles/v2/<id>.yaml",
    )
    src.add_argument(
        "path",
        nargs="?",
        default=None,
        type=Path,
        help="Path to a Profile v2 YAML file",
    )
    p.add_argument(
        "--no-check-plugins",
        action="store_true",
        help="Skip device/RF/data plugin discovery checks",
    )
    p.add_argument(
        "--require-data-plugins",
        action="store_true",
        help="Fail when required data capabilities have no installed data_providers",
    )
    p.add_argument(
        "--check-data",
        action="store_true",
        help="Also validate a protection-data bundle against --data-root",
    )
    p.add_argument(
        "--protection-bundle",
        default=None,
        help="Protection-data bundle id (default: cbrs_winnforum_protection)",
    )
    p.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Protection-data root directory for --check-data",
    )
    p.add_argument(
        "--strict-data",
        action="store_true",
        help="Strict protection-data payload checks",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of text",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_profile_doctor(
        profile_id=args.profile_id,
        path=args.path,
        check_plugins=not args.no_check_plugins,
        require_data_plugins=args.require_data_plugins,
        check_protection_data=args.check_data,
        protection_bundle=args.protection_bundle,
        data_root=args.data_root,
        protection_strict=args.strict_data,
    )
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(render_profile_doctor_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
