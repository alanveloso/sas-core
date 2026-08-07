# Spectrum Access System Core (`sas-core`)

Runnable **Spectrum Access System (SAS)** for the CBRS band (3550–3700 MHz),
evolved toward selected [WInnForum](https://github.com/Wireless-Innovation-Forum/CBRS-SAS-Test-Harness)
certification suites (**WINNF-TS-0061** / related).

This repository is a lab / interoperability baseline — not a commercial RF product.
Claimed WInnForum results require stored evidence under `compliance/evidence/`;
do not treat README prose as an official PASS.

---

## Interfaces

| Interface | Prefix | Auth | Purpose |
|-----------|--------|------|---------|
| **CBSD ↔ SAS** | `/v1.2` | mTLS (CBSD) | Registration, SIQ, Grant, Heartbeat, Relinquishment, Deregistration |
| **SAS ↔ SAS** | `/v1.3` | mTLS (peer SAS) | Full Activity Dump (FAD) |
| **Admin** | `/admin` | mTLS (harness / operator) | Injects, CPAS, sync, PAT query |

TLS listeners (Uvicorn):

- `https://0.0.0.0:9000` — RSA
- `https://0.0.0.0:9001` — ECDSA (SAS↔SAS ECC / SSS)

---

## Layout

| Path | Role |
|------|------|
| `routes/` | CBSD, SAS↔SAS, Admin HTTP |
| `services/` | Domain logic (lifecycle, FAD, CPAS, IAP, propagation, terrain, …) |
| `protection_data/` | Versioned RF/protection dataset manifests |
| `spectrum_profiles/` | Band plan / profile YAML |
| `data/` | Dataset root (VERSION markers; large payloads often gitignored) |
| `compliance/` | Matrix + versioned evidence |
| `tools/` | doctor, certs, WInnForum runner |

Stack: Python ≥3.11, FastAPI, SQLAlchemy, Pydantic, Celery, Uvicorn mTLS.

---

## Current compliance posture (honest)

Phases **P0–P6** product tasks are complete on branch work through
`feat/p6-protection-models` (see `compliance/evidence/P6_GATE_FINAL.md`).

| Area | Local status | Official harness |
|------|--------------|------------------|
| Protocol / Admin contract / CPAS / FAD | Strong local + PG tests | Case-level PASS only with evidence |
| HAAT / NED packaging | PASS_LOCAL | Needs full DEM for campaigns |
| Propagation Admin API | PASS_LOCAL (injectable engines) | PAT needs compiled ITM, NLCD, deps |
| IAP engine + frozen peer FAD | PASS_LOCAL (optional CPAS hook) | IPR/FDB RF campaigns still open |

**Not claimed here:** “all WINNF suites validated.” Use `compliance/matrix.yaml`.

---

## Install (fresh)

```bash
git clone <sas-core-repository-url>
cd sas-core

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade 'pip==25.2'
pip install -r requirements.lock.txt
pip install -e .

python -m tools.doctor   # expects CERTS_DIR or harness certs
```

Editable install includes `protection_data` and `spectrum_profiles` package data
(YAML manifests / profiles).

Dev tools:

```bash
pip install -r requirements-dev.txt
pytest -q
```

---

## Certificates

Canonical directory: **`./certs`** (`CERTS_DIR` override). Required:

- `server.cert` / `server.key`
- `server-ecc.cert` / `server-ecc.key`
- `ca.cert`
- `crl/` with at least one `*.crl.pem`

Ephemeral lab certs:

```bash
python -m tools.generate_dev_certs --out ./certs --force
CERTS_DIR=./certs python -m tools.doctor
```

Or copy from the WInnForum harness `generate_fake_certs.sh` output.

---

## Databases

- Default local: SQLite (`DATABASE_URL=sqlite:///./sas_mvp.db`)
- Compose / CI: PostgreSQL 15 (`psycopg2`)

PostgreSQL integration tests:

```bash
export SAS_TEST_DATABASE_URL='postgresql+psycopg2://sas:sas_test@127.0.0.1:5432/sas'
pytest -q tests/integration/test_startup.py::test_startup_postgres_integration \
  tests/integration/test_fad_publish_postgres.py \
  tests/integration/test_cpas_multi_sas_postgres.py \
  tests/integration/test_concurrency_postgres.py
```

---

## Docker Compose

```bash
docker compose config          # no .env required
# provision ./certs first
docker compose up --build
```

Image build context excludes `.git`, venvs, DBs, test trees, and bulky NED/DPA
payloads (VERSION markers remain). See `.dockerignore`.

---

## WInnForum harness

Harness is **not** vendored. Prefer:

```bash
python -m tools.run_winnforum --dry-run --family REG
```

Full runs need certs + harness checkout; artifacts under `artifacts/winnforum/`
(gitignored). Official PASS requires versioned evidence — never invent results.

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).

WInnForum harness / reference models are separate works under Wireless Innovation
Forum licensing.
