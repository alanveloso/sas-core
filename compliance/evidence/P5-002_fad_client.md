# Evidência P5-002 — FAD client seguro

**Data:** 2026-08-07  
**Branch:** `fix/p5-fad-sas-cpas`  
**Task:** P5-002 — FAD client seguro

## Defeito observado

`services/cpas_service.py` puxava FAD de peers com:

- `check_hostname=False`;
- sem validação de checksum/size/version/schema;
- redirects abertos;
- upsert sem purge de IDs ausentes;
- falha a meio podia misturar gerações / deixar estado parcial.

## Alterações

- Novo `services/fad_client_service.py`:
  - TLS `check_hostname` default **True** (`SAS_FAD_CLIENT_CHECK_HOSTNAME`);
  - allowlist = apenas `PeerSas` injectados;
  - SSRF: só `https`, same-origin com o peer, DNS bloqueia IPs privados/metadata salvo peer lab explícito, **sem** follow de redirects;
  - valida manifest + ficheiros (checksum SHA-1, size, version, recordType, envelope timestamps);
  - sync atómico por peer: fetch+validate → delete+insert → commit; rollback preserva snapshot anterior;
  - purge de registos ausentes na nova geração.
- `services/cpas_service.py` delega `run_peer_fad_sync` ao cliente seguro.
- `config.py` / `.env.example`: `SAS_FAD_CLIENT_CHECK_HOSTNAME`.
- Testes: `tests/unit/test_fad_client.py`.

## Comandos observados

```text
env -u DATABASE_URL -u CERTS_DIR .venv/bin/pytest -q \
  tests/unit/test_fad_client.py \
  tests/unit/test_fad_server.py \
  tests/unit/test_cpas_execution_mode.py \
  tests/unit/test_grant_pal_ppa.py \
  tests/unit/test_heartbeat_extended.py
→ 66 passed

.venv/bin/ruff check services/fad_client_service.py services/cpas_service.py \
  config.py tests/unit/test_fad_client.py
→ All checks passed
```

## Escopo WInnForum

Habilita FAD/SSS cliente sem SSRF óbvio e com geração coerente por peer.
Nenhum caso oficial marcado PASS (harness FAD/SSS client ainda pendente no gate F5).

## Riscos remanescentes

- Harness com peer URL `localhost` e leaf CN diferente exige
  `SAS_FAD_CLIENT_CHECK_HOSTNAME=false` explícito (não é o default).
- DNS rebinding entre `getaddrinfo` e o connect HTTP ainda é uma janela teórica
  (mitigado por same-origin + bloqueio de IPs sensíveis).
- CPAS pipeline transacional completo → **P5-003**.
- Conflitos multi-SAS / geração repetida → **P5-004**.

## Review WInnForum (pós-P5-002)

Correções high:

- metadata `169.254.169.254/253` nunca permitida (mesmo como peer lab);
- manifest exige os 4 `recordType`;
- URLs com userinfo rejeitadas;
- IDs `(recordType, id)` duplicados rejeitados;
- `follow_redirects=False` não pode ser overridden;
- `SELECT … FOR UPDATE` no `PeerSas` antes do replace atómico.

Testes: `pytest tests/unit/test_fad_client.py` → 14 passed (+ CPAS related).
