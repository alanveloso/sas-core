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

Intermediate `*_GATE_VERIFY_*` mid-phase notes for P5/P6 were superseded by the
`*_GATE_FINAL.md` files and removed during repository hardening (2026-08-07).

## Task evidence (P4–P6)

One task evidence file per plan id (no agent review notes in this tree).

- P4: `P4-001_*` … `P4-005_*`
- P5: `P5-001_*` … `P5-004_*`
- P6: `P6-001_*` … `P6-004_*`

## Matrix

Machine-readable status: `../matrix.yaml` (family rollups are never `passing`).
