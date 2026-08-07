# Evidência P4-003 — PPA creation Admin

**Data:** 2026-08-07  
**Branch:** `fix/p4-admin-api`  
**Task:** P4-003 — Implementar PPA creation

## Defeito observado

- `create_ppa` só verificava existência de `palIds` e devolvia ID fabricado `zone/ppa/mvp/.../0`;
- ignorava `cbsdIds` e `providedContour`;
- não persistia ZoneData para FAD;
- `get_ppa_status` default `{completed:true, withError:false}` mascarava “ainda não iniciado”.

## Alterações

- `services/ppa_service.py` — validação PAL (known/VALID/holder), cluster (registo + holder),
  geometria (`providedContour` ou convex hull do cluster), service area quando PAL traz
  GeoJSON, overlap com PPA existente, ID normativo `zone/ppa/{admin}/{palId}/{uuid}`,
  persistência `kind=zone`, status real (`completed:false` → `true`; `withError` só em erro);
- Rotas Admin delegam ao serviço;
- Testes: `tests/unit/test_ppa_creation.py`.

## Review WInnForum (2026-08-07)

Correções pós-review (alto):

- exceções inesperadas fecham status com `withError=true` (não deixam `completed:false` eterno);
- rejeição de `palIds`/`cbsdIds` duplicados;
- `licenseStatus` deve ser explicitamente `VALID` (sem default permissivo);
- testes negativos: missing cbsdIds, duplicates, contour inválido, PAL EXPIRED.

## Comandos observados

```text
env -u DATABASE_URL -u CERTS_DIR .venv/bin/pytest -q \
  tests/unit/test_ppa_creation.py \
  tests/unit/test_grant_pal_ppa.py \
  tests/unit/test_admin_inventory.py
→ 44 passed

python -m tools.winnforum.admin_inventory …
→ TriggerPpaCreation / GetPpaCreationStatus = implemented
→ stub_or_unimplemented: só PAT 501
```

## Escopo WInnForum

Nenhum caso oficial marcado PASS. Habilita PCR/WDB Admin path sem stub de criação.
Geometria RF de referência (contorno max vs NTIA model) e census county oficial
completos ficam para fases de dados/RF quando o dataset county estiver provisionado.

## Riscos remanescentes

- Sem `license.licenseArea` no PAL, service-area/census não é aplicada;
- Contorno gerado = hull do cluster (não modelo RF PCR.1);
- Overlap geométrico por vértices (falso negativo possível em polígonos entrelaçados);
- `InjectClusterList` permanece thin (não usado por PCR helpers).
