# Evidência P5-004 — Multi-SAS

**Data:** 2026-08-07  
**Branch:** `feat/p5-fad-sas-cpas`  
**Task:** P5-004 — Multi-SAS

## Defeito observado

O plano exigia cobertura explícita de resiliência multi-SAS:

- peer inacessível (preservar snapshot anterior);
- FAD inválido (checksum/validação; sem apply parcial);
- conflito PPA / grant / ESC peer;
- clocks diferentes (`generationDateTime` remoto ≠ relógio local);
- repetição da mesma geração (idempotente);
- duas execuções CPAS concorrentes (segunda é no-op).

Faltava coluna de geração aplicada por peer e suite dedicada.

## Alterações

- `models/models.py` — `PeerSas.last_fad_generation`
- `database.py` — patch `_ensure_peer_sas_fad_generation_column` no `init_db`
- `services/fad_client_service.py`:
  - erros de rede/HTTP → `FadClientError` (“peer unreachable”);
  - `apply_peer_generation` grava `last_fad_generation`;
  - skip apply só quando `generationDateTime` **e** fingerprint local dos
    registos coincidem (recupera wipe / reapply se conteúdo mudou);
  - `run_peer_fad_sync` reporta `skipped_same_generation` e continua peers independentes
- `tests/unit/test_multi_sas.py` — cenários alinhados ao plano (+ recovery/content)

Proteções peer PPA/ESC/grant já existiam em `cpas_service`; esta task valida o
comportamento end-to-end e a resiliência do sync.

## Comandos observados

```text
.venv/bin/python -m pytest -q tests/unit/test_multi_sas.py
→ 11 passed

.venv/bin/python -m pytest -q \
  tests/unit/test_multi_sas.py \
  tests/unit/test_fad_client.py \
  tests/unit/test_cpas_pipeline.py
→ 30 passed

.venv/bin/ruff check \
  services/fad_client_service.py models/models.py database.py \
  tests/unit/test_multi_sas.py
→ All checks passed!
```

## Escopo WInnForum

Nenhum caso oficial marcado PASS. Fortalece FAD/SSS/FDB (peer sync + CPAS)
para suítes Multi-SAS / daily activity; PASS harness oficial permanece pendente.

## Riscos remanescentes

- Gate Fase 5 ainda bloqueado por PASS oficial FAD/SSS no harness.
- IAP/DPA/propagação completa → Fase 6.
- Peer unreachable em produção depende de timeouts TLS/rede reais (mock cobre
  ConnectError/status no cliente).
- Concorrência CPAS/Multi-SAS: evidência PostgreSQL em
  `tests/integration/test_cpas_multi_sas_postgres.py` + review follow-up.
