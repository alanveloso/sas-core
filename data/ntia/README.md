# NTIA DPA KML catalogue

Provision ESC-monitored DPA definitions used by Admin `POST /admin/trigger/load_dpas`.

## Files expected

| File | Role |
|------|------|
| `E-DPAs.kml` | East / coastal ESC-monitored DPAs |
| `P-DPAs.kml` | Portal DPAs |

Do **not** commit the full NTIA KML blobs unless intentionally vendored.
Copy (or symlink) from the WInnForum harness tree:

```bash
mkdir -p data/ntia
cp ../winnforum-sas-harness/data/ntia/E-DPAs.kml data/ntia/
cp ../winnforum-sas-harness/data/ntia/P-DPAs.kml data/ntia/
```

## Resolution order (`services.dpa_service.resolve_dpa_kml_paths`)

1. `SAS_DPA_KML_PATHS` — `os.pathsep`-separated absolute/relative paths
2. `data/ntia/E-DPAs.kml` and `data/ntia/P-DPAs.kml` under this repo
3. Sibling checkout `../winnforum-sas-harness/data/ntia/{E,P}-DPAs.kml`

No DPA names or fixture IDs are hard-coded in application code.
