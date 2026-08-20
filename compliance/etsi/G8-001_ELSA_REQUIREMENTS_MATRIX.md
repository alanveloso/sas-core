# Matriz de requisitos ETSI eLSA (G8-001)

**Target profile:** `eu_elsa` → futuro `spectrum_profiles/profiles/v2/eu_elsa.yaml` (fatia G8).  
**Instrumentos primários:** ETSI TS 103 652-1/2/3 (eLSA Parts 1–3).  
**Formato:** colunas de `.cursor/generalization-plan/11_TRACEABILITY.md`.  
**Fonte machine-readable:** `compliance/etsi/elsa_requirements_matrix.yaml`.

Esta matriz **não** é conformidade ETSI, implementação de protocolo eLSA1, nem autorização para operar. É rastreabilidade de engenharia com foco em **network-centric** e **availability constraints**, para impedir overfit em CBSD/Grant.

## Fontes

| Source ID | Autoridade | Documento | Uso |
| --- | --- | --- | --- |
| `ETSI_TS_103_652_1` | ETSI | TS 103 652-1 V1.1.1 | Requisitos funcionais (GEN/INC/GRA) |
| `ETSI_TS_103_652_2` | ETSI | TS 103 652-2 V1.1.1 | Arquitetura eLC/eLR, eLSRAI, procedimentos |
| `ETSI_TS_103_652_3` | ETSI | TS 103 652-3 V1.1.2 | eLSRAI IEs / protocolo eLSA1 |
| `ARCH_G0_005` | Projeto | Freeze D6/D8/D9/D11/D12 | Consumidor canônico; lease; incumbents; preemption |
| `ARCH_G0_004` | Projeto | Stress-test CBRS+BR+LSA | Hipóteses a confirmar/rejeitar |
| `PLAN_SOURCES_ELSA` | Projeto | SOURCES.md | Índice da série 103 652 |

## Status legend

| Status | Significado |
| --- | --- |
| `PLANNED_YAML` | Expressável com mechanisms/capabilities já no catálogo (profile futuro) |
| `GAP_PRIMITIVE` | Exige primitive nova reutilizável — tipicamente `availability_constraint` (G8-003) |
| `GAP_DATA` | Precisa packs/dados de entidades (incumbents/zonas) sem inventar geometrias |
| `ADAPTER_REQUIRED` | Protocol/network adapter (G8-002 / G8-004), fora do Coordination Core |
| `PROCESS` | Regra de processo/framework nacional; não vira DSL no YAML |
| `OUT_OF_SCOPE_PROTOCOL` | Codificação completa eLSA1 / IEs — só na fatia de adapter |
| `OUT_OF_SCOPE_MFCN` | Mapeamento eLC→MFCN (eLSA4) fora do core |
| `MATRIX_TEST` | Coberto pelo teste de integridade desta matriz |

## Foco da task

- **Network-centric:** consumidor = VSP/MFCN via eLC; sem fake CBSD/Grant no domínio genérico.
- **Availability-centric:** eLSRAI / validity / scheduled+on-demand / incumbent return = expiry, não preemption.

## Matriz

