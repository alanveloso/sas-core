# G11-004 — Release gate + pacote de evidências

**Companion:** `compliance/generalization/g11_004_release_gate.yaml`  
**Verify:** `python -m tools.g11_004_release_gate --verify`

## Veredito deste pacote

| Claim | Status |
| --- | --- |
| Release local reproduzível (checklist + inventário) | **SIM** (este pacote) |
| `PASS_OFFICIAL` / certificação formal de entidade | **NÃO** |
| G5-009 suporta `PASS_OFFICIAL` | **NÃO** (`BLOCKED`; ver evidência) |
| Campanha oficial final | **G11-005** via `/run-winnforum-gate G11-005` |

Passar em testes locais **não** é certificação WInnForum/FCC/Anatel.

## UUT

- Branch: `generalization/g2`
- HEAD na authoring do pacote: `8d3a8cb026cff570a7c24f1a42986f03bac196bf`
- SHA do release candidate = commit que **inclui** este pacote (re-verificar após o commit)

Request-path: `cbrs_winnforum`. Profiles v2 no inventário: CBRS, BR SLP, eLSA, TVWS (**CONDITIONAL**).

## Claims permitidos vs proibidos

Permitidos: loads/doctor locais, G11-001..003, métricas G10-003, CONDITIONAL TVWS como evidência, existência da evidência G5-009 sem `PASS_OFFICIAL`.

Proibidos: `PASS_OFFICIAL`, “certified” regulatório, reescrever CONDITIONAL/PARTIAL/GAP → PASS sem nova evidência.

## Reprodução

1. `git checkout <release-candidate-sha>`
2. Instalar lock + editable (ver YAML)
3. `python -m tools.g11_004_release_gate --verify`
4. Rodar `local_gate_tests` do YAML
5. Só então, se necessário, `/run-winnforum-gate G11-005`

## Próximo candidato (não autorizado aqui)

**G11-005** — usar **`/run-winnforum-gate G11-005`**, não `/next-generalization-task`.
