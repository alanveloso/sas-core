# P8-004 — Final regression / certification campaign

**Date (UTC):** 2026-08-08T22:44Z…  
**Status:** PRODUCT REGRESSION **PASS_LOCAL**; CERTIFICATION CAMPAIGN **BLOCKED**  
**UUT commit (full):** `3f7f6e9717a4f9308bc8cf986e9493fbae904464`  
**Branch:** `feat/p7-ts-4010`  
**Dirty:** `false`  
**Harness:** `Wireless-Innovation-Forum/Spectrum-Access-System` @ `928c3150adf7b31e53a96b695bf1fbdd3284ecb2`  
**Campaign id:** `p8_004_regression_20260808T224429Z`  
**Artifacts:** `artifacts/winnforum/p8_004_regression_20260808T224429Z/` (gitignored)  
**Summary:** `artifacts/winnforum/p8_004_regression_20260808T224429Z/summary.json`

This evidence is for the **current UUT** above. Historical matrix `passing` rows
(`P3-004_scs_sds_sss.md`, `P5_GATE_FINAL.md`) remain **HISTORICAL_VERIFIED** and
are **not** re-validated as current-UUT official PASS in this campaign.

## Environment (no secrets)

| Item | Value |
|------|-------|
| Python | 3.12.3 |
| OS/kernel | Linux 6.17.0-1030-oem (Ubuntu) x86_64 |
| Host TZ at start | America/Sao_Paulo offset (-03); campaign full_N forced `TZ=UTC` |
| SAS_EXECUTION_MODE (host default) | `production` (security unit tests cover `certification`) |
| Database (full runs) | SQLite per-test + host residue cleanup between runs |
| PostgreSQL | Ephemeral integration subset ran (`postgres_integrations`); concurrency needs `:55432` / `SAS_TEST_DATABASE_URL` → 7 skips |
| Docker / Compose | Docker 29.7.1 / Compose v5.4.0 present; **full stack NOT_RUN** (`./certs` absent) |
| Redis / Celery | Not verified as live stack → **BLOCKED_BY_ENV** |
| Crypto / certificates | UUT `./certs` **absent**; RSA/ECC **unit/security subset** only |
| Datasets | NED VERSION `usgs_ned_1_gridfloat_v1`; NTIA VERSION `1.0.0` |
| `reference_models` | **absent** in venv |
| Rel1Ext | **absent** at harness pin → `BLOCKED_BY_HARNESS` |

## Security pre-check (same UUT)

| Control | Result |
|---------|--------|
| SSRF `allow_lab_private` default | False |
| Lab private egress | certification **or** `SAS_SSRF_ALLOW_LAB_PRIVATE` |
| Admin peer inject | uses `allow_lab_private_egress()` |
| WDB/DB sync | uses `allow_lab_private_egress()` |
| Rate-limit identity | TLS peer cert via `load_client_certificate` |
| Spoofed `x-ssl-client-sha1` | not trusted for identity |
| Certification rate limit | OFF (`test_security_p8_003` 16 passed) |
| Body limit streaming | covered by P8-003 tests |

## Initial local baseline

| Check | Result |
|-------|--------|
| `pytest -q` | **871 passed, 8 skipped, 0 failed** |
| `ruff check .` | All checks passed |
| `mypy compliance tools` | Success |

Skip audit: 7× PG concurrency **KNOWN_ENV**; 1× package PREVIEW/STALE **LOCAL_ONLY**.

## Full runs (same UUT, TZ=UTC)

| Run | exit | passed | skipped | failed | errors | duration_s | JUnit |
|-----|------|--------|---------|--------|--------|------------|-------|
| full_1 | 0 | 871 | 8 | 0 | 0 | 71.69 | `full_1.xml` |
| full_2 | 0 | 871 | 8 | 0 | 0 | 71.79 | `full_2.xml` |
| full_3 | 0 | 871 | 8 | 0 | 0 | 71.70 | `full_3.xml` |

Reset between runs: host SQLite residue cleanup via runner (`clean_host_db_residue`).

## Testcase-level flake analysis

- Comparable full runs: 3  
- JUnit testcase ids: 879 each (`871 PASS` + `8 SKIP`)  
- Inconsistencies: **0**  
- FLAKE_PRODUCT / UNKNOWN: **0**  
- Aggregate counts stable: **yes**  
- `product_regression_ok`: **true**  
- Runner verdict: **PASS_LOCAL**

## Timezone (outside full_1..3 flake set)

