# Final Feature-Complete Audit

**Data (UTC):** 2026-08-08T12:09Z
**Branch / HEAD:** `feat/p7-ts-4010` @ `b6727fc`
**Tipo:** auditoria read-only de produto (código + testes).
**Alteração deliberada:** apenas este ficheiro.
**Baseline anterior:** `compliance/evidence/P7_FINAL_AUDIT.md` (13 mandatory feature gaps).
**Pré-condição declarada:** C1–C5 COMPLETE (revalidada no código, não assumida por documento).

## Veredito

**FEATURE-COMPLETE: SIM** (produto / FT.S baseline + Rel1Ext delta adotado; sem PASS oficial de todas as famílias)

**MANDATORY FEATURE GAPS: 0**

### Final Feature Fix — FDB.2 Scheduled DPA (2026-08-08)

| Critério | Resultado |
|----------|-----------|
| Unknown scheduled dpaId rejected/fail-closed? | **YES** — `DatabaseSyncError(scheduled_dpa_unknown_dpaId:…)` |
| World fake geometry removed? | **YES** — sem `world_ring` / bbox global |
| Scheduled/manual DPA resolution consistent? | **YES** — catálogo + `_channel_in_definition` + `refresh_or_fail_closed_movelists` |
| RF failure no longer becomes valid empty movelist? | **YES** — fail-closed = grants overlapping no canal |
| Legitimate empty movelist still supported? | **YES** — refresh OK sem grants a mover |
| Partial scheduled activation impossible? | **YES** — validate-before-mutate; sync URL `rollback` on error |
| Snapshot/generation consistency preserved? | **YES** — C1–C5 freeze inalterado |
| Retry after temporary RF/ENV failure works? | **YES** — unknown→load catalogue; RF flaky→reeval |

Motivos (Q1–Q6) **após** o fix:

| Q | Pergunta | Resposta |
|---|----------|----------|
| Q1 | Algum dos 13 gaps antigos continua funcionalmente aberto? | **NO** |
| Q2 | Alguma required family com feature obrigatória faltando? | **NO** |
| Q3 | Alguma feature test-only sem production path? | **NO** |
| Q4 | Algum caminho obrigatório ainda fail-open? | **NO** |
| Q5 | Input RF/protection pode misturar snapshot N/N+1 no CPAS? | **NO** |
| Q6 | Algum FAIL atual é FAIL_PRODUCT? | **NO** |

---

## Critical

*(nenhum gap funcional obrigatório restante após FDB.2 fix)*

## High

1. **BPR.1 Rel1Ext** — baseline fail-closed OK; bind normativo Rel1Ext continua **BLOCKED_BY_SPEC/HARNESS** (não feature missing).
2. **PAT / IPR / MCP oficiais** — domínio wired; blockers **ENV** (ITM/NED/NLCD) + **NUMERIC_PARITY** (movelist MC) + harness Rel1Ext ausente.
3. **Evidence migration** — PASS case-level históricos (REG×3, SCS/SDS/SSS, FAD.1–2) em `docs/compliance/` / `artifacts/` vs rollups `FAMILY.*` ainda `failing` / paths mistos → **EVIDENCE_MIGRATION**, não feature.

## Medium

6. **SIQ sem quiet-zone** — QPR wired em Registration/Grant/pre-IAP; SIQ só aplica EXZ. Aceitável para família QPR (não SIQ); não reaberto como gap.
7. **PCR `_geometry_from_cluster` / hull** — código morto (não chamado no create path); RF unavailable → `PpaCreationError`. **functional-safe**.
8. **PRCZ** — classificação **C** (configurable / N/A dedicado) mantida.
9. **QPR configurable areas** — **CONDITIONAL**; não feature missing.
10. **PostgreSQL concurrency suite** (`tests/integration/test_concurrency_postgres.py`) — **7 skipped** (ENV `:55432` / `SAS_TEST_DATABASE_URL`); não contar como PASS.

## Low

11. Warnings `datetime.utcnow()` / Starlette lifespan.
12. Dead hull helpers em `ppa_service.py` (limpeza opcional).
13. Matrix `FAMILY.GPR/PPR/FPR` ainda `untested` apesar de implementação C3 — metadado matrix, não gap de código.

---

## Original 13 gaps reconciliation

