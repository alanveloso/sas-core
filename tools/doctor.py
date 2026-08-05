"""Operational diagnostics for sas-core (certificates, profile, runtime)."""

from __future__ import annotations

import inspect
import sys
from dataclasses import dataclass, field

import uvicorn
from uvicorn.config import Config

from config import clear_settings_cache, get_settings
from services.cert_layout import validate_certificate_layout
from spectrum_profiles.loader import ProfileError, load_profile


@dataclass
class DoctorFinding:
    name: str
    ok: bool
    detail: str


@dataclass
class DoctorReport:
    findings: list[DoctorFinding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(item.ok for item in self.findings)


def run_doctor() -> DoctorReport:
    clear_settings_cache()
    settings = get_settings()
    report = DoctorReport()

    report.findings.append(
        DoctorFinding(
            name="python",
            ok=sys.version_info >= (3, 11),
            detail=f"{sys.version.split()[0]} (requires >=3.11)",
        )
    )

    certs = validate_certificate_layout(settings)
    if certs.ok:
        detail = f"CERTS_DIR={certs.certs_dir} (RSA/ECC/CA/CRL present)"
        if certs.notes:
            detail += "; " + "; ".join(certs.notes)
        report.findings.append(DoctorFinding(name="certificates", ok=True, detail=detail))
    else:
        detail = f"CERTS_DIR={certs.certs_dir} missing={certs.missing}"
        if certs.notes:
            detail += "; " + "; ".join(certs.notes)
        report.findings.append(DoctorFinding(name="certificates", ok=False, detail=detail))

    try:
        profile = load_profile(settings.sas_profile)
        report.findings.append(
            DoctorFinding(
                name="spectrum_profile",
                ok=True,
                detail=(
                    f"{profile.id} v{profile.version} "
                    f"band={profile.band_plan.low_hz}-{profile.band_plan.high_hz} Hz"
                ),
            )
        )
    except ProfileError as exc:
        report.findings.append(
            DoctorFinding(name="spectrum_profile", ok=False, detail=str(exc))
        )

    has_factory = "ssl_context_factory" in inspect.signature(uvicorn.run).parameters
    has_config = "ssl_context_factory" in inspect.signature(Config.__init__).parameters
    report.findings.append(
        DoctorFinding(
            name="uvicorn_ssl_context_factory",
            ok=has_factory and has_config and uvicorn.__version__ == "0.52.1",
            detail=f"uvicorn {uvicorn.__version__} ssl_context_factory={has_factory and has_config}",
        )
    )

    report.findings.append(
        DoctorFinding(
            name="database_url",
            ok=bool(settings.database_url),
            detail=settings.database_url,
        )
    )
    report.findings.append(
        DoctorFinding(
            name="sas_execution_mode",
            ok=settings.sas_execution_mode in {"production", "certification"},
            detail=settings.sas_execution_mode,
        )
    )
    return report


def render_report(report: DoctorReport) -> str:
    lines = ["sas-core doctor", "=" * 16]
    for item in report.findings:
        status = "OK" if item.ok else "FAIL"
        lines.append(f"[{status}] {item.name}: {item.detail}")
    lines.append("=" * 16)
    lines.append("RESULT: " + ("PASS" if report.ok else "FAIL"))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    del argv  # reserved for future flags
    report = run_doctor()
    print(render_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
