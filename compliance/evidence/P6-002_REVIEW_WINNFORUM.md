# Review WInnForum — diff P6-002 HAAT geral (2026-08-07)

**Branch:** `feat/p6-protection-models`  
**Escopo:** `services/terrain/haat.py`, `fake.py`, testes HAAT gerais, matrix REG,
evidência P6-002 / gate verify 16:26.

## Achados

### Critical
Nenhum.

### High (corrigidos)

1. **`SAS_TERRAIN_DATASET_VERSION` whitespace → versão vazia** —
   `services/terrain/haat.py` (`resolve_ned_dataset_version`)  
   `if env: return env.strip()` aceitava `"   "` e devolvia `""`, corrompendo
   cache keys / identidade do dataset. Docstring também invertia a precedência
   (dizia VERSION antes do env).  
   **Fix:** só aceitar env non-empty após strip; precedência
   env → VERSION → default; testes blank-env / override / default.

### Medium (remanescentes)

1. **`CallableTerrainProvider` exportado em `services.terrain`** — helper de
   teste no pacote de produção (mesmo padrão de `DeterministicHaatProvider`);
   risco de uso acidental fora de testes se injectado via `set_haat_provider`.
2. **Listas `skip_gate_tiles` por amostra (débito não bloqueante)** — usadas
   **somente** para `pytest.skip` quando ficheiros faltam. **Não** entram em
   carregamento NED, escolha de tiles, cache key, VERSION/fingerprint nem no
   resultado HAAT (`NedTerrainProvider` resolve tiles dinamicamente). Lista
   incompleta → DX de CI (fail duro em vez de skip), não defeito de produto.
3. **Golden NED em testes** — coordenadas independentes (não REG.7), mas ainda
   amarradas a tiles Common-Data; regenerar se o DEM mudar.

### Low

1. Evidência P6-002 não marca caso oficial PASS (correto).
2. `FAMILY.REG` permanece `failing` com nota P6-002 (correto; sem claim PASS).
3. Warnings `utcnow` pré-existentes nos testes de Registration.

## Testes

```text
.venv/bin/python -m pytest -q tests/unit/test_haat_general.py
→ 15 passed
```
