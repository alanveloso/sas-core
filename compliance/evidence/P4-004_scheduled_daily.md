# Evidência P4-004 — Scheduled daily activities

**Data:** 2026-08-07  
**Branch:** `fix/p4-admin-api`  
**Task:** P4-004 — Scheduled daily activities

## Defeito observado

`POST /admin/trigger/enable_scheduled_daily_activities` apenas gravava a flag
`scheduled_daily_activities`; nenhum ticker lia a flag nem disparava o pipeline
CPAS na janela acordada (FDB_8: US/Pacific 02:00–04:00).

## Alterações

- `services/clock.py` — relógio UTC injetável (`set_clock_provider` / `utc_now`).
- `services/cpas_schedule_service.py` — enable com TZ/horas, `tick_scheduled_cpas`,
  anti-dupla (`lastSuccessfulLocalDate` + `cpas_running`), auditoria início/fim,
  loop daemon, retentativa se falhou o dispatch e ainda está na janela.
- Mesmo entrypoint `trigger_daily_activities` / `execute_cpas_pipeline` do imediato;
  sucesso na janela marca o dia via `mark_scheduled_success_if_applicable`.
- Rota Admin + resume no startup se a flag persistida estiver enabled.
- Env: `SAS_CPAS_TIMEZONE`, `SAS_CPAS_START_HOUR`, `SAS_CPAS_END_HOUR`,
  `SAS_CPAS_SCHEDULE_TICK_SECONDS` (defaults alinhados à política CPAS, sem
  hardcodes de fixtures FDB).
- Review WInnForum: fail-closed em TZ inválida / JSON corrompido / payload sem
  `enabled`; horas clamp 0–23; commit único enable+audit; lock no tick;
  HTTP 500 (não empty-200) se TZ inválida no enable.
- Testes: `tests/unit/test_cpas_schedule.py`.

## Comandos observados

```text
env -u DATABASE_URL -u CERTS_DIR .venv/bin/pytest -q \
  tests/unit/test_cpas_schedule.py \
  tests/unit/test_cpas_execution_mode.py \
  tests/unit/test_admin_inventory.py \
  tests/contract/test_admin_no_catchall.py
→ 39 passed

python -m tools.winnforum.admin_inventory …
→ TriggerEnableScheduledDailyActivities = implemented
→ stub_or_unimplemented: só PAT 501
```

## Escopo WInnForum

Nenhum caso oficial marcado PASS. Habilita FDB_8 a observar CPAS na janela de
parede sem `TriggerDailyActivitiesImmediately`.

## Riscos remanescentes

- Loop em processo API (não Celery Beat); workers Celery ainda executam o body.
- Unit tests avançam o relógio via `now=`; FDB_8 oficial continua a dormir wall-clock.
- Qualquer CPAS bem-sucedido *dentro* da janela marca o dia (imediato ou agendado).
- Injeções Admin thin (P4-005) e PAT 501 permanecem.