| # | Gap | Original evidence | Fix block | Current implementation | Production wired? | Regression tests | Remaining functional issue? | Status |
|---|-----|-------------------|-----------|------------------------|-------------------|------------------|----------------------------|--------|
| 1 | Wiring IAP produção no CPAS | P7 Critical #1; MCP TEST_ONLY | C2 | `mcp_protection.resolve_iap_context` → points from freeze + `make_production_iap_coupling`; `execute_cpas_pipeline` chama evaluate **sem** kwargs | **YES** | `test_c2_cpas_iap_wiring.py`, `test_mcp_iap_dpa.py` | Oficial MCP.1 ENV | **RESOLVED** (+ CERT) |
| 2 | GPR | P7 untested / missing | C3 | GWPZ points + pre-IAP EZ + peer RF | **YES** | `test_c3_gpr_ppr_fpr.py` (`test_gpr_*`); PG GWPZ freeze | Oficial NOT_RUN | **RESOLVED** |
| 3 | PPR | P7 untested | C3 | PPA aggregate + frozen PAL freqs | **YES** | `test_c3_*` (`test_ppr_*`) | Oficial NOT_RUN | **RESOLVED** |
| 4 | FPR | P7 untested | C3 | FSS_COCHANNEL/BLOCKING + TTC + GWBL | **YES** | `test_c3_*` (`test_fpr_*`) | ITM missing → fail-closed; oficial ENV | **RESOLVED** |
| 5 | EXZ | P7 parcial | C4 | `exclusion_zone_service` + freeze + pre-IAP + SIQ/admission | **YES** | `test_c4_exz_epr.py`; PG EXZ freeze | NTIA KML **DATASET** | **RESOLVED** (+ ENV_ONLY dataset) |
| 6 | EPR | P7 parcial | C4 | ESC ProtectionPoints; Cat A 40 / Cat B 80; peer ESC | **YES** | `test_c4_*` incl. `test_esc_cat_b_40_80_production_path` | Oficial NOT_RUN | **RESOLVED** |
| 7 | QPR | P7 parcial | C5 | NRQZ + FCC A/B + TM + configurable; Reg/Grant/pre-IAP; FCC CSV fail-closed | **YES** (Reg/Grant) | `test_c5_qpr_wdb_pcr_fdb.py` | SIQ N/A; oficial NOT_RUN | **RESOLVED** |
| 8 | WDB | P7 parcial | C5 | PAL replace; CPI reconcile/revoke; checksum; reeval N/N+1 | **YES** | `test_c5_*`; **`test_postgres_wdb_pal_freeze_n_vs_n1`** | Oficial NOT_RUN | **RESOLVED** |
| 9 | PCR | P7 parcial / hull | C5 (+ RF follow-up) | `ppa_rf_contour` −96 dBm/10 MHz; no hull RF fallback; `_rfEngines` test hook only | **YES** | `test_c5_*`, `test_ppa_rf_contour.py`, `test_ppa_creation.py` | Census/ITM **DATASET/ENV** | **RESOLVED** |
| 10 | FDB residual | P7 FDB RF + sync | C2–C5 + FDB.2 fix | EXZ/FSS/GWBL/ESC freeze; scheduled via catálogo real + `refresh_or_fail_closed_movelists` | **YES** | `test_c5_*`, **`test_fdb_scheduled_dpa.py`** | Oficial NOT_RUN / ENV | **RESOLVED** |
| 11 | BPR fail-closed | P7 High #2 | C1 | `BorderPfdOutcome.UNAVAILABLE` → reject; ImportError → UNAVAILABLE | **YES** | `test_border_protection_bpr.py` | BPR.1 Rel1Ext SPEC/HARNESS | **RESOLVED** (+ CERTIFICATION_ONLY Rel1Ext) |
| 12 | CPAS-DPA fail-closed | P7 High #3 | C1 | `CpasRfEvaluationError` (sem `except: pass`) | **YES** | `test_c1_cpas_rf_safety.py` | — | **RESOLVED** |
| 13 | Freeze attrs RF | P7 High #4 | C1 | `FrozenLocalGrantRf` / peer / protection_records; evaluate usa freeze | **YES** | `test_c1_*`; PG RF/IAP/EXZ/WDB N/N+1 | Legacy hydrate se `local_grants==()` (não produzido pelo freeze atual) | **RESOLVED** |

**Production IAP requires test kwargs?** **NO**

---

## Functional gaps remaining

**NONE**

## Certification/environment gaps

| Item | Classificação |
|------|---------------|
| ITM / `reference_models` / NED / NLCD | ENV / DATASET |
| Harness Rel1Ext suite ausente @ pin | HARNESS |
| BPR.1 Rel1Ext procedure bind | SPEC / HARNESS |
| PAT.2 / IPR / MCP official campaigns | ENV + NUMERIC_PARITY + HARNESS |
| Monte-Carlo movelist parity | NUMERIC_PARITY |
| NTIA EXZ / DPA KML / census GeoJSON | DATASET |
| Official REG/SIQ/GRA/HBT/RLQ/DRG family rollups | EVIDENCE_MIGRATION (+ campanha residual) |
| Certs `./certs` / doctor soft gaps | ENV |
| PG concurrency :55432 | ENV |
| Shapely/reference PPA parity harness | ENV |

