# Evidência P4-005 — Data injection contracts

**Data:** 2026-08-07  
**Branch:** `fix/p4-admin-api`  
**Task:** P4-005 — Data injection contracts

## Defeito observado

Os endpoints Admin `injectdata/{zone,fss,wisp,database_url,esc_zone,cluster_list,sas_admin}`
apenas faziam `_store_injection` (append cego em `AdminInjectedData`), sem
validação de schema, upsert por chave, generation ID, nem validação de URL/checksum.
O inventário classificava-os como `thin`; o gate da fase 4 falhava
`GATE_all_admin_mutate_verifiably`.

## Alterações

- `services/data_injection_service.py` — contratos de injeção:
  - validação tipada (FSS lat/lon/freq ordenada; WISP record+zone; zone geometry/usage;
    `database_url` type allowlist + HTTP(S); sas_admin `record.id`;
    esc_zone/cluster_list exigem identidade);
  - upsert por chave natural (id / type|url / userId…);
  - `injection_generation` (+ bump FSS em `federal_sync_meta`);
  - checksum SHA-1 opcional verificado no sync FSS/GWBL;
  - batch helper com um único commit (`commit=False` nos writers);
  - `reset_db` limpa tudo (drop/recreate).
- Rotas Admin passam a chamar `persist_*` / `upsert_*` (tokens de inventário).
- `database_sync_service` rejeita corpo com checksum divergente.
- Testes: `tests/unit/test_data_injection.py`.
- Review WInnForum: WISP sem crash em `deploymentParam` inválido; ESC admin
  transação única flag+audit; evidência alinhada ao gate 12:54.

## Comandos observados

```text
env -u DATABASE_URL -u CERTS_DIR .venv/bin/pytest -q \
  tests/unit/test_data_injection.py \
  tests/unit/test_esc_meas_admin.py \
  tests/unit/test_admin_inventory.py \
  tests/contract/test_admin_no_catchall.py
→ 50 passed

.venv/bin/python -m tools.winnforum.admin_inventory …
→ implemented=34  unimplemented=1 (PAT)  thin=0
```

## Escopo WInnForum

Nenhum caso oficial marcado PASS. Desbloqueia consumidores FDB/WDB/IPR/SIQ/HBT/FPR
que dependem de injects verificáveis. Famílias afetadas (consumidores Admin):
FDB, IPR, WDB, FPR, HBT, MCP, SIQ, GRA, FAD, PCR.

## Riscos remanescentes

- PAT `query/propagation_and_antenna_model` permanece 501 (P7).
- Validação Admin inject é fail-soft (HTTP 200 sem persistir payload inválido),
  alinhada ao harness.
- URL inject permite hosts locais (necessário ao harness); SSRF endurecido fica em P5 FAD client.
- Checksum opcional ainda não aplicado a sync PAL/CPI/EXZ no mesmo path.
