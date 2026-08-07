# Review WInnForum — diff P5-004 Multi-SAS (2026-08-07)

**Branch:** `fix/p5-fad-sas-cpas`  
**Escopo:** working tree P5-004 (`fad_client_service`, `PeerSas.last_fad_generation`,
`cpas_service` peer freeze, `test_multi_sas`, PG integration, matrix/evidence)

## Achados

### Critical
Nenhum.

### High (corrigidos)

1. **Skip idempotente só por `generationDateTime`** — `services/fad_client_service.py`  
   Skip após match do timestamp deixava wipe local irrecuperável e aceitava
   reutilização do mesmo timestamp com payload diferente.  
   **Fix:** `peer_generation_already_applied` exige timestamp **e** fingerprint
   `(record_type, record_id, data_json)` idêntico; wipe/conteúdo alterado → re-apply.

2. **Concorrência CPAS só por mock** (follow-up)  
   **Fix:** `tests/integration/test_cpas_multi_sas_postgres.py` com PostgreSQL real,
   sessões/processos independentes, sem mock de
   `acquire_cpas_pipeline_xact_lock` / `pg_advisory_xact_lock` / `lock_grant_row` /
   commit-rollback principais.

3. **Freeze de peer incompleto** — avaliação lia `PeerFadRecord` live (N→N+1 mid-run
   podia alterar decisões).  
   **Fix:** `CpasSnapshot.peer_records` capturado em `freeze_cpas_snapshot` (+
   `db.flush()` porque `SessionLocal.autoflush=False`); `evaluate_cpas_protections`
   usa o conjunto congelado.

### Medium (remanescentes)

1. Matrix FAD/FDB aponta `evidence` principalmente a P5-004 (P5-002/P5-003 ficam
   em ficheiros próprios).
2. `last_fad_generation` VARCHAR(32) alinhado a `FadDump.generation_datetime`.

### Low

1. Skip FAD client ainda descarrega a geração completa antes de decidir.
2. Warnings `utcnow` pré-existentes.

## Follow-up PostgreSQL (concorrência)

| Item | Valor |
|---|---|
| PostgreSQL | `SAS_TEST_DATABASE_URL` ou `postgresql+psycopg2://sas:sas_test@127.0.0.1:55432/sas`, senão Docker efémero `postgres:15-alpine` |
| Conexões / workers | 2 sessões SQLAlchemy independentes (threads); + 2 processos OS no teste multiprocess |
| Advisory lock | `acquire_cpas_pipeline_xact_lock` → `pg_advisory_xact_lock`; bloqueio peer com `lock_timeout`; `pg_locks` granted observado |
| Snapshot N→N+1 | Run congela peer N; publisher concorrente grava N+1; run termina com decisão de N; próximo run vê N+1 |
| Rollback | Falha injectada em `create_full_activity_dump` sob lock; rollback liberta lock; peer completa; sem `cpas_completed` no run falhado |
| RLock-only | Teste multiprocess falharia/inconsistente se só existisse RLock process-local (workers sem memória partilhada) |

## Testes

```text
.venv/bin/python -m pytest -q \
  tests/unit/test_multi_sas.py \
  tests/unit/test_fad_client.py \
  tests/unit/test_cpas_pipeline.py \
  tests/integration/test_cpas_multi_sas_postgres.py
→ 36 passed

.venv/bin/python -m pytest -q tests/integration/test_cpas_multi_sas_postgres.py
→ 6 passed

.venv/bin/ruff check .
→ All checks passed!
```
