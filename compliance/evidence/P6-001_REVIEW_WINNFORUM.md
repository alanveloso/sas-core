# Review WInnForum — diff P6-001 + residual P5 FAD/matrix (2026-08-07)

**Branch:** `feat/p6-protection-models`  
**Escopo:** `protection_data/`, doctor/startup hooks, FAD `validate_manifest`
(omit empty types), matrix FAD.1/.2 + PAT packaging notes.

## Achados

### Critical
Nenhum.

### High (corrigidos)

1. **Doctor mutava `set_data_root` global** — `tools/doctor.py`  
   `run_doctor()` chamava `set_data_root(...)` apesar de já passar `data_root=` a
   `validate_dataset_bundle`, poluindo o processo após o doctor.  
   **Fix:** remover `set_data_root`; validar só com `data_root=` explícito.
   Teste: `get_data_root()` inalterado após doctor.

2. **`file_glob` permitia path escape** — `protection_data/schema.py` + `loader.py`  
   `Path.glob("../**/*")` saía do `relative_path` do slot.  
   **Fix:** validator rejeita `..` / abs em `file_glob`; matches fora de
   `slot_dir` são ignorados via `_assert_within`.

3. **`assert_protection_data_ready(strict=True)` por omissão** — `loader.py`  
   Desalinhado de `Settings.sas_protection_data_strict=False`; chamada sem kwargs
   falhava com payloads soft ausentes.  
   **Fix:** default `strict=False` + teste de aceitação com só VERSION markers.

### Medium (remanescentes)

1. **FAD omit types** — peer pode omitir `cbsd`/`zone`/… (não só `coordination`);
   `files` continua non-empty; tipos desconhecidos rejeitados. Justificado pelo
   harness FAD.2; risco residual de wipe local se peer omitir tipos com dados
   esperados (comportamento “absent ≡ empty” intencional).
2. **P6 packaging vs RF real** — VERSION markers não garantem conteúdo semântico
   (ITM/NLCD/FSS ainda stubs de revisão); strict mode ainda opcional por omissão.
3. **Working tree misto** — residual P5 (FAD client + `P5_GATE_FINAL`) junto com
   P6-001; commits devem separar se possível.

### Low

1. Docstring FAD client tinha indentação inconsistente (corrigida cosmeticamente).
2. `FAMILY.PAT` tem `evidence` de packaging com `status: blocked` (não é claim PASS).
3. Warnings `utcnow` pré-existentes nos testes FAD.

## Testes

```text
.venv/bin/python -m pytest -q \
  tests/unit/test_protection_data.py \
  tests/unit/test_fad_client.py \
  tests/security/test_certs_and_doctor.py \
  tests/unit/test_compliance_matrix.py
→ 47 passed

.venv/bin/ruff check protection_data/ tools/doctor.py \
  services/fad_client_service.py tests/unit/test_protection_data.py
→ All checks passed!
```
