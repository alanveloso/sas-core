# P8-005 — Pacote final de certificação

**Date:** 2026-08-08
**Status:** DONE (local package)
**UUT commit (package pin):** see `certification-package/uut-commit.txt`
**Official harness:** NOT claimed PASS — deviations documented

## Scope

Plano tree:

```text
certification-package/
├── README.md
├── target-specifications.md
├── uut-commit.txt
├── harness-commit.txt
├── dependency-locks/
├── profiles/
├── datasets-manifest.json
├── configs/
├── results/
├── junit/
├── logs/
├── compliance-matrix.yaml
├── known-deviations.md
└── security-review.md
```

## Implementation

| Piece | Location |
|-------|----------|
| Builder | `tools/p8_005_certification_package.py` |
| Tests | `tests/unit/test_p8_005_certification_package.py` |
| Package | `certification-package/` (generated; committed layout) |

Rebuild:

```bash
.venv/bin/python -m tools.p8_005_certification_package --outdir certification-package
.venv/bin/python -m tools.p8_005_certification_package --validate-only --outdir certification-package
pytest -q tests/unit/test_p8_005_certification_package.py
```

## Observed (2026-08-08)

- Package build: **validation_errors=[]**
- Harness sibling resolved: `928c3150adf7b31e53a96b695bf1fbdd3284ecb2`
- Unit tests: **3 passed** (layout + missing-file + repo package validate)
- Related security/regression units with P8-005: **22 passed**
- Review follow-up: `compliance-matrix.NOTES.md` documents that historical
  case-level `passing` rows are not re-proven by the package alone.

## Non-claims

- No WInnForum family marked `passing`.
- No PASS_OFFICIAL.
- `known-deviations.md` lists ENV/harness/OCSP/legacy gaps explicitly.
- After new commits, rebuild the package so `uut-commit.txt` matches HEAD.
