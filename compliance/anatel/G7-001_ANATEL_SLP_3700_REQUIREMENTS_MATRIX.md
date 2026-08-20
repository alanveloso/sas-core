# Matriz de requisitos ANATEL — SLP 3700–3800 MHz (G7-001)

**Target profile:** `br_anatel_slp_3700` → `spectrum_profiles/profiles/v2/br_anatel_slp_3700.yaml` (G7-002).  
**Instrumento primário:** Ato nº 915, de 1º de fevereiro de 2024 — Anexo, item **5.13** (faixa 3.700–3.800 MHz).  
**URL oficial:** https://informacoes.anatel.gov.br/legislacao/atos-de-requisitos-tecnicos-de-gestao-do-espectro/2024/1920-ato-915  
**Formato:** colunas de `.cursor/generalization-plan/11_TRACEABILITY.md`.  
**Fonte machine-readable:** `compliance/anatel/slp_3700_3800_requirements_matrix.yaml`.

Esta matriz **não** é evidência de conformidade ANATEL nem autorização para operar. É rastreabilidade de engenharia para um reference profile futuro. Valores numéricos só entram no YAML quando o item exato abaixo for citado.

## Fontes

| Source ID | Autoridade | Documento | Uso |
| --- | --- | --- | --- |
| `ATO_915_2024` | ANATEL | Ato nº 915/2024 (Anexo) | Requisitos técnicos/operacionais SLP terrestres; §5.13 = 3700–3800 MHz |
| `ATO_915_2024_ART` | ANATEL | Ato nº 915/2024 arts. 1º–3º | Aprovação do Anexo; remissão 4.5.2 (SIC) aos limites do Ato 915 para 3700–3800 |
| `PLAN_SOURCES_REDES` | ANATEL / plano | Redes Privativas (SOURCES.md) | Contexto de faixa típica SLP 3700–3800; não substitui o Ato |
| `ARCH_D9_D10` | Projeto | G0-005 D9/D10 | Naming `static_authorization`; regime classless omite `access` |

## Status legend

| Status | Significado |
| --- | --- |
| `PLANNED_YAML` | Expressável no Profile v2 com mechanisms/capabilities já no catálogo (G7-002) |
| `GAP_DATA` | Precisa provider/dados BR (G7-004); sem inventar datasets |
| `GAP_PRIMITIVE` | Pode exigir primitive nova — só se reutilizável (G7-003); revisar antes |
| `OUT_OF_SCOPE_EQUIP` | Máscara/certificação de equipamento (ACLR/OBUE/espúrios); fora do Coordination Core |
| `PROCESS` | Processo de outorga/coordenação entre partes; não é decisão automática de grant CBRS-like |
| `MATRIX_TEST` | Coberto pelo teste de integridade desta matriz (G7-001) |

## Matriz