| Probe | Result |
|-------|--------|
| full_N UTC | 871/8/0 |
| `full_tz_america_los_angeles` (runner) | 871/8/0 exit 0 |
| `full_tz_america_sao_paulo` (supplemental) | 871/8/0 exit 0 |

No count divergence; no FAIL_PRODUCT observed.

## PostgreSQL / concurrency

| Item | Result |
|------|--------|
| `postgres_integrations` | exit 0; **22 passed, 7 skipped** |
| Concurrency PG | **BLOCKED_BY_ENV** (no `:55432` / `SAS_TEST_DATABASE_URL`) |
| Gate (`evaluate_postgres_gate`) | ok (exit authoritative) |

## Docker / Celery / restart

| Item | Result |
|------|--------|
| Compose full stack | **NOT_RUN** / **BLOCKED_BY_ENV** (`./certs` absent) |
| Celery worker path | **BLOCKED_BY_ENV** |
| Restart/recovery stack | **NOT_RUN** / **BLOCKED_BY_ENV** |

## RSA / ECC

| Item | Result |
|------|--------|
| `rsa_ecc` subset (TLS matrix, CBSD auth, cert policy, doctor) | **61 passed**, exit 0 |
| Official mTLS campaign with provisioned RSA/ECC cert trees | **BLOCKED_BY_ENV** (no `./certs`) |

## Official harness inventory

Harness pin has Release-1 FT.S modules (REG…WDB, PAT/IPR/MCP, …). Rel1Ext suite files: **not present**.

| Family | Available? | Executed? | Result | Classification | Evidence |
|--------|------------|-----------|--------|----------------|----------|
| REG | yes (pin) | no | — | NOT_RUN | this campaign / no certs |
| SIQ | yes | no | — | NOT_RUN | |
| GRA | yes | no | — | NOT_RUN | |
| HBT | yes | no | — | NOT_RUN | |
| RLQ | yes | no | — | NOT_RUN | |
| DRG | yes | no | — | NOT_RUN | |
| SCS | yes | no | — | NOT_RUN | historical P3-004 only |
| SDS | yes | no | — | NOT_RUN | historical P3-004 only |
| SSS | yes | no | — | NOT_RUN | historical P3-004 only |
| FAD | yes | no | — | NOT_RUN | historical P5_GATE_FINAL only |
| EXZ | yes | no | — | NOT_RUN | |
| BPR | yes | no | — | NOT_RUN | |
| EPR | yes | no | — | NOT_RUN | |
| QPR | yes | no | — | NOT_RUN | |
| WDB | yes | no | — | NOT_RUN | |
| FDB | yes | no | — | NOT_RUN | |
| GPR | yes | no | — | NOT_RUN | |
| PCR | yes | no | — | NOT_RUN | |
| PPR | yes | no | — | NOT_RUN | |
| FPR | yes | no | — | NOT_RUN | |
| PAT | yes | no | — | NOT_RUN / NUMERIC_PARITY open | `reference_models` absent |
| IPR | yes | no | — | NOT_RUN | |
| MCP | yes | no | — | NOT_RUN | |
| Rel1Ext | **no** | no | — | **BLOCKED_BY_HARNESS** | pin `928c315` |

No **PASS_OFFICIAL** claimed.

## Historical evidence (matrix passing rows)

| Classification | Paths |
|----------------|-------|
| CURRENT_UUT | (none from official harness this campaign) |
| HISTORICAL_VERIFIED | `compliance/evidence/P3-004_scs_sds_sss.md` (56 rows), `compliance/evidence/P5_GATE_FINAL.md` (2 rows) |
| HISTORICAL_UNVERIFIED | — |
| MISSING | — |

## FAIL_PRODUCT

NONE

## Product flakes

NONE

## Certification blockers

- **ENV:** `./certs`, Compose/Celery/Redis full stack, PG concurrency URL  
- **DATASET:** `reference_models` / full NED-NLCD payloads  
- **HARNESS:** Rel1Ext absent; official families not executed this run  
- **SPEC:** Rel1Ext binding still open in plan  
- **NUMERIC_PARITY:** PAT/IPR/MCP not measured officially  

## Verdicts

- **P8-004 PRODUCT REGRESSION:** PASS  
- **P8-004 CERTIFICATION CAMPAIGN:** BLOCKED  
- **P8-004 COMPLETE:** YES (product pass + external blockers documented; summary matches HEAD)

## Non-claims

- Does **not** assert WInnForum family PASS / PASS_OFFICIAL.  
- Does **not** authorize P8-005 FINAL until an operator regenerates the package against this summary after review.
