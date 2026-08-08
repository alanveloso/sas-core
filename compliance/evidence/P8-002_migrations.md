# P8-002 — Banco e migrações

**Date:** 2026-08-08
**Status:** DONE (local)
**Official harness:** N/A (hardening; no family PASS claim)

## Scope

Plano bullets:

- Alembic;
- timezone-aware UTC;
- constraints e índices;
- testes de upgrade/downgrade;
- backup/restore;
- isolamento transacional documentado.

## Implementation

| Piece | Location |
|-------|----------|
| Alembic | `alembic.ini`, `alembic/env.py`, `alembic/versions/20260808_0001_initial_schema.py` |
| Apply helpers | `services/migrations.py` (`upgrade_head` / `downgrade_base` / `stamp_head` / `apply_schema`) |
| `init_db` / `reset_db` | `database.py` → Alembic head (legacy column patches kept for stamped DBs) |
| UTC datetimes | `models/types.UtcDateTime` + `DateTime(timezone=True)` columns; `services.clock.ensure_utc` |
| Backup/restore | `services/db_backup.py` (SQLite file copy; logical JSON for other dialects) |
| Isolation notes | Module docstring in `services/migrations.py` + `database.py` |
| Fast pytest path | `SAS_SCHEMA_VIA_CREATE_ALL=1` (setdefault in `tests/conftest.py`): `create_all` + stamp |

## Acceptance commands

```bash
pytest -q tests/unit/test_p8_002_migrations.py
pytest -q tests/unit
ruff check alembic database.py models services/migrations.py services/db_backup.py
```

**Observed (2026-08-08):** `test_p8_002_migrations` includes password-URL regression;
full suite after gate fix **823 passed, 7 skipped**; ruff/mypy OK.

## Non-claims

- No WInnForum family marked `passing`.
- Gate verify found a real product bug (`str(engine.url)` password redaction);
  fixed via `database_url_for_alembic`. Remaining concurrency-PG skips are ENV
  (`SAS_TEST_DATABASE_URL` / `:55432`).
- Models must stay aligned with the Alembic initial revision when using the create_all fast path.
- Logical JSON backup/restore for non-SQLite is implemented but only SQLite
  file-copy roundtrip is covered by automated tests.