| Requirement ID | Source | Section/item | Requirement summary | Profile field/mechanism | Code/plugin | Test | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ELSA-001 | ETSI_TS_103_652_2 | 4.2.1 eLC/eLR | Consumidor = MFCN/VSP via eLC; eLR armazena recursos e disponibilidade | representação network/managed-consumer (D6) | `ManagedNetworkAdapter` (G8-002); eLSA1→G8-004 | test_g8_002 | ADAPTER_REQUIRED |
| ELSA-002 | ARCH_G0_005 | D6/D8 | Não promover Grant/CBSD como substantivos universais | `dynamic_lease` / `fixed_window` sem Grant no core | — | MATRIX_TEST | PLANNED_YAML |
| ELSA-003 | ETSI_TS_103_652_2 | 4.2.2 eLSA1 | Interface eLR↔eLC para eLSRAI + ack | protocol adapter | G8-004 | TBD:G8-004 | ADAPTER_REQUIRED |
| ELSA-004 | ETSI_TS_103_652_2 | 4.2.2 eLSA4 | eLC mapeia eLSRAI → config de rádio MFCN | — | adapter MFCN | — | OUT_OF_SCOPE_MFCN |
| ELSA-005 | ARCH_G0_005 | D11 | Incumbents ≠ access class | protection + availability sources | — | MATRIX_TEST | PLANNED_YAML |
| ELSA-006 | ETSI_TS_103_652_1 | R-FUNC-GEN-01 | Sharing / licensing / leasing (t×espaço×freq) | `frequency_ranges`, `authorized_area`, lease/window | — | TBD:G8-005 | PLANNED_YAML |
| ELSA-007 | ETSI_TS_103_652_1 | R-FUNC-GEN-03 | Troca de disponibilidade e mudanças no tempo; conexão permanente opcional | `availability_constraint` (defer) | — | TBD:G8-003 | GAP_PRIMITIVE |
| ELSA-008 | ETSI_TS_103_652_1 | R-FUNC-GEN-04 | Múltiplos licensees sem contention entre MFCNs | escopos por rede; não GAA-contention | — | MATRIX_TEST | PROCESS |
| ELSA-009 | ETSI_TS_103_652_1 | R-FUNC-GEN-05 | Um MFCN × múltiplos incumbents/lessors | multi-source protection/availability | data packs | TBD:G8-003 | GAP_DATA |
| ELSA-010 | ETSI_TS_103_652_1 | R-FUNC-GEN-06 / 5.4 | Sharing Framework nacional | metadata/constraints derivados; não hardcode no core | — | MATRIX_TEST | PROCESS |
| ELSA-011 | ETSI_TS_103_652_1 | R-FUNC-GEN-11 | Modo scheduled de disponibilidade | `fixed_window` + `availability_constraint` | — | TBD:G8-003 | GAP_PRIMITIVE |
| ELSA-012 | ETSI_TS_103_652_1 | R-FUNC-GEN-12 | Modo on-demand / evacuação | `snapshot_evaluate_apply` + availability | — | TBD:G8-003 | GAP_PRIMITIVE |
| ELSA-013 | ETSI_TS_103_652_2 | 5.4.2 validity | eLSRAI com validity time; expirado ⇒ não aplicável | validity / fail-closed | — | TBD:G8-003 | GAP_PRIMITIVE |
| ELSA-014 | ETSI_TS_103_652_3 | 4.4 | Zonas allowance/restriction/protection/exclusion (espaço×freq×rádio×tempo) | geo + power + exclusões; gap em restriction model | — | TBD:G8-003 | GAP_PRIMITIVE |
| ELSA-015 | ETSI_TS_103_652_1 | R-FUNC-GEN-17 / 5.6 | Allowance zones geográficas | `authorized_area` + ranges | — | TBD:G8-005 | PLANNED_YAML |
| ELSA-016 | ETSI_TS_103_652_1 | R-FUNC-INC-02 | Traduzir requisitos do incumbent → disponibilidade para o MFCN | derivation → `availability_constraint` | — | TBD:G8-003 | GAP_PRIMITIVE |
| ELSA-017 | ETSI_TS_103_652_1 | R-FUNC-INC-03 | Mudança de uso/proteção do incumbent atualiza disponibilidade | event reevaluation | — | TBD:G8-003 | GAP_PRIMITIVE |
| ELSA-018 | ARCH_G0_005 | D12 | Retorno do incumbent = expiry de availability, **não** preemption | forbid preemption for this semantics | — | MATRIX_TEST | GAP_PRIMITIVE |
| ELSA-019 | ETSI_TS_103_652_1 | R-FUNC-INC-05 | Constraints de transmissão (zonas + EIRP + freq + tempo) | `max_power`, areas, exclusões, windows | — | TBD:G8-005 | PLANNED_YAML |
| ELSA-020 | ETSI_TS_103_652_1 | R-FUNC-INC-06 | Constraints de interferência recebida (protection zone) | `single_link_threshold`; `rf.required` opcional | RF port | TBD:G8-005 | PLANNED_YAML |
| ELSA-021 | ETSI_TS_103_652_1 | R-FUNC-GRA-05 | Ack ponta-a-ponta de mudanças de disponibilidade | — | eLSA1 confirmation | TBD:G8-004 | ADAPTER_REQUIRED |
| ELSA-022 | ETSI_TS_103_652_1 | GEN-03 / DOM | Sem heartbeat CBRS-like como keep-alive genérico | forbid `dynamic_lease`/`periodic` as keepalive | — | MATRIX_TEST | PLANNED_YAML |
| ELSA-023 | ETSI_TS_103_652_2 | 5.5 | Request/Notification/Confirmation de eLSRAI | — | protocol adapter | TBD:G8-004 | OUT_OF_SCOPE_PROTOCOL |
| ELSA-024 | ETSI_TS_103_652_1 | 5.6 | Sem coordenação automática de interferência entre vizinhos MFCN | não exigir IAP/fairshare no profile eLSA | — | MATRIX_TEST | PROCESS |
| ELSA-025 | ARCH_G0_004 | rf.required | RF gated por profile; fail-closed só se `rf.required` | `rf.required` | RF port | MATRIX_TEST | PLANNED_YAML |
| ELSA-026 | ETSI_TS_103_652_1 | R-FUNC-GEN-14 | Verificar inputs; rejeitar mudanças inválidas (fail closed) | `snapshot_evaluate_apply` + validation | — | MATRIX_TEST | PLANNED_YAML |
| ELSA-027 | PLAN_SOURCES_ELSA | SOURCES | `eu_elsa` ↔ série TS 103 652; input para G8-002…005 | `metadata.id=eu_elsa` | — | MATRIX_TEST | MATRIX_TEST |

## Implicações para G0 (revisão)

| Hipótese G0-004/G0-005 | Veredito após matriz |
| --- | --- |
| `availability_constraint` first-class | **Confirmada** — ainda `GAP_PRIMITIVE` até G8-003 |
| Incumbent return = preemption | **Rejeitada** — expiry (ELSA-018 / D12) |
| Consumidor = device/CBSD | **Rejeitada** — network/eLC (ELSA-001) |
| Grid de canalização obrigatório | **Não exigido** pelo eLSA citado |
| Heartbeat no lease genérico | **Rejeitada** (ELSA-022) |

## Fora desta task (G8-001)

- Representação canônica network/managed-consumer: **G8-002**.
- Primitive `availability_constraint`: **G8-003**.
- Adapter/protocolo eLSA1: **G8-004**.
- Suite multi-regime LSA+CBRS+BR: **G8-005**.
- Não alterar Coordination Core nem o path CBRS v1.
