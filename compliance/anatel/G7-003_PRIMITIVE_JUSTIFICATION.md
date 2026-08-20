# G7-003 — Justificação de primitives (reuso ≥2 regimes)

Somente gaps `GAP_PRIMITIVE` da matriz ANATEL SLP 3700–3800 que passam o teste de reuso. Sem branching de país no Coordination Core. Sem DSL no YAML.

## Implementado nesta task

| Mechanism id | Axis | Gap BR | Reuso (não-BR) | Primitive |
| --- | --- | --- | --- | --- |
| `duplex_mode` | spectrum | BR-SLP-3700-002 (TDD) | Alemanha 3.7–3.8 / EU WBB-LMP / várias locais TDD | `DuplexModeRequirement` |
| `max_assignment_bandwidth` | spectrum | BR-SLP-3700-011 (≤50 MHz outdoor) | UK Shared Access / Canada NCLL / licenças locais com teto de BW | `MaxAssignmentBandwidth` |
| `antenna_height_limit` | power | BR-SLP-3700-010 (≤6 m outdoor) | UK low/medium power height practice / campus locais com teto AGL | `AntennaHeightLimit` |
| `forbidden_device_roles` | access | BR-SLP-3700-006 (anti-repetidor) | Regimes que proíbem booster/repeater / tipologias de estação | `ForbiddenDeviceRoles` |

Cada um é um contrato no `builtin_mechanism_registry`, parâmetros fechados no Profile v2 (`constraints[]`), e checagem pura em `primitives/` (sem ORM, sem `if brasil`).

## Adiado (não implementar agora)

| Gap | Motivo |
| --- | --- |
| BR-SLP-3700-017 (prioridade indoor vs outdoor) | Resolução de conflito de coexistência / PROCESS; falta segundo regime claro com a mesma semântica antes de congelar primitive |
| BR-SLP-3700-018 (sync TDD) | Já `PROCESS` — operacional entre operadores, não admission mechanism |
| ACLR/OBUE | `OUT_OF_SCOPE_EQUIP` |
| BDTA / EMSAT geometrias | `GAP_DATA` → G7-004 |

## O que esta task não faz

- Não inventa datasets brasileiros.
- Não liga evaluation ao request path CBRS v1.
- Não adiciona `if profile_id == "br_anatel_*"` no core.
