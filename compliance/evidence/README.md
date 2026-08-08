# Compliance evidence index

Authoritative, versionable evidence lives in this directory (`compliance/evidence/`).
Raw harness logs may live under gitignored `artifacts/winnforum/`.

## Phase gates (authoritative)

| Phase | Gate evidence |
|-------|----------------|
| P0 | `docs/compliance/evidence/P0_GATE_VERIFY_2026-08-05.md` (legacy path) |
| P3 SCS/SDS/SSS | `P3-004_scs_sds_sss.md` |
| P4 | `P4_GATE_VERIFY_2026-08-07_1254.md` (final mid-phase close) |
| P5 | **`P5_GATE_FINAL.md`** |
| P6 | **`P6_GATE_FINAL.md`** |
| P7 | Rel1Ext gate still open — `P7_GATE_VERIFY_2026-08-08.md` |
| P8 | **`P8_GATE_VERIFY_2026-08-08.md`** (APROVADA produto 16:38Z — P8-001…005) |

Intermediate `*_GATE_VERIFY_*` mid-phase notes for P5/P6 were superseded by the
`*_GATE_FINAL.md` files and removed during repository hardening (2026-08-07).

## Task evidence (P4–P8)

One task evidence file per plan id (no agent review notes in this tree).

- P4: `P4-001_*` … `P4-005_*`
- P5: `P5-001_*` … `P5-004_*`
- P6: `P6-001_*` … `P6-004_*`
- P7: `P7-004_*`, `P7-005_*`, `P7_FINAL_AUDIT.md` (Rel1Ext official gate still open)
- P8: `P8-001_observability.md`, `P8-002_migrations.md`, `P8-003_security.md`, `P8-004_regression_campaign.md` (authoritative campaign; `P8-004_regression.md` historical), `P8-005_certification_package.md`
- Pre-P8 product close: `FEATURE_COMPLETE_AUDIT.md`

## Matrix

Machine-readable status: `../matrix.yaml` (family rollups are never `passing`).
