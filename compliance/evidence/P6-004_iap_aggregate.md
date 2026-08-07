# Evidência P6-004 — IAP e aggregate interference

**Data:** 2026-08-07  
**Branch:** `feat/p6-protection-models`  
**Task:** P6-004 — IAP e aggregate interference

## Defeito observado

CPAS só aplicava regras booleanas peer (same CBSD / PPA / ESC → terminate).
Não havia motor IAP por ponto/canal com fairshare, redução EIRP 1 dB, nem
saídas tipadas keep / reduce_power / suspend / terminate com audit trail.

## Alterações

- `services/iap/` — modelos Pydantic (`ProtectionPoint`, `GrantRfInfo` com
  `source_sas_id`); `aggregate_channel` / canais 5 MHz / margem pré-IAP;
  `run_iap` alinhado à estrutura do harness `iapPointConstraint` (fairshare
  residual, todos os canais, −1 dB só quando nenhum grant satura na ronda);
  `peer_fad.py` converte CBSD FAD congelados → grants peer
  (`is_managing_sas=False`); coupling injectável.
- `services/cpas_service.py` — snapshot `(peer_sas_id, type, id, json)`;
  IAP sobre grants locais + peers do freeze; mutações só locais;
  ações desconhecidas / `peer/*` ignoradas.
- Floor −137: bound FAD.1 / maxEirp CBRS (ver review).
- `suspend`: **não** exigido pelo IAP reference model nesta etapa (débito).
- Testes: `tests/unit/test_iap_service.py` (fairshare, peers, freeze N/N+1).

Escopo consciente **fora** deste task (→ P6-005):

- coupling RF real (ITM/NLCD) e points oficiais PPA/FSS/ESC/DPA;
- DPA movelist completo;
- peer grants no fairshare IAP (hoje só grants locais no hook CPAS).

## Comandos observados

```text
.venv/bin/ruff check services/iap/ services/cpas_service.py \
  tests/unit/test_iap_service.py
→ All checks passed!

.venv/bin/python -m pytest -q \
  tests/unit/test_iap_service.py \
  tests/unit/test_cpas_pipeline.py \
  tests/unit/test_multi_sas.py \
  tests/unit/test_fad_client.py \
  tests/unit/test_compliance_matrix.py
→ 61 passed
```

## Escopo WInnForum

Motor IAP local determinístico. **Nenhum** caso oficial
`WINNF.FT.S.IPR.*` / FPR / PPR marcado PASS. Matrix: `FAMILY.IPR` e
`FAMILY.GRA` notas atualizadas; `FAMILY.FDB` permanece failing
(BLOCKED_BY_P6 RF completo).

## Riscos remanescentes

- Sem points/coupling no pipeline CPAS default → comportamento peer
  boolean inalterado (compatível).
- Fairshare só sobre grants locais até peers entrarem no RF info set.
- Famílias avançadas → **P6-005**.
