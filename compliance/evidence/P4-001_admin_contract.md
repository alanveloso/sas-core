# Evidência P4-001 — Inventário do contrato Admin

**Data:** 2026-08-07  
**Branch:** `fix/p4-admin-api`  
**Task:** P4-001 — Gerar inventário do contrato Admin

## Defeito observado

Existia inventário só de **paths** (`services/admin_api_inventory.py`, P0-006),
sem tabela programática método↔endpoint↔schema↔estado↔consumidores exigida pelo plano.

## Alterações

- `tools/winnforum/admin_inventory.py` — extrator AST/grep:
  - `SasAdminImpl` → endpoint;
  - docstrings `SasAdminInterface` → request/response;
  - scan `testcases/` + helpers → famílias consumidoras;
  - classificação UUT (`implemented` / `thin` / `stub` / `unimplemented`).
- Artefacto: `compliance/admin_contract.yaml` (35 métodos).
- Tabela MD: `compliance/evidence/P4-001_admin_contract_table.md`.
- Testes: `tests/unit/test_admin_inventory.py`.

## Review WInnForum (2026-08-07)

Correções pós-review (crítico/alto):

- request schema `(none)` para métodos Admin sem parâmetro `request` (AST);
- classificação UUT: serviços de domínio (`persist_exclusion_zone`,
  `enable_ntia_exclusion_zones`, `get_daily_activities_completed`, …) antes de
  heurísticas `thin`/`_empty_ok`;
- testes sintéticos CI-safe (não dependem só do checkout irmão).

## Comandos observados

```text
.venv/bin/python -m tools.winnforum.admin_inventory \
  --harness-dir ../winnforum-sas-harness \
  --write compliance/admin_contract.yaml \
  --markdown compliance/evidence/P4-001_admin_contract_table.md
→ wrote … methods=35
→ stub_or_unimplemented:
    - /admin/query/propagation_and_antenna_model
    - /admin/trigger/load_dpas

env -u DATABASE_URL -u CERTS_DIR .venv/bin/pytest -q \
  tests/unit/test_admin_inventory.py tests/contract/test_admin_no_catchall.py
→ 19 passed
```

## Gaps apontados (próximas tasks)

| Endpoint | uut_status | Task |
|---|---|---|
| `/admin/trigger/load_dpas` | stub | P4-002 |
| `/admin/query/propagation_and_antenna_model` | unimplemented (501) | PAT / P7 |
| DPA act/bulk/deact, PPA, scheduled daily, DB URL | thin/partial | P4-002…P4-005 |

## Escopo WInnForum

Nenhum caso oficial marcado PASS. Inventário habilita implementação Admin real sem
hardcodes de fixture.
