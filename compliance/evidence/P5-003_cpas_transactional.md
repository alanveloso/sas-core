# Evidência P5-003 — CPAS transacional

**Data:** 2026-08-07  
**Branch:** `fix/p5-fad-sas-cpas`  
**Task:** P5-003 — CPAS transacional

## Defeito observado

`execute_cpas_pipeline` era uma sequência fina (sync DB → peer FAD →
`apply_peer_conflict` com commit próprio) sem:

- congelamento explícito do conjunto de grants;
- secção crítica única para decisões + novo FAD;
- auditoria de pipeline;
- garantia de rollback das terminações se a publicação FAD falhar;
- `mark_scheduled_success` só após sucesso completo.

## Alterações

- `services/cpas_service.py` — pipeline em estágios:
  1. `sync_databases`
  2. `sync_peer_fads`
  3. `freeze_snapshot` (`CpasSnapshot` com PKs ativos)
  4. `evaluate_protections` (peer CBSD / PPA / ESC; sem writes)
  5. `apply_decisions_and_generate_fad` (advisory `cpas/pipeline` +
     terminações + `create_full_activity_dump` na mesma secção)
  6. `finalize_status_audit` (`mark_scheduled_success` + `cpas_pipeline_audit`)
- `services/concurrency.py` — `acquire_cpas_pipeline_xact_lock`
- Testes: `tests/unit/test_cpas_pipeline.py`

Proteções IAP/DPA numéricas completas permanecem na Fase 6; neste task o
passo “IAP/proteções” usa as regras peer já existentes de forma determinística
sobre o snapshot congelado.

## Comandos observados

```text
env -u DATABASE_URL -u CERTS_DIR .venv/bin/pytest -q \
  tests/unit/test_cpas_pipeline.py \
  tests/unit/test_cpas_execution_mode.py \
  tests/unit/test_cpas_schedule.py \
  tests/unit/test_grant_pal_ppa.py
→ 48 passed

.venv/bin/ruff check .
→ All checks passed
```

## Escopo WInnForum

Nenhum caso oficial marcado PASS. Melhora determinismo do daily activity /
CPAS para FAD/SSS/GRA peer-conflict.

## Riscos remanescentes

- IAP agregado / DPA completo → **P6 / P5-004**.
- Sync de peers com certs ausentes falha o pipeline (fail-closed) — esperado.
- Multi-SAS edge cases (peer down, FAD inválido, CPAS concorrente) → **P5-004**.
- Preview `evaluate_protections` fora do lock é só observabilidade; decisões
  autoritativas são recomputadas sob advisory.

## Review WInnForum (pós-P5-003)

Correções high:

- terminações via `apply_grant_event(TERMINATE)` (lifecycle + `terminated`);
- `FOR UPDATE` / `lock_grant_row` ao aplicar;
- reavaliação sob `pg_advisory_xact_lock` (anti-TOCTOU);
- `result["ok"]=True` só após commit de finalize/audit.

Testes: `pytest test_cpas_pipeline + execution_mode + grant_pal_ppa + lifecycle`
→ 65 passed.
