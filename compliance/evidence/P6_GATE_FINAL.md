# Evidência — P6 GATE FINAL

**Data:** 2026-08-07 (~17:16–17:20 local / 20:16–20:20Z)  
**Branch:** `feat/p6-protection-models`  
**HEAD:** `d33aaf2` + working tree P6-004 (IAP/peer FAD, não commitado)  
**Comando:** `/P6-GATE` (revisão integrada; sem feature nova)  
**Artefactos:** `artifacts/winnforum/p6_gate_final_20260807T201615Z/`

## Resultado

### Fase 6 — APROVADA (produto P6-001…004)

Critério Part N: **não** há defeito restante no motor RF/IAP/proteção já
implementado que possa ser corrigido sem feature posterior.

Critério legado do plano (“famílias avançadas Release 1 verdes”) permanece
**não satisfeito** — classificado como dependência **ENV / P6-005 wiring /
P7**, não como finding **A** (defeito P6 no código entregue).

| Task | Status |
|---|---|
| P6-001 Empacotar modelos e dados | **PASS** |
| P6-002 HAAT geral | **PASS** |
| P6-003 Propagation Model API | **PASS** (local; engines oficiais ENV) |
| P6-004 IAP + peer FAD freeze | **PASS** (local; hook CPAS opcional) |
| **P6 overall** | **APROVADA** (produto) |

Nenhum fix de produção nesta corrida (nenhum finding A).

---

## Findings

### Critical
Nenhum.

### High
Nenhum.

### Medium

1. **CPAS diário não injecta `iap_points` / `iap_coupling`** —  
   `execute_cpas_pipeline` → `evaluate_cpas_protections(db, snapshot)` sem kwargs
   IAP. O motor e o hook existem e são testados; o caminho default continua só
   com regras booleanas peer. Completar wiring (points ESC/FSS/PPA/DPA +
   coupling de propagação) é **feature** (P6-005 / campanha RF), não bug do
   engine.
2. **Soft gaps** `dpa_payload` (e NED/NLCD payload sob `STRICT=false`) — markers
   OK; payloads binários/KML podem faltar. Operações que carregam engines
   oficiais falham fechado (`PropagationUnavailableError` / 503). Strict mode
   falha no doctor/startup.
3. **`suspend` no enum IAP** — débito documentado; R2-SGN-16 não emite suspend.

### Low

1. Working tree P6-004 ainda não commitado.
2. PG integration requer Docker/`SAS_TEST_DATABASE_URL` (esta corrida: Compose up → 17 passed).
3. `load_reference_engines` falha aqui por `shapely` + ITM não compilado (ENV).

---

## Parte A — Inventário P6

| Feature | Implemented in | Tests | Used by product | Official dependency | Status |
|---|---|---|---|---|---|
| protection datasets + VERSION | `protection_data/` | `test_protection_data` | doctor/startup | harness data | PASS_LOCAL |
| dataset versioning | manifest + VERSION | idem | yes | — | PASS_LOCAL |
| terrain/NED | `services/terrain/` + `data/geo/ned` | HAAT tests | registration HAAT | NED tiles | PASS_LOCAL (sample tiles) |
| HAAT | `services/terrain/haat` | haat_* + anti-hardcode | registration | NED | PASS_LOCAL |
| propagation service/engine | `services/propagation/` | `test_propagation_service` | Admin PAT | ITM/NLCD/harness | PASS_LOCAL; official ENV |
| FSS/WISP inputs | Admin inject + prop FSS fields | propagation + inject | Admin / SIQ paths | FSS DB | PASS_LOCAL (partial) |
| band plan | `spectrum_profiles` | spectrum + IAP origin | yes | — | PASS_LOCAL |
| aggregate interference | `services/iap/aggregate.py` | `test_iap_service` | via IAP hook | — | PASS_LOCAL |
| IAP / fairshare / residual / multi-channel | `services/iap/engine.py` | iap + repeatability×3 | **hook only** (not default CPAS) | IPR/MCP | PASS_LOCAL |
| local grants | CPAS + IAP | cpas/iap | yes | — | PASS_LOCAL |
| peer grants FAD | `peer_fad.py` + freeze | iap peer + PG freeze | when IAP hook used | FAD | PASS_LOCAL |
| CPAS integration (boolean peer) | `cpas_service` | cpas/multi_sas/PG | **yes (default)** | FDB | PASS_LOCAL |
| CPAS↔IAP default wiring | — | tests only with explicit kwargs | **no** | IPR/FDB RF | DEFERRED feature |
| actions on managed grants | `apply_cpas_decisions` | iap/cpas | yes | — | PASS_LOCAL |
| provenance `source_sas_id` | `GrantRfInfo` | peer converter | IAP inputs | — | PASS_LOCAL |

