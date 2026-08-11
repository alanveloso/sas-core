# USGS NED 1″ terrain tiles (GridFloat)

Required for Category A outdoor HAAT validation (47 CFR § 96.43 / WINNF REG.7).

Package contract: `protection_data/manifests/cbrs_winnforum_protection.yaml`
(slot `terrain_ned` / `terrain_ned_payload`). Keep `VERSION` in sync with the
manifest; binary `.flt` tiles remain gitignored.

## Source

WInnForum [Common-Data](https://github.com/Wireless-Innovation-Forum/Common-Data)
(`data/ned/usgs_ned_1_*_gridfloat_std.zip`). Algorithm and tile layout match the
official harness `reference_models.geo.terrain.TerrainDriver`.

## Minimum tiles for REG family (Cat A outdoor HAAT)

Extract these `.flt` files into this directory (Common-Data naming):

**REG.7 (DC area)**

- `usgs_ned_1_n39w077_gridfloat_std.flt`
- `usgs_ned_1_n39w078_gridfloat_std.flt`
- `usgs_ned_1_n40w077_gridfloat_std.flt`
- `usgs_ned_1_n40w078_gridfloat_std.flt`

**Other REG fixtures (Kansas)**

- `usgs_ned_1_n39w098_gridfloat_std.flt` (device_c)
- `usgs_ned_1_n40w101_gridfloat_std.flt` (device_g)

## Expanded tiles (G1-004 ENV REMEDIATION 02)

Additional tiles for SIQ/GRA/EXZ outdoor Cat-A HAAT and related fixtures
(harness `ceil(lat)` / `floor(lon)` NW-corner encoding). Prefer
`usgs_ned_1_*_gridfloat_std` when present on the Common-Data revision;
otherwise `floatn*_1_std` from Common-Data `master` (same GridFloat payload;
both names accepted by `NedTerrainProvider` / harness `TerrainDriver`).

Provenance: Common-Data commit `f53c776f657b5965d1f5aa7d12ff786265ca91dd`
(+ `master` floatn fallbacks). Hashes: `.cache/ned-download/PROVENANCE.txt`.

- `usgs_ned_1_n40w097_gridfloat_std.flt` / `usgs_ned_1_n40w100_gridfloat_std.flt`
- `floatn40w098_1_std.flt` (SIQ ~40°N/−97.87°)
- `floatn41w098_1_std.flt`
- `floatn42w106_1_std.flt` / `floatn43w100_1_std.flt` / `floatn43w101_1_std.flt`
- `floatn43w106_1_std.flt` / `floatn43w111_1_std.flt`
- `floatn34w107_1_std.flt` (EXZ_2 N1[2] Cat-A outdoor @ 33.85263°N/−106.57198°)
- `usgs_ned_1_n31w090_gridfloat_std.flt` (EXZ_2 N2[1] Cat-A outdoor @ 30.69461°N/−89.82421°)

## Configuration

- Default path: `data/geo/ned` (this directory)
- Override: `SAS_TERRAIN_DIR` / `TERRAIN_DIR`
- Dataset version label precedence: non-empty `SAS_TERRAIN_DATASET_VERSION`,
  else `VERSION` marker, else built-in default (cache key component)

## HAAT tolerances (P6-002)

Documented in `services/terrain/haat.py`:

| Constant | Value | Use |
|---|---|---|
| `HAAT_SYNTHETIC_ABS_TOL_M` | `1e-9` | Analytic terrain regression |
| `HAAT_NED_ABS_TOL_M` | `1e-3` | NED float32 + bilinear vs recorded refs |
| `HAAT_REPEATABILITY_ABS_TOL_M` | `0` | Same inputs → bit-identical |

Tiles are gitignored; do not commit binary DEM data.
