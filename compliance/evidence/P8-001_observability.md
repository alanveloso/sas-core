# P8-001 — Observabilidade

**Date:** 2026-08-08
**Status:** DONE (local)
**Official harness:** N/A (hardening; no family PASS claim)

## Scope

Plano bullets:

- correlation ID por request/batch/item;
- audit log admin / CPAS / RF decisions;
- métricas de latência/erro;
- logs sem dados sensíveis;
- dump diagnóstico por caso falho.

## Implementation

| Piece | Location |
|-------|----------|
| Correlation `X-Request-ID` | `services/request_context.py` + `ObservabilityMiddleware` |
| Batch bind | `routes/cbsd_routes._run_batch` binds `batchId` **before** service call |
| Item index | Bound **after** merge for protocol metrics only (batch still one domain call) |
| Unified audit helper | `services/audit_log.py` (`admin_audit`, optional `rf_decision_audit`) |
| Admin audit | `/admin/injectdata/fcc_id`, `/admin/trigger/daily_activities_immediately`; `/admin/reset` logs `request_id` only (no DB session across `reset_db`) |
| CPAS audit + requestId | `services/cpas_service._append_cpas_audit` |
| Metrics | `services/metrics.py` + `GET /admin/metrics` (Admin mTLS; not a WINNF procedure) |
| Log redaction | `services/logging_redaction.py` |
| Failure dumps | `tools/winnforum/failure_dump.py` wired in `runner.py` → `artifacts/.../failures/<case>/` |

## RF decisions

Durable RF decision lists remain on `cpas_pipeline_audit` (generation N). Protocol non-success codes are counted in metrics per procedure. Domain DPA/ESC/PPA audits unchanged.

## Tests

- `tests/unit/test_observability_p8.py`
- Existing admin/DPA/CPAS regressions

## Acceptance commands

```bash
pytest -q tests/unit/test_observability_p8.py
ruff check .
pytest -q
```

**Observed (2026-08-08):** `test_observability_p8` 10 passed; full suite **817 passed, 7 skipped, 0 failed**; `ruff check` on touched modules OK.

## Non-claims

- No WInnForum family marked `passing`.
- Not a Rel1Ext/P7 gate substitute.
- Metrics are in-process (process-local); not Prometheus scrape format (JSON Admin snapshot).