---

## Family reconciliation

| Family | Required? | Feature complete? | Product wired? | Local tests? | Official evidence? | Remaining blocker |
|--------|-----------|-------------------|----------------|--------------|--------------------|-------------------|
| REG | YES | YES | YES | YES | PASS histórico família×3 (`docs/…/P2_GATE_FINAL.md`, `artifacts/winnforum/p2_reg7/`) — matrix family ainda failing | EVIDENCE_MIGRATION |
| SIQ | YES | YES* | YES | YES | não (family) | EVIDENCE_MIGRATION / campanha (*QPR não no SIQ — OK) |
| GRA | YES | YES | YES | YES | local IAP evidence; harness aberto | EVIDENCE_MIGRATION |
| HBT | YES | YES | YES | YES | Rel1Ext local `docs/…/P7-002_hbt_rel1ext.md` | HARNESS Rel1Ext + EVIDENCE_MIGRATION |
| RLQ | YES | YES | YES | YES | não family | EVIDENCE_MIGRATION |
| DRG | YES | YES | YES | YES | não family | EVIDENCE_MIGRATION |
| SCS | YES | YES | YES | YES | case PASS P3-004 (`artifacts/…/p3_004_*`) | EVIDENCE_MIGRATION (rollup) |
| SDS | YES | YES | YES | YES | idem | EVIDENCE_MIGRATION |
| SSS | YES | YES | YES | YES | idem | EVIDENCE_MIGRATION |
| FAD | YES | YES | YES | YES | FAD.1/2 PASS (`P5_GATE_FINAL`, artifacts) | EVIDENCE_MIGRATION (rollup) |
| EXZ | YES | YES | YES | YES | C4 local only | DATASET (NTIA) + NOT_RUN |
| BPR | YES | YES (baseline) | YES | YES | não oficial | SPEC/HARNESS (BPR.1 Rel1Ext) |
| EPR | YES | YES | YES | YES | C4 local | NOT_RUN |
| QPR | YES | YES | YES | YES | C5 local | NOT_RUN / CONDITIONAL config |
| WDB | YES | YES | YES | YES | C5 + PG N/N+1 | NOT_RUN |
| FDB | YES | YES | YES | YES | parcial P5/C5 | ENV / NOT_RUN (oficial) |
| GPR | YES | YES | YES | YES | C3 local | NOT_RUN (matrix `untested` = metadado) |
| PCR | YES | YES | YES | YES | C5 local | ENV/DATASET |
| PPR | YES | YES | YES | YES | C3 local | NOT_RUN |
| FPR | YES | YES | YES | YES | C3 local | ENV/NOT_RUN |
| PAT | YES | YES (domínio) | YES | YES | local P6/P7 | ENV (ITM/NED/NLCD) + HARNESS |
| IPR | YES | YES (domínio) | YES | YES | local P7-004 | ENV + NUMERIC_PARITY + HARNESS |
| MCP | YES | YES (domínio) | YES | YES | C2 / P7-005 local | ENV + HARNESS |

\* SIQ feature-complete para escopo SIQ; quiet-zone não é requisito SIQ neste código.

---

## C3 / C4 / C5 spot checks (resumo)

| Área | Feature complete? | Production wired? | Officially validated? |
|------|-------------------|-------------------|------------------------|
| GPR | YES | YES | NO |
| PPR | YES | YES | NO |
| FPR | YES | YES | NO |
| EXZ | YES | YES | NO |
| EPR (incl. Cat B 40–80 km) | YES | YES | NO |
| QPR | YES | YES | NO |
| WDB (PG N/N+1) | YES | YES | NO |
| PCR (no hull RF fallback) | YES | YES | NO |
| FDB residual | YES | YES | NO |

### FDB requirement table

| FDB requirement/gap | Resolved by | Product path | Remaining issue |
|---------------------|-------------|--------------|-----------------|
| EXZ → CPAS | C4 | freeze + pre-IAP | Official / KML |
| Scheduled DPA channel | C5 + FDB.2 fix | `_apply_scheduled_dpa` + shared fail-closed | Oficial / ENV KML |
| FSS_BLOCKING / TTC / GWBL | C3 | IAP / pre-IAP | Official / ENV |
| Federal sync / generation | P5/C5 | `federal_db_service` + sync | Official |
| Reeval flag / next CPAS | C5 | `cpas_reevaluation` | — |
| Snapshot N/N+1 | C1–C5 | freeze | — |
| Rollback | P5 | CPAS transactional | — |

