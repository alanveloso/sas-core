# P8-004 — Regressão final

**Date:** 2026-08-08
**Status:** DONE (PASS_LOCAL)
**UUT commit:** `1949e6e`
**Official harness:** NOT_RUN (ENV / Rel1Ext — not claimed)
**Artefacts:** `artifacts/winnforum/p8_004_regression_20260808T1602Z/` (gitignored)

## Scope

Plano bullets:

- 3 runs completos sequenciais;
- banco limpo em cada run;
- RSA e ECC;
- stack local de certificação;
- stack Docker/PostgreSQL/Celery;
- timezone UTC e timezone alternativo;
- análise de flakes.

## Runner

`tools/p8_004_regression.py` (+ `tests/unit/test_p8_004_regression.py`):

```bash
.venv/bin/python -m tools.p8_004_regression --runs 3 \
  --outdir artifacts/winnforum/p8_004_regression_<stamp>
```

Each full run deletes host SQLite residue (`sas_mvp.db`, restore DB) before
`pytest -q`. Tests themselves already use per-test `tmp_path` DBs.

## Observed results (2026-08-08)

| Label | Result | Notes |
|-------|--------|-------|
| full_1 (TZ=UTC) | **842 passed, 7 skipped** | exit 0 |
| full_2 (TZ=UTC) | **842 passed, 7 skipped** | exit 0 |
| full_3 (TZ=UTC) | **842 passed, 7 skipped** | exit 0 |
| rsa_ecc | **61 passed** | TLS matrix + auth/certs |
| full_tz_america_los_angeles | **842 passed, 7 skipped** | exit 0 |
| postgres_integrations | **22 passed, 7 skipped** | ephemeral Docker PG; concurrency KNOWN_ENV |
| celery unit (`test_cpas_execution_mode`) | **7 passed** | certification inline / production enqueue |

**Flakes:** none — full-suite counts identical across 3×UTC + LA timezone probe
(`passed=842 skipped=7 failed=0`).

**Verdict file:** `summary.json` → `PASS_LOCAL`.

## ENV / not met this run

| Item | Status |
|------|--------|
| Docker Compose full stack (api+worker+rabbitmq+db) | **NOT_RUN** — `./certs` absent (gitignored); compose config validates |
| Official WInnForum harness Rel1Ext | **NOT_RUN** |
| Concurrency on shared PG `:55432` / `SAS_TEST_DATABASE_URL` | **KNOWN_ENV** (7 skips) |

## Non-claims

- No WInnForum family marked `passing`.
- No PASS_OFFICIAL.
- Compose/Celery end-to-end stack remains an ops/ENV follow-up when certs are provisioned.
