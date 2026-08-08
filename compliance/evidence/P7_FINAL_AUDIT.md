# Auditoria P7 Final — Baseline + Rel1Ext

**Data:** 2026-08-08  
**Branch / HEAD:** `feat/p7-ts-4010` @ `60a329d`  
**Harness pin (checkout local):** `winnforum-sas-harness` @ `928c3150adf7b31e53a96b695bf1fbdd3284ecb2`  
**Tipo:** auditoria read-only (sem alteração de produto)

## Veredito

**FEATURE-COMPLETE: NÃO**

Motivos objectivos (Q1–Q4):

| Q | Resposta | Evidência |
|---|----------|-----------|
| Q1 Features obrigatórias em falta? | **SIM** (parcial) | Famílias GPR/PPR/FPR `untested` / `implementation: []`; PCR parcial; domínio FPR/GPR ausente na matrix |
| Q2 Implementado mas não ligado ao path real? | **SIM** | Motor IAP + builder de pontos existem; `execute_cpas_pipeline` **nunca** passa `iap_coupling` → IAP/MCP multi-constraint só via kwargs de teste |
| Q3 Fail-open onde deveria fail-closed? | **SIM** | `border_protection` `ImportError` → `return False` (autoriza); CPAS `except …: pass` em falha DPA (não termina) |
| Q4 Só passa com injection de teste? | **SIM** | `iap_coupling` / `iap_points` injectados em `test_iap_service` / `test_mcp_iap_dpa`; path diário não os constrói |

## Critical

1. **IAP/MCP não wired no CPAS de produção** — `services/cpas_service.py` `execute_cpas_pipeline` chama `evaluate_cpas_protections(db, snapshot)` sem coupling; IAP só corre se `iap_coupling is not None`. Classificação: **TEST_ONLY_OR_PARTIAL** / gap de wiring obrigatório para MCP.1 e campanhas FDB/IPR RF.

## High

2. **Border fail-open sem `reference_models`** — `services/border_protection.py` L58–59: `ImportError` → não viola → grant autorizado.
3. **CPAS DPA fail-open em excepção** — `evaluate_cpas_protections` L355–357: erros de propagação/terrain engolidos sem terminações DPA (enquanto `evaluate_protected_channel` interno é fail-closed).
4. **Snapshot membership N + RF live** — freeze só `active_grant_pks` + peer JSON; `_local_grant_to_rf_info` / `collect_active_dpa_grants(grant_pks=)` re-lê `max_eirp`, frequências e `registration_json` vivos. Classificação auditoria §10: **C** (risco TOCTOU face a update de registo concurrente; lock CPAS ≠ lock CBSD).

## Medium

5. **Suite Rel1Ext ausente no harness fixado** — `testcases/` @ `928c315`: 0 ficheiros/conteúdo Rel1Ext/4010 → campanha oficial Rel1Ext **BLOCKED_BY_HARNESS**.
6. **ITM / `reference_models` / NED / NLCD** — não disponíveis neste ENV → PAT.2/IPR oficiais **BLOCKED_BY_ENV** (domínio local existe).
7. **Evidence Rel1Ext HBT.13** aponta `docs/compliance/evidence/P7-002_hbt_rel1ext.md` (gitignored via `.git/info/exclude`) — não é evidence canónica persistida em `compliance/evidence/`.
8. **`IapThresholdProfile`** — defaults locais documentados; não prova tabelas oficiais.
9. **Movelist greedy ≠ Monte-Carlo/keep-move oficial** — gap de **paridade/certificação**, não requisito normativo SAS claramente separado do procedimento harness (mantido como certification gap).
10. **BPR.1 Rel1Ext `blocked`** — `REL1Ext-R1-SGN-09`; notes: deferred até bind procedimento↔harness. Classificação: **BLOCKED_BY_SPEC/HARNESS** (baseline Arrangement R existe).
11. **FDB.1–6/8** — sync/heartbeat/generation locais; RF campaign oficial **BLOCKED_BY_ENV**; sem case-level rows na matrix (só `FAMILY.FDB`).
12. **Doctor** — `./certs` ausente; `protection_data` soft gap `dpa_payload`.
13. **Ruff E731** — `tests/unit/test_propagation_service.py:198` (pré-existente; não falha pytest).

## Low

14. Warnings `datetime.utcnow()` / Starlette lifespan.
15. Evidence P7-001…003 ainda sob `docs/compliance/evidence/` (excluído do git); P7-004/005 em `compliance/evidence/`.
16. Matrix family rollups REG/SIQ/GRA/… `failing` apesar de PASS case-level SCS/SDS/SSS/FAD — rollup ≠ case PASS (esperado).

## Mandatory features missing (prioridade)

1. **Wiring de produção IAP**: provider de coupling (ITM/path-loss) + construção de `ProtectionPoint` no `execute_cpas_pipeline` / daily CPAS (MCP.1 / FDB RF).
2. **Domínio GPR / PPR / FPR** (matrix `untested` / implementation vazia) se o escopo adoptado inclui essas famílias baseline.
3. **Fail-closed BPR** quando `reference_models`/ITM border indisponível (hoje autoriza).
4. **Fail-closed CPAS** quando avaliação DPA levanta erro de propagação (hoje `pass`).
5. **Congelar inputs RF** no snapshot CPAS (ou provar imutabilidade sob o mesmo controlo) — residual High TOCTOU.

## Implemented but not officially validated

| Área | Domínio local | Oficial |
|------|---------------|---------|
| HBT Rel1Ext TxExpire / neighborhood | P7-002 | FAILING / harness Rel1Ext ausente |
| PAT.2 Type-3 compose | P7-003 | FAILING / ITM+datasets |
| IPR DPA protection + CPAS movelist | P7-004 | FAILING / harness+ITM |
| MCP joint IAP+DPA (tests + freeze) | P7-005 | FAILING / coupling prod + harness |
| SCS/SDS/SSS / FAD.1–2 | PASS case-level | Evidence P3/P5 |
| IAP engine fairshare | P6-004 | hook only no daily |

