# G7-004 — Providers de dados (sem inventar regulatório)

## Entrega

- Entry points `bundle_protected_entities` / `bundle_boundaries` → `providers.operator_feature_bundle`
- Template + README em `data/geo/anatel/` (sem geometrias oficiais commitadas)
- Env `SPECTRUM_ACCESS_FEATURE_BUNDLE` ou ficheiro local gitignored
- `fetch()` fail-closed se bundle ausente ou secção vazia

## Não feito (de propósito)

- Coordenadas EMSAT / estações terrenas / BDTA inventadas
- Branching `if brasil` no Coordination Core
- Ligação completa distance_exclusion↔bundle no request path (G7-005)

Ver `data/geo/anatel/README.md`.
