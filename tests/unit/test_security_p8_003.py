"""P8-003 operational security: SSRF, body limits, rate limit, RBAC matrix, trust reload."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from config import clear_settings_cache, get_settings
from main import app
from services import mtls_auth, rbac, winnf_role_oids
from services.request_limits import RequestSizeLimitMiddleware
from services.rbac import ROLE_CBSD, ROLE_DOMAIN_PROXY, ROLE_SAS, roles_for_surface
from services.ssrf import SsrfError, assert_https_egress_url_allowed

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_settings():
    clear_settings_cache()
    yield
    clear_settings_cache()


def test_rbac_matrix_surfaces():
    assert ROLE_SAS in roles_for_surface("admin")
    assert ROLE_SAS in roles_for_surface("sas_sas")
    assert ROLE_CBSD in roles_for_surface("cbsd_api")
    assert ROLE_DOMAIN_PROXY in roles_for_surface("cbsd_api")
    with pytest.raises(KeyError):
        roles_for_surface("unknown")


def test_canonical_role_oids_match_mtls_and_rbac():
    """Single source: winnf_role_oids; mtls_auth + rbac must not drift."""
    assert winnf_role_oids.OID_ROLE_SAS.dotted_string == "1.3.6.1.4.1.46609.1.1.1"
    assert winnf_role_oids.OID_ROLE_INSTALLER.dotted_string == "1.3.6.1.4.1.46609.1.1.2"
    assert winnf_role_oids.OID_ROLE_CBSD.dotted_string == "1.3.6.1.4.1.46609.1.1.3"
    assert (
        winnf_role_oids.OID_ROLE_DOMAIN_PROXY.dotted_string
        == "1.3.6.1.4.1.46609.1.1.4"
    )

    assert mtls_auth.OID_ROLE_SAS is winnf_role_oids.OID_ROLE_SAS
    assert mtls_auth.OID_ROLE_INSTALLER is winnf_role_oids.OID_ROLE_INSTALLER
    assert mtls_auth.OID_ROLE_CBSD is winnf_role_oids.OID_ROLE_CBSD
    assert mtls_auth.OID_ROLE_DOMAIN_PROXY is winnf_role_oids.OID_ROLE_DOMAIN_PROXY

    assert rbac.ROLE_SAS == winnf_role_oids.OID_ROLE_SAS.dotted_string
    assert rbac.ROLE_INSTALLER == winnf_role_oids.OID_ROLE_INSTALLER.dotted_string
    assert rbac.ROLE_CBSD == winnf_role_oids.OID_ROLE_CBSD.dotted_string
    assert rbac.ROLE_DOMAIN_PROXY == winnf_role_oids.OID_ROLE_DOMAIN_PROXY.dotted_string


def test_ssrf_rejects_http_and_metadata():
    with pytest.raises(SsrfError):
        assert_https_egress_url_allowed("http://example.com/x")
    with pytest.raises(SsrfError):
        assert_https_egress_url_allowed("https://user:pass@example.com/x")
    with pytest.raises(SsrfError):
        assert_https_egress_url_allowed("https://metadata.google.internal/latest")


def test_ssrf_allows_lab_loopback_https(monkeypatch):
    def _fake_getaddrinfo(host, *args, **kwargs):
        return [(None, None, None, None, ("127.0.0.1", 0))]

    monkeypatch.setattr("services.ssrf.socket.getaddrinfo", _fake_getaddrinfo)
    assert_https_egress_url_allowed("https://127.0.0.1:8443/dump")


def test_request_size_limit_rejects_large_content_length(monkeypatch):
    monkeypatch.setenv("SAS_MAX_REQUEST_BODY_BYTES", "1024")
    clear_settings_cache()
    assert get_settings().sas_max_request_body_bytes == 1024
    resp = client.post(
        "/admin/injectdata/fcc_id",
        json={"fccId": "x", "fccMaxEirp": 30},
        headers={"Content-Length": "99999"},
    )
    assert resp.status_code == 413


def test_asgi_size_limit_no_content_length_under_and_over(monkeypatch):
    """Incremental ASGI receive counting without Content-Length (A/B/C/E/F)."""
    import asyncio

    monkeypatch.setenv("SAS_MAX_REQUEST_BODY_BYTES", "8")
    clear_settings_cache()

    seen: list[bytes] = []

    async def inner(scope, receive, send):
        req = Request(scope, receive)
        seen.append(await req.body())
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": b"ok"})

    app_mw = RequestSizeLimitMiddleware(inner)

    async def _call(chunks: list[bytes], *, content_length: str | None = None):
        headers = [(b"host", b"test")]
        if content_length is not None:
            headers.append((b"content-length", content_length.encode()))
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 123),
            "server": ("test", 80),
            "scheme": "http",
        }
        queue = list(chunks)

        async def receive():
            if queue:
                body = queue.pop(0)
                return {
                    "type": "http.request",
                    "body": body,
                    "more_body": bool(queue),
                }
            return {"type": "http.disconnect"}

        status_holder: dict[str, int] = {}

        async def send(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]

        await app_mw(scope, receive, send)
        return status_holder["status"]

    async def _run():
        seen.clear()
        assert await _call([b"12345678"]) == 200  # exact limit
        assert seen == [b"12345678"]

        seen.clear()
        assert await _call([b"123456789"]) == 413  # limit + 1
        assert seen == []

        seen.clear()
        assert await _call([b"12", b"34", b"56", b"78"]) == 200  # chunked under
        assert seen == [b"12345678"]

        seen.clear()
        assert await _call([b"12", b"34", b"56", b"789"]) == 413  # chunked over
        assert seen == []

        # Declared Content-Length smaller than real bytes → real limit prevails.
        seen.clear()
        assert await _call([b"123456789"], content_length="4") == 413
        assert seen == []

        # Announced Content-Length over limit → early 413 without forwarding.
        seen.clear()
        assert await _call([b"xx"], content_length="999") == 413
        assert seen == []

    asyncio.run(_run())

def test_request_size_limit_preserves_valid_cbsd_body(monkeypatch):
    """Valid CBSD-shaped JSON under the limit reaches the route unchanged."""
    monkeypatch.setenv("SAS_MAX_REQUEST_BODY_BYTES", "65536")
    clear_settings_cache()
    payload = {
        "registrationRequest": [
            {
                "fccId": "test",
                "cbsdSerialNumber": "s1",
                "userId": "u1",
                "cbsdCategory": "A",
                "airInterface": {"radioTechnology": "E_UTRA"},
                "cbsdInfo": {"model": "m"},
                "installationParam": {
                    "latitude": 37.0,
                    "longitude": -122.0,
                    "height": 3.0,
                    "heightType": "AGL",
                    "indoorDeployment": True,
                },
            }
        ]
    }
    raw = json.dumps(payload).encode()
    resp = client.post(
        "/v1.2/registration",
        content=raw,
        headers={"content-type": "application/json"},
    )
    # Auth / validation may fail; must not be size-limit 413 and body must parse.
    assert resp.status_code != 413
    assert len(raw) < get_settings().sas_max_request_body_bytes


def test_certification_keeps_size_limit_and_disables_rate_limit(monkeypatch):
    monkeypatch.setenv("SAS_EXECUTION_MODE", "certification")
    monkeypatch.setenv("SAS_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("SAS_RATE_LIMIT_PER_SECOND", "1")
    monkeypatch.setenv("SAS_RATE_LIMIT_BURST", "1")
    monkeypatch.setenv("SAS_MAX_REQUEST_BODY_BYTES", "64")
    clear_settings_cache()

    for _ in range(20):
        assert client.get("/admin/metrics").status_code == 200

    oversized = client.post(
        "/admin/injectdata/fcc_id",
        content=b"x" * 128,
        headers={"content-type": "application/json", "Content-Length": "128"},
    )
    assert oversized.status_code == 413


def test_rate_limit_disabled_in_certification(monkeypatch):
    monkeypatch.setenv("SAS_EXECUTION_MODE", "certification")
    monkeypatch.setenv("SAS_RATE_LIMIT_ENABLED", "true")
    clear_settings_cache()
    # Many rapid requests must still succeed (middleware forced off).
    for _ in range(30):
        resp = client.get("/admin/metrics")
        assert resp.status_code == 200


def test_rate_limit_enforced_in_production(monkeypatch):
    monkeypatch.setenv("SAS_EXECUTION_MODE", "production")
    monkeypatch.setenv("SAS_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("SAS_RATE_LIMIT_PER_SECOND", "1")
    monkeypatch.setenv("SAS_RATE_LIMIT_BURST", "2")
    clear_settings_cache()
    codes = [client.get("/admin/metrics").status_code for _ in range(5)]
    assert 429 in codes
    assert codes.count(200) >= 1


def test_peer_sas_rejects_ssrf_url(db_session, monkeypatch):
    monkeypatch.setattr(
        "services.ssrf.socket.getaddrinfo",
        lambda *a, **k: (_ for _ in ()).throw(OSError("no")),
    )
    # http scheme fails before DNS
    resp = client.post(
        "/admin/injectdata/peer_sas",
        json={"certificateHash": "AA:BB", "url": "http://evil.example/dump"},
    )
    assert resp.status_code == 200
    from models.models import PeerSas
    import database

    session = database.SessionLocal()
    try:
        assert session.query(PeerSas).filter_by(certificate_hash="AA:BB").first() is None
    finally:
        session.close()


def test_trust_material_admin_endpoints():
    get_resp = client.get("/admin/security/trust_material")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert "crlFiles" in body
    assert body["ocspMode"] == "disabled"
    post_resp = client.post("/admin/security/reload_trust_material")
    assert post_resp.status_code == 200
    assert "notes" in post_resp.json()


def test_ocsp_mode_default_disabled():
    assert get_settings().sas_ssl_ocsp_mode == "disabled"


def test_env_example_documents_production_secrets():
    text = open(".env.example", encoding="utf-8").read()
    assert "PRODUCTION SECRETS" in text
    assert "DB_SYNC_PASSWORD=" in text
    # Empty default in example (no literal password=password trap).
    assert "DB_SYNC_PASSWORD=password" not in text
