# P8-005 — Pacote final de certificação

**Date:** 2026-08-08  
**Status:** DONE (FINAL package bound to current UUT)  
**UUT commit:** `3f7f6e9717a4f9308bc8cf986e9493fbae904464`  
**P8-004 campaign:** `p8_004_regression_20260808T224429Z` (same UUT, dirty=false, PASS_LOCAL)  
**Harness:** `928c3150adf7b31e53a96b695bf1fbdd3284ecb2`  
**Official harness:** NOT claimed PASS — deviations + historical evidence classified

## Scope

Rebuild `certification-package/` in **FINAL** mode after the P8-004 current-UUT
campaign, with integrity checks from `tools/p8_005_certification_package.py`:

- P8-004 summary must match package UUT;
- dirty/aborted summaries rejected;
- `package-status.json` mode=`final`;
- passing matrix rows bundle evidence under `compliance/evidence/` in-package;
- historical PASS ≠ current-UUT official PASS (`passing-evidence-manifest.json`).

## Rebuild / validate

```bash
.venv/bin/python -m tools.p8_005_certification_package \
  --outdir certification-package --mode final
.venv/bin/python -m tools.p8_005_certification_package \
  --validate-only --require-final --outdir certification-package
pytest -q tests/unit/test_p8_005_certification_package.py
```

Directory is listed in `.gitignore` as a generated bundle; regenerate after any
UUT change so `uut-commit.txt` stays equal to `git rev-parse HEAD`.

## Observed (2026-08-08 FINAL)

| Check | Result |
|-------|--------|
| Build `--mode final` | `validation_errors=[]` |
| `uut-commit.txt` | `3f7f6e9717a4f9308bc8cf986e9493fbae904464` (= HEAD) |
| `package-status.json` | mode=final, `current_uut_campaign_match=true`, `certification_ready=true` |
| P8-004 summary copied | `results/p8_004_regression_summary.json` from campaign `20260808T224429Z` |
| Passing evidence bundled | 58 rows; P3-004 + P5_GATE_FINAL present; classified HISTORICAL_VERIFIED |
| Validate `--require-final` | `ok: true` |
| Unit tests P8-004/005 | **32 passed** |

## Non-claims

- No WInnForum family marked newly `passing`.
- No PASS_OFFICIAL.
- Certification campaign remains **BLOCKED** for ENV/HARNESS/DATASET (certs,
  Rel1Ext, Compose/Celery, official PAT/IPR/MCP) — see
  `compliance/evidence/P8-004_regression_campaign.md`.
- Historical matrix `passing` rows are not re-proven as current-UUT official PASS.
