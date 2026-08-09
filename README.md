# Spectrum Access System

Implementation of a **Spectrum Access System (SAS)** for the CBRS band
(3550–3700 MHz), aimed at interoperability with
[WInnForum](https://github.com/Wireless-Innovation-Forum/CBRS-SAS-Test-Harness)
test harness suites (WINNF-TS-0061 and related).

Python ≥3.11 · FastAPI · SQLAlchemy · Pydantic · Celery · Uvicorn (mTLS)

---

## Interfaces

| Interface | Prefix | Auth | Purpose |
|-----------|--------|------|---------|
| **CBSD ↔ SAS** | `/v1.2` | mTLS (CBSD) | Registration, SIQ, Grant, Heartbeat, Relinquishment, Deregistration |
| **SAS ↔ SAS** | `/v1.3` | mTLS (peer SAS) | Full Activity Dump (FAD) |
| **Admin** | `/admin` | mTLS (harness / operator) | Injects, CPAS, sync, PAT query |

TLS listeners:

- `https://0.0.0.0:9000` — RSA
- `https://0.0.0.0:9001` — ECDSA (SAS↔SAS ECC / SSS)

---

## Repository layout

| Path | Role |
|------|------|
| `routes/` | CBSD, SAS↔SAS, Admin HTTP |
| `services/` | Domain logic (lifecycle, FAD, CPAS, IAP, propagation, terrain, …) |
| `protection_data/` | Versioned RF / protection dataset manifests |
| `spectrum_profiles/` | Band plan / profile YAML |
| `data/` | Dataset root (`VERSION` markers; large payloads often gitignored) |
| `compliance/` | Compliance matrix and versioned evidence |
| `tools/` | Doctor, certs, WInnForum runner, campaign helpers |
| `alembic/` | Database migrations |

---

## Install

```bash
git clone git@github.com:alanveloso/spectrum-access-system.git
cd spectrum-access-system

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade 'pip==25.2'
pip install -r requirements.lock.txt
pip install -e .

python -m tools.doctor
```

Editable install includes `protection_data` and `spectrum_profiles` package data.

Development dependencies and tests:

```bash
pip install -r requirements-dev.txt
pytest -q
```

---

## Certificates

Canonical directory: **`./certs`** (override with `CERTS_DIR`). Required files:

- `server.cert` / `server.key`
- `server-ecc.cert` / `server-ecc.key`
- `ca.cert`
- `crl/` with at least one `*.crl.pem`

Generate ephemeral lab certificates:

```bash
python -m tools.generate_dev_certs --out ./certs --force
CERTS_DIR=./certs python -m tools.doctor
```

Alternatively, copy output from the WInnForum harness `generate_fake_certs.sh`.

---

## Databases

- Local default: SQLite (`DATABASE_URL=sqlite:///./sas_mvp.db`)
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
# Provision ./certs first
docker compose config
docker compose up --build
```

The image build context excludes `.git`, virtualenvs, databases, test trees, and
bulky NED/DPA payloads (`VERSION` markers remain). See `.dockerignore`.

---

## WInnForum harness

The official harness is **not** vendored. Local dry-run:

```bash
python -m tools.run_winnforum --dry-run --family REG
```

Full campaigns need certificates and a harness checkout. Artifacts are written
under `artifacts/winnforum/` (gitignored). Official PASS claims require stored
evidence under `compliance/evidence/` — see `compliance/matrix.yaml`.

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).

WInnForum harness and reference models are separate works under Wireless
Innovation Forum licensing.
