# Evidência P6-003 — Propagation Model API

**Data:** 2026-08-07  
**Branch:** `feat/p6-protection-models`  
**Task:** P6-003 — Propagation Model API

## Defeito observado

`POST /admin/query/propagation_and_antenna_model` devolvia HTTP 501; não havia
serviço genérico alinhado ao oráculo PAT (FSS ITM, PPA hybrid, DPA ITM+P.2108+8 dB).

## Alterações

- `services/propagation/` — `compute_propagation_and_antenna_model` espelha
  harness `computePropagationAntennaModel` / `computePropagationDpa`;
  `PropagationEngines` injectável; `load_reference_engines` carrega
  `reference_models` do sibling `winnforum-sas-harness`.
- `routes/admin_routes.py` — 200 + JSON; 400 request inválido; 503 engines
  indisponíveis (sem fake PASS).
- Inventário Admin: removido de `EXPLICIT_UNIMPLEMENTED_*`; classificado
  `implemented`.
- Testes: `tests/unit/test_propagation_service.py` + contract admin.

Tolerâncias oficiais (documentadas para campanhas PAT, não assertadas aqui como
PASS harness):

| Campo | Critério harness |
|---|---|
| `pathlossDb` | UUT &lt; ref + 1.0 dB |
| `txAntennaGainDbi` / `rxAntennaGainDbi` | UUT ≥ ref − 0.2 dBi |

## Comandos observados

```text
.venv/bin/python -m pytest -q \
  tests/unit/test_propagation_service.py \
  tests/contract/test_admin_no_catchall.py \
  tests/unit/test_admin_inventory.py \
  tests/unit/test_compliance_matrix.py
→ 43 passed

.venv/bin/ruff check services/propagation/ routes/admin_routes.py \
  services/admin_api_inventory.py tools/winnforum/admin_inventory.py \
  tests/unit/test_propagation_service.py tests/contract/test_admin_no_catchall.py
→ All checks passed!
```

## Escopo WInnForum

API Admin PAT implementada localmente. **Nenhum** caso `WINNF.FT.S.PAT.*`
marcado PASS (requer extensão ITM compilada, NLCD, NED e campanha harness —
P6-005 / P7-003). Matrix: `FAMILY.PAT` → `failing` (já não `blocked` por 501).

## Riscos remanescentes

- Produção real: `python setup.py build_ext -i` no ITM do harness; `numpy`;
  `SAS_HARNESS_DIR` / `SAS_TERRAIN_DIR` / `SAS_NLCD_DIR`.
- Border protection ainda usa path harness incorreto/legado (fora deste task).
- IAP / aggregate → **P6-004**.
