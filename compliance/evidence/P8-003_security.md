# P8-003 — Segurança operacional

**Date:** 2026-08-08
**Status:** DONE (local)
**Official harness:** N/A (hardening; no family PASS claim)

## Scope

Plano bullets:

- RBAC Admin/CBSD/DP/SAS;
- secrets fora do `.env` de exemplo em produção;
- rotação de certificados;
- CRL/OCSP conforme target;
- proteção contra SSRF e payloads grandes;
- rate limiting operacional sem quebrar o harness.

## Implementation

| Piece | Location |
|-------|----------|
| RBAC surface matrix | `services/rbac.py` |
| Shared SSRF egress checks | `services/ssrf.py` (peer inject, DB sync, FAD) |
| Max body (`Content-Length` → 413) | `services/request_limits.py` + `main.py` |
| Rate limit (forced off in certification) | `services/rate_limit.py` + `main.py` |
| Trust/CRL status + reload | `services/trust_reload.py`; Admin GET/POST `/admin/security/*` |
| FAD download byte cap | `services/fad_client_service.py` (`sas_fad_max_file_bytes`) |
| Config knobs | `config.py` (`sas_max_request_body_bytes`, rate limit, `sas_ssl_ocsp_mode=disabled`, …) |
| Secrets guidance | `.env.example` PRODUCTION SECRETS section; empty defaults for sync creds |

## Acceptance commands

```bash
pytest -q tests/unit/test_security_p8_003.py
pytest -q tests/unit/test_security_p8_003.py \
  tests/unit/test_admin_inventory.py \
  tests/contract/test_admin_no_catchall.py \
  tests/unit/test_fad_client.py \
  tests/unit/test_c5_qpr_wdb_pcr_fdb.py \
  tests/unit/test_multi_sas.py
ruff check services/ssrf.py services/rbac.py services/request_limits.py \
  services/rate_limit.py services/trust_reload.py \
  services/database_sync_service.py services/fad_client_service.py \
  routes/admin_routes.py main.py config.py tests/unit/test_security_p8_003.py
```

**Observed (2026-08-08):** `test_security_p8_003` **10 passed**; related suites **74 passed**; ruff **All checks passed**.

## Security closure (2026-08-08 follow-up)

- Canonical role OIDs: `services/winnf_role_oids.py` (re-exported by `mtls_auth`;
  `rbac` derives dotted strings from the same objects).
- Request size limit: pure ASGI middleware counts body bytes incrementally;
  does not rely only on `Content-Length`.
- Review fix: rate-limit keys use TLS peer cert via `load_client_certificate`
  (not spoofable `x-ssl-client-sha1` headers); SSRF default `allow_lab_private=False`.

## Non-claims

- No WInnForum family marked `passing`.
- OCSP network validation is not implemented; target mode is `disabled` (CRL-oriented).
- Invalid peer inject URLs return empty Admin 200 without persistence (existing Admin contract).
- Rate limiting must stay off under `SAS_EXECUTION_MODE=certification`.