**Test-only (não no caminho default de produto):** invocação IAP com
`iap_points`+`iap_coupling`; `skip_gate_tiles` (só pytest.skip metadata).

---

## Parte B — Fluxo end-to-end

### Caminho default CPAS (produto hoje)

```text
freeze_cpas_snapshot (local PKs + peer FAD rows)
  → evaluate_cpas_protections (boolean peer CBSD/PPA/ESC)
  → apply_cpas_decisions (terminate)
  → FAD publish (critical section + advisory lock)
```

Sem placeholder RF: IAP simplesmente **não corre** no default.

### Caminho IAP (quando caller injecta points+coupling)

```text
frozen local grants + frozen peer FAD → GrantRfInfo
  → run_iap (residual fairshare, all channels, −1 dB)
  → CpasDecision (só grant_pk local)
  → apply_cpas_decisions (reduce_power / terminate / suspend)
```

Peers: interferência + fairshare; `source_sas_id`; **nunca** mutação local
(`grant_pk=None`, rejeição `peer/`).

Propagação Admin: engines injectáveis nos testes; produção → 503 se backend
indisponível (não inventa pathloss).

---

## Parte C — Datasets

| Dataset | Required by | Location/config | Version/fingerprint | strict | Missing behavior |
|---|---|---|---|---|---|
| ITM package | PAT / prop | `data/models/itm` + harness | VERSION 1.0.0 | marker always | engines 503 |
| NED | HAAT / ITM | `data/geo/ned` | VERSION usgs…; sample .flt present | payload soft | TerrainDataUnavailable / 503 |
| NLCD | PPA hybrid | `data/geo/nlcd` | VERSION only (no raster here) | soft | 503 on NLCD vote |
| DPA KML | DPA/FDB | `data/ntia` | VERSION; **no .kml** (gap) | soft | soft OK; strict FAIL; DPA load must not fake |
| FSS/GWBL | FDB/SIQ | `data/federal/*` | VERSION | marker | packaging only until RF campaign |
| zones/census | border/PPA | `data/geo/*` | VERSION | marker | packaging |

`STRICT=false` não mascara engines: falta de shapely/ITM/NLCD →
`PropagationUnavailableError`, não pathloss inventado.

---

## Parte D–H — Resumo de verificação local

| Check | Resultado |
|---|---|
| HAAT / REG.7 local + anti-hardcode | **PASS** (`skip_gate_tiles` ausente em produto) |
| Propagation unit + Admin 200 inject | **PASS** |
| IAP vs harness structure (residual, all-ch, −1 dB) | **PASS** local |
| Floor −137 | documentado (FAD.1 maxEirp bound) |
| Peer A–G (local/peer/N·N+1/order/immutable) | **PASS** unit |
| Action safety (None / peer/ / unknown) | **PASS** |
| `suspend` IAP | débito (não exigido R2-SGN-16) |

---

## Parte I — Concorrência PostgreSQL

