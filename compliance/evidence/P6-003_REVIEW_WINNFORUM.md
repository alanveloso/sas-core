# Review WInnForum — diff P6-003 Propagation API (2026-08-07)

**Branch:** `feat/p6-protection-models`  
**Escopo:** `services/propagation/*`, Admin route PAT, inventário, testes, matrix.

## Achados

### Critical
Nenhum.

### High (corrigidos)

1. **Cache de engines ignorava `SAS_NLCD_DIR`** — `engines.py`  
   `lru_cache` só em harness/terrain; mudar NLCD após o 1º load ficava stale.  
   **Fix:** cache key `(harness, terrain, nlcd)`.

2. **`ValueError` do ITM/engines → HTTP 503** — `service.py`  
   Fake SAS mapeia `ValueError` → 400; backends lançando `ValueError` eram
   engolidos como unavailable.  
   **Fix:** `_engine_call` mapeia `ValueError` → `PropagationRequestError` (400).

3. **FSS `rxAntennaGainRequired` sem campos de antena → 503** — `service.py`  
   `KeyError` em `antennaElevation` etc. caía no `except Exception`.  
   **Fix:** validar campos obrigatórios → 400; teste negativo.

### Medium (remanescentes)

1. **`sys.path` + `ConfigureTerrainDriver` globais** — estado de processo partilhado
   (padrão legado de border); risco em testes paralelos.
2. **`modelType` 1/2 não validado no ramo FSS/PPA** — alinhado ao oráculo harness;
   pedidos ambíguos ainda aceites se fss/ppa presentes.
3. **PAT oficial** ainda depende de ITM C compilado + NLCD + NED (ambiental;
   evidência não marca PASS harness).

### Low

1. Nota do inventário Admin “mutates domain tables/services” para query read-only
   (heurística de tokens).
2. Sem claim PASS oficial indevido (`FAMILY.PAT` = failing).

## Testes

```text
.venv/bin/python -m pytest -q \
  tests/unit/test_propagation_service.py \
  tests/contract/test_admin_no_catchall.py \
  tests/unit/test_admin_inventory.py
→ 34 passed

.venv/bin/ruff check services/propagation/ routes/admin_routes.py \
  tests/unit/test_propagation_service.py
→ All checks passed!
```
