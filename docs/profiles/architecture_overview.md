# Visão de arquitetura para authors (G11-003)

Este documento é o mapa de extensão da plataforma. Não substitui o freeze em
`.cursor/generalization-plan/` nem claims oficiais WInnForum.

## Camadas

```text
Profile YAML (reference | custom)
    │  seleciona mechanisms + declara capabilities
    ▼
Primitive / Mechanism catalog (registry)
    │
    ├── Device / Network adapters (plugins)
    ├── Protocol adapters (plugins)
    ├── Data providers (plugins)
    └── RF models (plugins)

Coordination Core
    snapshot → evaluate → decision → apply
    fail-closed · ProfileContext por decisão
```

O **Coordination Core** não deve ganhar `if country` / `if profile`. Novo regime
com comportamento já conhecido → YAML + dados + testes. Comportamento novo →
plugin ou primitive registrada, depois YAML.

## Profile = composição completa

A banda vive **dentro** do profile (`spectrum.ranges` / channelization). Não há
`BandProfile` separado. Reference e custom usam o **mesmo schema**; a diferença é
`metadata.status` (`reference` | `custom`) e proveniência — não capacidade.

`based_on` é metadado/proveniência apenas. **Não** há herança/merge YAML no v2.

## ProfileContext (decisão)

Toda decisão genérica carrega identidade imutável: `profile_id`, `profile_version`,
`profile_hash`, `dataset_versions`, `mechanism_versions`, `rf_provenance`.
Isso não é um singleton global de processo.

## Trust de load (G11-001)

| Tier | Como carrega |
| --- | --- |
| `builtin_v2` | `load_profile_v2(id)` sob `spectrum_profiles/profiles/v2/` |
| `operator_explicit` | path YAML do operador (doctor / custom) |

IDs de profile e nomes de plugin são tokens `[a-z][a-z0-9_]*` (sem path-like).
YAML usa `yaml.safe_load` — configuração, não código executável.

## Profiles de referência neste repositório

| Id | Papel |
| --- | --- |
| `cbrs_winnforum` | Design / request-path CBRS (RF-heavy, `dynamic_lease`) |
| `br_anatel_slp_3700` | Primeiro regime novo (YAML + primitives) |
| `eu_elsa` | Network / availability-centric (não fake CBSD/Grant) |
| `us_tvws_15_711` | Holdout §15.711 — representação **CONDITIONAL** (evidência; path de query DB ainda gated) |

Challenge-set (UK SA, CA NCLL, EU WBB-LMP, DE local, AFC) foi auditado em G9;
nem todos têm profile operacional completo. `query_assignment` permanece
`OPEN_FOR_LATER_DESIGN` (G9-006) — não invente Grant/SIQ como query universal.

## O que o YAML não faz

- `if` / `else`, loops, expressões Python
- listar nomes de vendor/adapter como regra principal (use capabilities)
- registrar mechanisms via entry point (`spectrum_access.mechanisms` é **reservado**;
  mechanisms vivem no `MechanismRegistry`)

Ver também: [reference_and_custom.md](reference_and_custom.md),
[creating_plugins.md](../plugins/creating_plugins.md).