**After C2–C5 + FDB.2 fix, is there any FDB product feature still missing?** **NO**

---

## Snapshot/concurrency

| Input | Congelado no freeze CPAS? | Mistura N/N+1 possível na mesma evaluate? |
|-------|---------------------------|-------------------------------------------|
| Grants RF (freq, maxEirp, state) | YES (`FrozenLocalGrantRf`) | **NO** |
| CBSD (lat/lon, height, heightType, category, indoor, antenna) | YES | **NO** |
| Peer FAD | YES (`peer_records`) | **NO** (PG peer N vs N+1) |
| Protection records (GWPZ/PPA/PAL/FSS/GWBL/EXZ/ESC/scheduled_dpa/dpa_activation) | YES | **NO** |
| WDB/federal generation | sync bump + next freeze | In-flight N inalterado |

**Uma execução CPAS pode observar N e N+1 misturados em input que altera decisão?** **NO** (path de freeze atual).

Caveats não classificados como mix de decisão: `activate_dpa`/admission usam estado live (by design); legacy hydrate se snapshot só com PKs (não emitido pelo freeze atual).

---

## Fail-closed audit

| Path | Achado | Impacto |
|------|--------|---------|
| BPR missing `reference_models` | Deny / UNAVAILABLE | OK (C1) |
| CPAS DPA RF exception | `CpasRfEvaluationError` | OK (C1) |
| IAP coupling missing (entidade aplicável) | fail-closed C2 | OK |
| QPR FCC CSV missing | deny | OK |
| PCR RF engines missing | `withError` / no hull | OK |
| Scheduled DPA movelist RF fail | fail-closed overlapping grants (`refresh_or_fail_closed_movelists`) | OK |
| Scheduled DPA unknown dpaId | `DatabaseSyncError` / no activation | OK |
| `sas_iap_enabled=false` | skip explícito | config, não silent |
| Free Space | só perfil explícito lab | OK |

Novo fail-open obrigatório encontrado ⇒ **FEATURE-COMPLETE = NÃO** (estado pré-FDB.2).
**Pós-FDB.2:** nenhum fail-open obrigatório remanescente nos caminhos de proteção auditados.

---

## Test-only / fake dependencies

| Feature | Test injection | Production equivalent exists? | Required at runtime? | Classification |
|---------|----------------|-------------------------------|----------------------|----------------|
| IAP coupling / points | kwargs override | `make_production_iap_coupling` + freeze points | No (override only) | OK |
| PCR `_rfEngines` | body hook | `load_default_ppa_rf_engines()` | No | OK |
| DPA path_loss_fn | test stub | ITM production / fail-closed | No | OK |
| Scheduled DPA world ring | — | removido | — | OK |

---

## Hard-code scan