## Environment / dataset blockers

| Item | Estado |
|------|--------|
| Harness Rel1Ext suite | Ausente @ `928c315` |
| ITM / `wf_itm` / `reference_models` | Ausentes |
| NED / NLCD | Campanha PAT/IPR |
| DPA KML vendored | Soft gap `dpa_payload` |
| Certs `./certs` | Doctor FAIL |
| PostgreSQL concurrency suite | Skip sem `SAS_TEST_DATABASE_URL` / :55432 (CPAS/FAD PG OK via docker efémero) |

## Baseline reconciliation (resumo)

- **58** case-level `passing` (SCS/SDS/SSS/FAD.1–2) com evidence.
- Famílias protocolares REG/SIQ/GRA/HBT/RLQ/DRG: implementação wired + testes locais; rollup `failing` (sem PASS oficial de família completa).
- RF avançadas EXZ/BPR/EPR/QPR/WDB/FDB/PCR/PAT/IPR/MCP: parciais / failing.
- GPR/PPR/FPR: **ausentes ou quase** (`untested`, `implementation: []`).

## Rel1Ext reconciliation

- Delta **19/19** preenchida; `passing=0`, `failing=18`, `blocked=1` (BPR.1).
- P7-001…005 domínio local concluído no HEAD.
- Nenhum PASS oficial Rel1Ext; suite harness Rel1Ext **NOT_RUN** / **BLOCKED_BY_HARNESS**.

## Official family status

| Family | Baseline status | Rel1Ext status | Product implementation | Product wiring | Official evidence | Remaining blocker |
|--------|-----------------|----------------|------------------------|----------------|-------------------|-------------------|
| REG | failing (family) | — | sim | sim | não (family) | campanha oficial |
| SIQ | failing | — | sim | sim | não | RF/PAL parcial + campanha |
| GRA | failing | — | sim + IAP engine | grant sim; IAP daily não | não | IAP wiring + campanha |
| HBT | failing | HBT.* failing (HBT.13 evidence docs/) | Rel1Ext TxExpire | sim | não oficial | harness Rel1Ext |
| RLQ/DRG | failing | — | sim | sim | não | campanha |
| SCS/SDS/SSS | family failing; cases PASS | — | sim | sim | P3-004 | — |
| FAD | family failing; FAD.1/2 PASS | — | sim | sim | P5_GATE_FINAL | — |
| EXZ | failing | — | parcial | parcial | não | RF + ENV |
| **BPR** | failing | **BPR.1 blocked** | baseline Arrangement R | sim (fail-open w/o models) | não | SPEC/HARNESS bind + fail-open |
| EPR/QPR/WDB | failing | — | parcial | parcial | não | domínio + campanha |
| **FDB** | failing | (baseline) | sync/HB/generation | daily sim; RF IAP não | não | ENV + IAP wiring |
| GPR | untested | — | **não** | não | não | **feature missing** |
| PCR | failing | — | parcial PAL/admin | parcial | não | PPA/PAL incompleto |
| PPR | untested | — | **não** | não | não | **feature missing** |
| FPR | untested | — | **não** | não | não | **feature missing** |
| **PAT** | failing | PAT.2 failing | Rel1Ext Type-3 | Admin API + DPA path | não | ITM/NED/NLCD + harness |
| **IPR** | failing | IPR.1–8 failing | DPA protection | grant/HBT/CPAS | não | ITM + harness + MC parity |
| **MCP** | failing | MCP.1 failing | joint domain + tests | **IAP daily unwired** | P7-005_mcp (local) | **wiring coupling** + harness |

## Testes executados (reais)

| Comando | Resultado |
|---------|-----------|
| `ruff check .` | **FAIL** E731 `tests/unit/test_propagation_service.py:198` |
| `pytest -q` | **686 passed, 7 skipped** |
| Skips | 7× `test_concurrency_postgres.py` — PostgreSQL :55432 / `SAS_TEST_DATABASE_URL` ausente |
| `pytest` CPAS+FAD postgres | **11 passed** |
| Hardcode/HAAT unit | OK (registration + haat) |
| Doctor | FAIL certs; soft gap `dpa_payload` |
| Harness Rel1Ext | **NOT_RUN** (suite ausente) |

Artefactos: `artifacts/winnforum/p7_final_audit_20260808T014928Z/`.

## Classification cheat-sheet (P7 tasks)

| Task | Classificação dominante |
|------|-------------------------|
| P7-001 delta | IMPLEMENTED_AND_WIRED (matrix) |
| P7-002 HBT | IMPLEMENTED_NOT_OFFICIALLY_VALIDATED (+ ENV harness) |
| P7-003 PAT.2 | IMPLEMENTED_NOT_OFFICIALLY_VALIDATED + ENV_BLOCKED (ITM) |
| P7-004 IPR | IMPLEMENTED_NOT_OFFICIALLY_VALIDATED + ENV + certification parity (movelist) |
| P7-005 MCP | **TEST_ONLY_OR_PARTIAL** no daily IAP; domínio local wired para DPA/freeze |

## Próximos passos (não feitos nesta auditoria)

1. Wiring production IAP coupling + points no CPAS.  
2. Fechar fail-open BPR/CPAS-DPA.  
3. Congelar RF attrs no snapshot (ou provar imutabilidade).  
4. Domínio GPR/PPR/FPR se no escopo.  
5. Evidence canónica para P7-001…003; campanha Rel1Ext quando suite+ITM existirem.  
6. Só então P8 hardening / certification-ready.
