# Evidência P6-001 — Empacotar modelos e dados

**Data:** 2026-08-07  
**Branch:** `feat/p6-protection-models`  
**Task:** P6-001 — Empacotar modelos e dados

## Defeito observado

Não existia um pacote versionado que declarasse ITM, NED, NLCD, antenas, DPA,
FSS/GWBL, zones e census; o doctor/startup não falhavam quando datasets
obrigatórios estavam ausentes.

## Alterações

- `protection_data/` — schema Pydantic + loader/validação + manifest
  `cbrs_winnforum_protection` v1.0.0
- `data/**/VERSION` — marcadores de revisão por slot (binários continuam fora do git)
- `config.py` — `SAS_PROTECTION_DATA_BUNDLE` / `_ROOT` / `_STRICT`
- `tools/doctor.py` — finding `protection_data`
- `main.py` — `assert_protection_data_ready` no startup / entrypoint
- Testes: `tests/unit/test_protection_data.py`

Payloads NED (`.flt`) e DPA (`.kml`) são `payload_optional_unless_strict`:
falham doctor/startup apenas com `SAS_PROTECTION_DATA_STRICT=true`.
Marcadores `VERSION` são sempre obrigatórios.

Não implementa algoritmos ITM/IAP (P6-003+).

## Comandos observados

```text
.venv/bin/python -m pytest -q \
  tests/unit/test_protection_data.py \
  tests/security/test_certs_and_doctor.py
→ 19 passed

env -u DATABASE_URL -u CERTS_DIR .venv/bin/pytest -q tests/integration/test_startup.py
→ 6 passed

.venv/bin/ruff check protection_data/ config.py tools/doctor.py main.py \
  tests/unit/test_protection_data.py
→ All checks passed!
```

## Escopo WInnForum

Nenhum caso oficial marcado PASS. Pré-requisito de packaging para PAT/IPR/FDB
(P6). Matrix: notas em famílias RF avançadas.

## Riscos remanescentes

- Binários NED/DPA ainda não provisionados no checkout → strict=false por omissão.
- ITM/antenna/census são marcadores; cálculo chega em P6-002…P6-004.
- Próximo: **P6-002** HAAT geral.