- `ruff check .`: **All checks passed**
- Scanner dedicado `tools/scan_hardcodes.py`: **ausente**; revisão manual + testes `test_registration_no_fixture_hardcode`
- Coordenadas FCC/TM/NRQZ: datasets normativos (não harness fixtures)
- **Achado:** world-ring em `_apply_scheduled_dpa` (ver Critical #2)
- Free Space lab: só com flag explícita de modelo

---

## Evidence migration

PASS oficiais / gates anteriores existem; **não migrar nesta auditoria**.

| Família | Onde está a evidência original | Ação necessária |
|---------|--------------------------------|-----------------|
| REG | `docs/compliance/evidence/P2_GATE_FINAL.md`, `P2_HARNESS_EXECUTION.md`, `artifacts/winnforum/p2_reg7/` | Copiar/indexar sob `compliance/evidence/` + alinhar matrix paths |
| SIQ/GRA/HBT/RLQ/DRG | P2 gate + reviews em `docs/compliance/evidence/P2-*` | Mesmo + re-run se rollup exigir |
| HBT Rel1Ext | `docs/compliance/evidence/P7-002_hbt_rel1ext.md` (excluído do git via `.git/info/exclude` em `docs/compliance/`) | Canonicalizar em `compliance/evidence/` |
| SCS/SDS/SSS | `compliance/evidence/P3-004_scs_sds_sss.md` + `artifacts/winnforum/p3_004_*`; case rows PASS na matrix | Atualizar FAMILY rollup quando política permitir |
| FAD.1/2 | `compliance/evidence/P5_GATE_FINAL.md` + artifacts p5_gate_final | Rollup FAMILY.FAD |

Classificação: **EVIDENCE_MIGRATION** apenas.

---

## PAT / IPR / MCP / BPR

| Family | Restante | FEATURE? |
|--------|----------|----------|
| PAT | ITM/NED/NLCD + tolerância oficial + harness | **NO** — ENV/HARNESS |
| IPR | campanha oficial + parity movelist + ENV | **NO** — ENV/NUMERIC_PARITY |
| MCP | campanha oficial + ENV + thresholds ref | **NO** — ENV (wiring prod OK desde C2) |
| BPR baseline | fail-open eliminado | OK |
| BPR.1 Rel1Ext | SPEC/HARNESS bind | **NO** — não feature missing |

---

## Tests

| Suite | Resultado |
|-------|-----------|
| Full pytest `pytest -q` | **806 passed, 7 skipped, 0 failed** (68.75s) |
| ruff `ruff check .` (touched) | **All checks passed** |
| mypy (CI: `mypy compliance tools`) | **Success** (20 files) |
| FDB.2 + DPA/CPAS/C1/C5 cluster | **105 passed** |
| PostgreSQL CPAS multi-SAS | **12 passed** |
| Official harness | **NOT_RUN** |

Skips: 7× concurrency PG (ENV `:55432`).

Skips relevantes (full suite = os 7 de concurrency PG): ambiente PostgreSQL dedicado ausente — **não são PASS**.

### Official harness inventory (não executado agora)

| Family | Official run status | Why not run/pass? |
|--------|---------------------|-------------------|
| REG | PASS_OFFICIAL (histórico P2) | Evidence migration |
| SIQ/GRA/HBT/RLQ/DRG | NOT_RUN / parcial histórico | Campanha + migration |
| SCS/SDS/SSS | PASS_OFFICIAL (P3-004 cases) | Rollup migration |
| FAD.1/2 | PASS_OFFICIAL | Rollup migration |
| EXZ/EPR/QPR/WDB/GPR/PPR/FPR/PCR | NOT_RUN | Campanha + datasets |
| FDB | NOT_RUN | ENV / campanha oficial |
| BPR.1 Rel1Ext | BLOCKED_BY_SPEC | Procedure bind |
| PAT/IPR/MCP Rel1Ext | BLOCKED_BY_ENV / HARNESS | ITM + suite Rel1Ext |

Nenhum **FAIL_PRODUCT** observado nesta corrida (oficiais não reexecutados).

---

## Final answers

**MANDATORY FEATURE GAPS: 0**

**FEATURE-COMPLETE: SIM**

### Para CERTIFICATION-READY

- Provisionar ITM/NED/NLCD/`reference_models` + datasets NTIA/census.
- Harness Rel1Ext suite + campanhas oficiais PAT/IPR/MCP/BPR.1.
- Paridade numérica movelist / thresholds de referência.
- Migrar evidence histórica para `compliance/evidence/` e alinhar matrix.
- Cert provisioning / doctor / KML oficial.
- PASS oficial das famílias required (não só feature-complete).

---

## A. FUNCTIONAL GAPS

**NONE**

## B. CERTIFICATION-ONLY / ENV GAPS

ITM/NED/NLCD; reference_models; Rel1Ext suite; Monte-Carlo parity; official harness runs; evidence migration; certs; KML/census oficiais; BPR.1 SPEC bind; shapely/reference PPA harness parity.

---

## Final Feature Fix Review — FDB.2 Scheduled DPA

### Unknown DPA handling

Validate-before-mutate against `get_catalogue_definition` + `_channel_in_definition` (same as `activate_dpa`). Unknown → `DatabaseSyncError`; no catalogue mutation; no activation.

### RF/movelist failure semantics

Shared `refresh_or_fail_closed_movelists`: on `PropagationUnavailableError` / terrain / domain errors → overlapping grants on movelist (strategy B, same as `activate_dpa`). Successful empty movelist preserved when no grants need move.

### Transactionality

`sync_injected_database_urls` already `rollback`s per URL on exception. Validation precedes deletes/upserts. `_upsert_activation` flushes under `autoflush=False` to avoid duplicate activation keys.

### Snapshot/generation

Unchanged from C1–C5; successful sync bumps dpa generation and marks reevaluation.

### Tests

- Unit FDB.2: `tests/unit/test_fdb_scheduled_dpa.py` (A–L)
- C5 scheduled cases updated
- Regression cluster DPA/CPAS/C1/C5: 105 passed
- PostgreSQL CPAS: 12 passed
- Full pytest / ruff / mypy: ver secção Tests abaixo (atualizada no fix)

*Fix FDB.2 alterou código de produto + testes; não marcou families `passing`; sem commit.*