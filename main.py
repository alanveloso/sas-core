"""
SAS Agent entrypoint — HTTPS + mTLS for the WINNF harness.

- RSA endpoint:  https://0.0.0.0:9000  (server.cert)
- ECDSA endpoint: https://0.0.0.0:9001  (server-ecc.cert) — SSS_3 / SSS_4

Usage (from sas_mvp_core/ in the Spectrum-Access-System monorepo):
  .venv/bin/python main.py
"""

from __future__ import annotations

import ssl
import sys
import threading
from pathlib import Path

# Allow `python main.py` and `uvicorn main:app` from sas_mvp_core/
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import get_settings
from database import init_db
from routes.admin_routes import router as admin_router
from routes.cbsd_routes import router as cbsd_router
from routes.cbsd_version_routes import router as cbsd_version_router
from routes.sas_sas_routes import router as sas_sas_router
from services.error_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from services.mtls_auth import (
    ECC_CIPHERS,
    RSA_CIPHERS,
    create_mtls_ssl_context,
    patch_uvicorn_for_client_cert,
)

# Must run before uvicorn binds so RequestResponseCycle exposes the TLS transport.
patch_uvicorn_for_client_cert()

app = FastAPI(title="SAS Agent", version="0.1.0")
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.include_router(admin_router)
app.include_router(cbsd_router)
# Version catch-alls after concrete /v1.2 routes so supported version keeps priority.
app.include_router(cbsd_version_router)
app.include_router(sas_sas_router)


@app.on_event("startup")
def on_startup():
    from spectrum_profiles.context import active_profile_id, get_active_profile

    profile = get_active_profile()
    print(
        f"Active spectrum profile: {active_profile_id()} "
        f"(rule={profile.rule_applied}, "
        f"band={profile.band_plan.low_hz}-{profile.band_plan.high_hz} Hz)"
    )
    init_db()


def _rsa_ssl_context_factory(config, default_factory):
    del config, default_factory
    settings = get_settings()
    return create_mtls_ssl_context(
        certfile=settings.resolved_ssl_certfile,
        keyfile=settings.resolved_ssl_keyfile,
        ca_certs=settings.resolved_ssl_ca_certs,
        crl_dir=settings.resolved_ssl_crl_dir,
        ciphers=RSA_CIPHERS,
    )


def _ecc_ssl_context_factory(config, default_factory):
    del config, default_factory
    settings = get_settings()
    return create_mtls_ssl_context(
        certfile=settings.resolved_ssl_ecc_certfile,
        keyfile=settings.resolved_ssl_ecc_keyfile,
        ca_certs=settings.resolved_ssl_ca_certs,
        crl_dir=settings.resolved_ssl_crl_dir,
        ciphers=ECC_CIPHERS,
    )


def _run_uvicorn(port: int, certfile: Path, keyfile: Path, ssl_factory) -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=port,
        ssl_certfile=str(certfile),
        ssl_keyfile=str(keyfile),
        ssl_ca_certs=str(settings.resolved_ssl_ca_certs),
        ssl_cert_reqs=ssl.CERT_REQUIRED,
        ssl_context_factory=ssl_factory,
        # Prefer h11; httptools is also patched in mtls_auth for mTLS fingerprinting.
        http="h11",
        reload=False,
        log_level="info",
    )


def main():
    settings = get_settings()
    from services.cert_layout import format_certificate_error, validate_certificate_layout

    cert_check = validate_certificate_layout(settings)
    if not cert_check.ok:
        raise SystemExit(format_certificate_error(cert_check))

    certfile = settings.resolved_ssl_certfile
    keyfile = settings.resolved_ssl_keyfile
    ecc_certfile = settings.resolved_ssl_ecc_certfile
    ecc_keyfile = settings.resolved_ssl_ecc_keyfile

    ecc_thread = threading.Thread(
        target=_run_uvicorn,
        kwargs={
            "port": settings.ecc_port,
            "certfile": ecc_certfile,
            "keyfile": ecc_keyfile,
            "ssl_factory": _ecc_ssl_context_factory,
        },
        name="uvicorn-ecc",
        daemon=True,
    )
    ecc_thread.start()
    print(
        f"ECDSA mTLS listener starting on "
        f"https://{settings.api_host}:{settings.ecc_port}"
    )

    print(
        f"RSA mTLS listener starting on "
        f"https://{settings.api_host}:{settings.rsa_port}"
    )
    _run_uvicorn(
        port=settings.rsa_port,
        certfile=certfile,
        keyfile=keyfile,
        ssl_factory=_rsa_ssl_context_factory,
    )


if __name__ == "__main__":
    main()
