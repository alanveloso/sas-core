# Evidência P4-002 — DPA lifecycle Admin

**Data:** 2026-08-07  
**Branch:** `fix/p4-admin-api`  
**Task:** P4-002 — Implementar DPA lifecycle

## Defeito observado

- `/admin/trigger/load_dpas` retornava HTTP 200 vazio sem carregar catálogo;
- ativação sobrescrevia uma única flag `dpa_active` (sem multi-canal / multi-DPA);
- bulk `activate=True` era no-op; deactivation limpava **todas** as ativações;
- sem geometria/neighborhood, movelist, auditoria ou validação de `dpaId`/canal.

## Alterações

- `services/dpa_service.py` — parse KML NTIA-style, catálogo persistido (`dpa_catalogue`),
  ativações por `(dpaId, frequencyRange)`, movelist vazio por ativação, audit log,
  bulk/selectivo, reset DPA, overlap helper para heartbeat.
- Rotas Admin em `routes/admin_routes.py` delegam ao serviço (resposta ainda empty 200).
- `services/heartbeat_service.py` usa `grant_overlaps_active_dpa`.
- Resolução de KML: `SAS_DPA_KML_PATHS` → `data/ntia/` → sibling harness.
- `data/ntia/README.md` + gitignore dos blobs KML.
- Testes: `tests/unit/test_dpa_lifecycle.py`.
- Inventário: `load_dpas` / act / bulk / deact → `implemented` (PAT 501 permanece).

## Review WInnForum (2026-08-07)

Correções pós-review (alto):

- ativação exige canal **exactamente** na lista do catálogo (rejeita spans 20 MHz / OOB);
- bulk exige `activate: bool` explícito (`None`/ausente não desativa tudo);
- `resolve_dpa_kml_paths([])` não faz fallback silencioso;
- load/bulk inserem ativações sem scan O(n²);
- `sources` no catálogo guardam só basename (sem path absoluto da máquina).

## Comandos observados

```text
env -u DATABASE_URL -u CERTS_DIR .venv/bin/pytest -q \
  tests/unit/test_dpa_lifecycle.py \
  tests/unit/test_heartbeat_protocol.py \
  tests/unit/test_admin_inventory.py \
  tests/contract/test_admin_no_catchall.py
→ 38 passed

# Smoke catálogo real (sibling harness KML, sem hardcode de fixture IDs no código)
→ catalogueSize=107 activations=1180

.venv/bin/python -m tools.winnforum.admin_inventory \
  --harness-dir ../winnforum-sas-harness \
  --write compliance/admin_contract.yaml
→ stub_or_unimplemented:
    - /admin/query/propagation_and_antenna_model
```

## Escopo WInnForum

Nenhum caso oficial marcado PASS nesta task. Habilita GRA/HBT/IPR/MCP Admin DPA
sem stub; proteção geométrica/IAP completa permanece nas fases RF (P6/P7).

## Riscos remanescentes

- Movelist ainda vazio (preenchimento em IPR/IAP);
- Overlap heartbeat continua só por frequência (neighborhood geo → P7);
- KML não vendored: ambiente precisa `SAS_DPA_KML_PATHS` ou sibling/data/ntia.