Compose `db` iniciado nesta corrida; `SAS_TEST_DATABASE_URL=postgresql+psycopg2://sas:change_me@127.0.0.1:5432/sas`.

```text
pytest tests/integration/test_cpas_multi_sas_postgres.py \
       tests/integration/test_fad_publish_postgres.py \
       tests/integration/test_concurrency_postgres.py
→ 17 passed
```

Inclui freeze N vs N+1, advisory lock CPAS/FAD, row locks. P6 não removeu
garantias P5.

---

## Parte J — Regressão

| Comando | Resultado |
|---|---|
| `ruff check .` | All checks passed |
| `pytest -q` | **626 passed**, 7 skipped |
| Bundle P6 (protection/haat/prop/iap/cpas/fad/admin/matrix/doctor) | **148 passed** |
| DPA/PAL/HAAT/heartbeat-ext | **79 passed** |
| Hardcode scanners | OK (sem `_KNOWN_STREET_HAAT` / fixture IDs em produto) |
| IAP repeatability ×3 | 3× **3 passed** |

---

## Parte K — Harness oficial

Harness sibling presente. **Campanha oficial não aprovada nesta gate:**

| Case / family | Result | P6 implemented? | Failure class | Next |
|---|---|---|---|---|
| FAMILY.PAT | not PASS | Admin API yes; ITM C/NLCD no | **B** ENV (`shapely`, ITM `.so`, NLCD raster) | P7-003 / env |
| FAMILY.IPR | not PASS | engine+peer hook yes; default CPAS wiring no | **C/D** feature wiring + campaign | P6-005/P7-004 |
| FAMILY.FDB RF | not PASS | CPAS/FAD yes; EXZ/DPA/FSS RF no | **C/D** | P7 / RF campaign |
| FAMILY.PCR/PPR/FPR/GPR/MCP | not PASS | partial/absent | **C/D** | P6-005/P7 |
| FAMILY.GRA | failing rollup | IAP local | **C** harness PASS open | later |

Nenhum PASS_OFFICIAL inventado. Nenhum finding **A**.

---

## Parte L — Repetibilidade

IAP críticos ×3: estáveis (artefacto `iap_repeatability.txt`).

---

## Parte M — Matrix

Family rollups **não** marcados `passing`. Notas FDB/PAT/IPR actualizadas:
`BLOCKED_BY_ENV` / P7 (já não `BLOCKED_BY_P6` como se o motor IAP/HAAT/prop
estivesse ausente).

Evidence versionável: este ficheiro + P6-001…004 + review.

---

## Requirement rollup

| Requirement | Local evidence | Official evidence | Status | Remaining dependency |
|---|---|---|---|---|
| Protection data package | P6-001 + doctor | — | PASS_LOCAL | DPA KML payload (strict/env) |
| HAAT geral / NED | P6-002 + tests | — | PASS_LOCAL | full CONUS NED for campaigns |
| Propagation Admin API | P6-003 + unit | PAT harness | PASS_LOCAL | ITM build, shapely, NLCD |
| IAP deterministic + peer FAD | P6-004 + unit×3 | IPR harness | PASS_LOCAL | points+coupling on default CPAS; campaign |
| CPAS multi-SAS freeze | P5 + PG 17 | FAD/FDB | PASS_LOCAL | RF incumbents |
| Advanced families green | — | — | **not met** | P6-005/P7 + ENV |

---

## Próxima fase / trabalho

1. **Wiring produto:** protection points + coupling RF no CPAS default (ex-P6-005).
2. **ENV:** ITM C extension, `shapely`/deps, NLCD rasters, DPA KML, certs locais.
3. **P7:** TS-4010 deltas; PAT.2; IPR.1–8 oficiais; FDB RF EXZ/DPA/FSS/GWBL.
4. Commit working tree P6-004 quando desejado.

**Pergunta 50:** Existe defeito A corrigível sem feature nova? **NÃO.**  
→ **Fase 6 — APROVADA.**
