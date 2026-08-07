# Evidência P6-002 — HAAT geral

**Data:** 2026-08-07  
**Branch:** `feat/p6-protection-models`  
**Task:** P6-002 — HAAT geral

## Defeito observado

O plano exigia remoção de `_KNOWN_STREET_HAAT_M` e cálculo para **qualquer**
coordenada, com amostras independentes e tolerâncias documentadas. A tabela de
rua já estava ausente (P2-REG7); faltavam amostras gerais + constantes de
tolerância além do único golden REG.7.

## Alterações

- `services/terrain/haat.py` — documenta algoritmo genérico; exporta
  `HAAT_SYNTHETIC_ABS_TOL_M` (`1e-9`), `HAAT_NED_ABS_TOL_M` (`1e-3`),
  `HAAT_REPEATABILITY_ABS_TOL_M` (`0`); `resolve_ned_dataset_version` (env /
  `VERSION` / default).
- `services/terrain/fake.py` — `CallableTerrainProvider` para terreno analítico.
- `tests/unit/test_haat_general.py` — plano/pico/AGL≡AMSL/repetibilidade + 3
  amostras NED independentes (não REG.7 device_8).
- `data/geo/ned/README.md` — tabela de tolerâncias.

Sem hardcodes de produção; coordenadas de amostra só em testes.

## Amostras NED independentes (referência 2026-08-07)

| Site | lat/lon | height AGL | elev / norm / HAAT (m) | skip_gate_tiles (diagnóstico) |
|---|---|---|---|---|
| dc_alt | 38.95, −77.25 | 5 | 106.300 / 12.390 / 17.390 | n39–40 w077–078 |
| ks_n39w098 | 38.75, −97.5 | 4 | 398.190 / 8.225 / 12.225 | n39w098 |
| ks_n40w101 | 39.75, −100.5 | 3 | 839.484 / 18.743 / 21.743 | n40w101 |
| boundary | 38.995, −77.005 | 4 | 59.533 / −12.364 / −8.364 | n39–40 w077–078 |

Tolerância NED: `abs ≤ 1e-3` m. AGL e AMSL equivalentes bit-a-bit nos samples.

### Débito não bloqueante — `skip_gate_tiles`

A coluna/lista de tiles nos testes é **apenas** metadata para `pytest.skip`
quando o ficheiro está ausente. **Não** participa de:

- carregamento do terreno;
- escolha de tiles (feita em runtime por `NedTerrainProvider` via `(lat, lon)`);
- cache key / `dataset_version`;
- fingerprint / `VERSION`;
- reprodutibilidade do HAAT.

Produção: tile vizinho em falta → `TerrainDataUnavailable` (fail-closed).
Listas incompletas afetam só a UX do skip em CI.

## Comandos observados

```text
.venv/bin/python -m pytest -q \
  tests/unit/test_haat_general.py \
  tests/unit/test_haat_registration.py \
  tests/unit/test_registration_no_fixture_hardcode.py \
  tests/unit/test_compliance_matrix.py
→ 39 passed

.venv/bin/ruff check services/terrain/ \
  tests/unit/test_haat_general.py tests/unit/test_haat_registration.py
→ All checks passed!
```

## Escopo WInnForum

Suporte local a REG.7 / Cat A outdoor HAAT genérico. Nenhum caso oficial marcado
PASS neste task (REG.7 harness já exercitado em fases anteriores quando tiles
existem). Matrix: nota em `FAMILY.REG`.

## Riscos remanescentes

- `skip_gate_tiles`: débito não bloqueante (só `pytest.skip`); ver secção acima.
- Propagation / path-loss completo fica em **P6-003**.