| Requirement ID | Source | Section/item | Requirement summary | Profile field/mechanism | Code/plugin | Test | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BR-SLP-3700-001 | ATO_915_2024 | 5.13.1 / Tabela XII | Faixa operacional 3.700–3.800 MHz; blocos com F1=3.700 MHz, BW=10 MHz, N=10 | `spectrum.ranges`; `spectrum.channelization.mechanism=fixed_width_channelization` (width_hz=10e6, origin_hz=3700e6) | — | TBD:G7-005 | PLANNED_YAML |
| BR-SLP-3700-002 | ATO_915_2024 | 5.13.2 | Duplexação por divisão de tempo (TDD) na subfaixa | `constraints.duplex_mode=tdd` | — | test_g7_003 | PLANNED_YAML |
| BR-SLP-3700-003 | ATO_915_2024 | 5.13.3-I | e.i.r.p. PSD máx. base/nodal indoor: 30 dBm/10 MHz | `power.mechanism=rule_table` (regra indoor) | — | TBD:G7-005 | PLANNED_YAML |
| BR-SLP-3700-004 | ATO_915_2024 | 5.13.3-II | e.i.r.p. PSD máx. base/nodal outdoor: 26 dBm/10 MHz | `power.mechanism=rule_table` (regra outdoor) | — | TBD:G7-005 | PLANNED_YAML |
| BR-SLP-3700-005 | ATO_915_2024 | 5.13.3-III | e.i.r.p. máx. móvel/terminal: 26 dBm (+2 dB tol. conformidade) | `power.mechanism=rule_table` (classe terminal); tolerância de certificação fora do core | — | TBD:G7-005 | PLANNED_YAML |
| BR-SLP-3700-006 | ATO_915_2024 | 5.13.3.1 | Proibido reforçador/repetidor na faixa | `constraints.forbidden_device_roles` | — | test_g7_003 | PLANNED_YAML |
| BR-SLP-3700-007 | ATO_915_2024 | 5.13.4–5.13.11 | ACLR, OBUE e espúrios (Tabelas XII-a/b/c) | — (certificação de equipamento) | — | — | OUT_OF_SCOPE_EQUIP |
| BR-SLP-3700-008 | ATO_915_2024 | 5.13.12 | Autorização limitada aos limites geográficos da propriedade; cobertura só na propriedade | `authorization.mechanism=static_authorization`; `geography.mechanism=authorized_area` (ou footprint da licença) | station/license device adapter | TBD:G7-005 | PLANNED_YAML |
| BR-SLP-3700-009 | ATO_915_2024 | 5.13.13 | Preferência indoor; outdoor com área de cobertura limitada | `power` indoor/outdoor rules; geography area limits | — | TBD:G7-005 | PLANNED_YAML |
| BR-SLP-3700-010 | ATO_915_2024 | 5.13.14 | Altura máx. antena outdoor base/nodal: 6 m AGL | `constraints.antenna_height_limit` | — | test_g7_003 | PLANNED_YAML |
| BR-SLP-3700-011 | ATO_915_2024 | 5.13.15 | Outdoor: largura consignada ≤ 50 MHz | `constraints.max_assignment_bandwidth` (+ channelization 10 MHz) | — | test_g7_003 | PLANNED_YAML |
| BR-SLP-3700-012 | ATO_915_2024 | 5.13.16 | Parâmetros de estações no BDTA públicos para coordenação prévia | `data.required_capabilities` (ex.: `protected_entities`, `boundaries`) | data provider BDTA/bundle BR | TBD:G7-004 | GAP_DATA |
| BR-SLP-3700-013 | ATO_915_2024 | 5.13.17.1 | Proteger EMSAT (Ilha do Governador) de emissões terrestres | `protection` + `exclusion_zone` / entidade protegida | data provider + geography | TBD:G7-004/G7-005 | GAP_DATA |
| BR-SLP-3700-014 | ATO_915_2024 | 5.13.17.3–5 / Tabela XII-d | Separação mínima / acordo de coordenação estação terrestre ↔ terrena | `protection.mechanisms` incl. `distance_exclusion`; acordos = PROCESS | data provider estações terrenas | TBD:G7-004/G7-005 | GAP_DATA |
| BR-SLP-3700-015 | ATO_915_2024 | 5.13.17.6–7 | Terrena entrante / mitigação / faixa de guarda | PROCESS + possíveis exclusões/guard bands no profile | — | TBD:G7-005 | PROCESS |
| BR-SLP-3700-016 | ATO_915_2024 | 5.13.18.2 / Tabela XII-e | Separação entre estações terrestres (200 m / 500 m etc.) | `distance_exclusion` (+ sync/guard = PROCESS) | data provider estações terrestres | TBD:G7-004/G7-005 | GAP_DATA |
| BR-SLP-3700-017 | ATO_915_2024 | 5.13.18.4 | Em conflito outdoor vs indoor comprovado, prioridade à indoor | regra de coexistência / policy (não `ordered_classes` de acesso dinâmico) | — | TBD:G7-005 | GAP_PRIMITIVE |
| BR-SLP-3700-018 | ATO_915_2024 | 5.13.18.5 | Sincronismo TDD comum entre redes vizinhas quando necessário | PROCESS / parâmetro operacional; não grant heartbeat | — | — | PROCESS |
| BR-SLP-3700-019 | ARCH_D9_D10 | D9 | Autorização tipo licença local de longa validade, sem refresh periódico tipo CBRS | `authorization.mechanism=static_authorization` | — | TBD:G7-005 | PLANNED_YAML |
| BR-SLP-3700-020 | ARCH_D9_D10 | D10 | Regime sem classes/prioridades dinâmicas Incumbent/PAL/GAA | **omitir** seção `access` (não usar `ordered_classes[1]`) | — | TBD:G7-005 | PLANNED_YAML |
| BR-SLP-3700-021 | ATO_915_2024 + G0-004 | — | Sem protocolo de heartbeat / `transmitExpireTime` como condição genérica de lease | não selecionar `dynamic_lease` / `periodic` como keep-alive obrigatório | — | TBD:G7-005 | PLANNED_YAML |
| BR-SLP-3700-022 | ATO_915_2024_ART | Art. 1º / Art. 3º (4.5.2) | Limites de potência/emissões/condições adicionais 3700–3800 remeten ao Ato 915 | reforço de fonte; implementação via linhas 001–018 | — | MATRIX_TEST | MATRIX_TEST |
| BR-SLP-3700-023 | PLAN_SOURCES_REDES | Redes Privativas | Contexto: 3700–3800 entre faixas típicas SLP | `metadata.references` no profile futuro | — | MATRIX_TEST | MATRIX_TEST |

## Implicações para G0 (revisão)

| Hipótese G0-004 | Veredito após matriz |
| --- | --- |
| Faixa 3700–3800 | **Confirmada** (5.13 / Tabela XII) |
| `static_authorization` primário | **Confirmada** (5.13.12 + D9) |
| Omitir `access` (classless) | **Mantida** (sem tiers dinâmicos no Ato §5.13) |
| Sem heartbeat CBRS-like | **Mantida** |
| RF IAP-style obrigatório | **Não imposto** pelo §5.13; RF de path-loss agregado é opcional; máscaras ACLR = equipamento |
| Potência só “por licença” sem números | **Atualizar:** números explícitos em 5.13.3 I–III |

## Fora desta task (G7-001)

- Profile YAML: entregue em **G7-002** (`br_anatel_slp_3700.yaml`).
- Não implementar primitives novas (G7-003) nem providers BR (G7-004).
- Não alterar Coordination Core nem o path CBRS v1.
