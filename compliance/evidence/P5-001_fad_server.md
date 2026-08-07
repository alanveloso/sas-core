# Evidência P5-001 — FAD server completo

**Data:** 2026-08-07  
**Branch:** `fix/p5-fad-sas-cpas`  
**Task:** P5-001 — FAD server completo

## Defeito observado

O gerador FAD já emitia manifest + 4 tipos de ficheiro, mas:

- usava `datetime.utcnow()` (naive);
- não paginava `recordData` (risco de dumps enormes / limite schema 101 ficheiros);
- não supersedia dumps `ready` anteriores (risco de misturar gerações);
- faltavam testes de checksum/size/timestamp/IDs e evidência P5.

## Alterações

- `services/fad_service.py`:
  - `utc_now` / timestamps UTC `…Z` partilhados no snapshot;
  - paginação por `SAS_FAD_MAX_RECORDS_PER_FILE` (default 500);
  - sempre ≥1 ficheiro por `cbsd|zone|esc_sensor|coordination`;
  - checksum SHA-1 e `size` = bytes UTF-8 do corpo; assert interno;
  - `ready=False` nos dumps anteriores antes de commit do novo;
  - `verify_ready_dump_integrity` para ops/testes;
  - IDs `cbsd/{fcc}/{sha1(serial)}`, `zone/ppa/{admin}/…`, `esc_sensor/{admin}/…`.
- Testes: `tests/unit/test_fad_server.py`.
- `.env.example`: `SAS_FAD_MAX_RECORDS_PER_FILE`.
- Matrix: `FAMILY.FAD` aponta evidência/testes (status ainda `failing` até PASS oficial).

## Comandos observados

```text
env -u DATABASE_URL -u CERTS_DIR .venv/bin/pytest -q tests/unit/test_fad_server.py
→ 9 passed

env -u DATABASE_URL -u CERTS_DIR .venv/bin/pytest -q \
  tests/unit/test_fad_server.py \
  tests/unit/test_cpas_execution_mode.py \
  tests/unit/test_cpas_schedule.py \
  tests/contract/test_admin_no_catchall.py
→ 37 passed

.venv/bin/ruff check services/fad_service.py tests/unit/test_fad_server.py
→ All checks passed
```

## Escopo WInnForum

Nenhum caso oficial FAD marcado PASS. Habilita FAD.1–FAD.n a obterem dump
coerente via `/v1.3/dump` + ficheiros; coordination permanece envelope vazio
até eventos multi-SAS (P5-004).

## Riscos remanescentes

- Coordination sem registos de domínio (só envelope) — P5-004.
- Grants com `terminated=true` ainda excluídos do dump (só grants ativos).
- Cliente FAD peer / SSRF / purge → **P5-002**.
- `fad_public_base` default localhost exige config no harness remoto.

## Review WInnForum (pós-P5-001)

- CBSD só `REGISTERED`; zonas com `terminated=true` omitidas.
- Semântica B: `ready` = snapshot completo (históricos OK); `published` = current atómico.
- Coordenação PostgreSQL: `pg_advisory_xact_lock` + índice único parcial `published`.
- RLock process-local só auxiliar SQLite; evidência multi-worker em PG.
- Follow-up: `docs/compliance/evidence/P5-001_FAD_SERVER_REVIEW.md`.
