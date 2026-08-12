# G1-004 FIX-06 REPORT

**Date (UTC):** 2026-08-12T01:21Z–01:27Z  
**Product code changed:** YES (heartbeat TERMINATED semantics only)  
**CPAS termination / federal ingest / FDB_2–8 / PCR / GPR / MCP / IPR:** not touched  
**Harness test logic:** not modified  
**Full G1-004 / G2:** not run  

---

## Identity

| Item | Value |
|------|--------|
| BASELINE UUT SHA | `d578091b94ffdc4fe79a1016871ffd6a3c5662ca` |
| FIXED WORKTREE SHA/STATE | same baseline + **uncommitted** FIX-06 (not committed) |
| Harness SHA | `928c3150adf7b31e53a96b695bf1fbdd3284ecb2` |

---

## STEP 1 — control-flow characterization

Grant lookup (`lock_grant_row(grant_id, cbsd_id)`) already distinguished:

| Branch | Path | Pre-fix response |
|--------|------|------------------|
| A never existed / cannot resolve | `grant is None` | 103, no `grantId` |
| B other CBSD | same (`cbsd_id` filter) | 103, no `grantId` |
| C active GRANTED/AUTHORIZED | `life.ok` | 0 + authorize |
| D SUSPENDED | `life.response_code == 501` | 501 + `grantId` |
| E TERMINATED | **collapsed with RELINQUISHED** | **103, no `grantId`** |

**Exact failing branch (E):**

1. `services/lifecycle.py` `heartbeat_operation_allowed`  
   `if current in (GrantState.TERMINATED, GrantState.RELINQUISHED):`  
   → `response_code=INVALID_PARAM` (103), `detail="terminal_state"`
2. `services/heartbeat_service.py`  
   `if life.response_code == INVALID_PARAM:`  
   → `_base(INVALID_PARAM, cbsd_id=cbsd_id)` **without** `grant_id`  
   comment: *“Terminal relinquished/terminated: do not echo grantId.”*

D and E were collapsed into “invalid grant”. CPAS termination itself was correct.

---

## ROOT CAUSE

Persisted TERMINATED grants (after CPAS/lifecycle) were mapped to heartbeat **103** without `grantId` instead of WINNF terminal-grant **500** with `grantId`.

---

## FILES CHANGED

- `services/lifecycle.py` — TERMINATED → 500; RELINQUISHED stays 103
- `services/heartbeat_service.py` — TERMINATED branch echoes original `grantId`; no authorize/renew/mutate
- `tests/unit/test_heartbeat_terminated_grant.py` — new (A–D + negatives)
- `tests/unit/test_lifecycle.py` — pin TERMINATED ≠ RELINQUISHED

---

## NEW REGRESSION TESTS

| Test | Coverage |
|------|----------|
| `test_a_heartbeat_on_lifecycle_terminated_grant_returns_500_with_grant_id` | TEST A |
| `test_b_unknown_grant_id_remains_103_without_grant_id` | TEST B |
| `test_b_wrong_cbsd_grant_association_remains_103_without_grant_id` | wrong association |
| `test_c_suspended_grant_heartbeat_stays_501_not_500` | TEST C |
| `test_d_cpas_terminated_grant_heartbeat_returns_500_with_original_grant_id` | TEST D (`apply_cpas_decisions`) |
| `test_relinquished_grant_is_not_converted_to_500` | RELINQUISHED stays 103 |
| `test_heartbeat_operation_allowed_terminated_is_500_not_103` | lifecycle gate |

---

## LOCAL TESTS

| Suite | Result |
|-------|--------|
| focused (new + heartbeat + lifecycle + CPAS/G1 related) | **105 passed** |
| `pytest -q` | **921 passed, 14 skipped** in 77.26s |
| `ruff check .` | **All checks passed** |

No unrelated failures.

---

## OFFICIAL ISOLATED RETEST

UUT rebuilt/restarted with G1-004 compose override (`SAS_EXECUTION_MODE=certification`, RF deps, host network). Admin 200. Reset between cases.

Artifacts: `.cache/g1-004-vm/reruns/20260812T012608Z/artifacts/{HBT_9,FDB_1}/`

### HBT_9

**PASS** (`Ran 1 test … OK`, unittest_exit_code 0)

Second heartbeat `[2]` (device E):

```json
{
  "transmitExpireTime": "2026-08-12T01:26:32Z",
  "response": {"responseCode": 500},
  "cbsdId": "test_fcc_id_e/test_serial_number_e",
  "grantId": "grant/98d91ae00393476f81b3ce03373dff55"
}
```

| Check | Result |
|-------|--------|
| responseCode | **500** |
| grantId preserved | **YES** (same as issued / first HB) |
| terminal state preserved | **YES** (`TERMINATED`, `terminated=t`; A/C remain AUTHORIZED) |
| transmit not restored | past `transmitExpireTime`; no authorize |

### FDB_1

**PASS** (`passed: 1`, `raw_ok: true`, `Ran 1 test … OK`)

| Check | Result |
|-------|--------|
| responseCodes | post-CPAS HB **500, 500** with original grantIds (official accepts 500 or 501) |
| EXZ ingestion proven | **YES** — mock `GET /db_sync` 200 twice; 2 `exclusion_zone` rows; `federal_sync_meta.exz=2` |
| terminal state preserved | **YES** — both grants remain `TERMINATED` / `terminated=t` |

---

## NEGATIVE CHECKS

| Check | Result |
|-------|--------|
| unknown grant | 103, no `grantId` (TEST B) |
| wrong association | 103, no `grantId`; owner stays TERMINATED |
| suspended grant | 501 + `grantId`; not 500; not terminated |
| no reactivation | lifecycle stays TERMINATED; `authorized` not restored to success path |
| no expiration extension | `grant_expire_time` unchanged after HB |
| CPAS behavior | unchanged; still terminates; only HB reporting fixed |

---

## STOP CARD

**CONFIRMED OFFICIAL FAILING CASES BEFORE FIX:** 2  
**CONFIRMED UNIQUE PRODUCT DEFECTS BEFORE FIX:** 1  

**FIX-06 RESULT:** **PASS**  
**PRODUCT DEFECT CLOSED:** **YES**

**OTHER PRODUCT_FAIL_CANDIDATES UNCHANGED:**
- FDB_2
- PCR_1
- GPR_3
- MCP

**ENVIRONMENT BLOCKERS UNCHANGED:**
- FDB_3
- FDB_4
- FDB_5
- FDB_6

**DATASET BLOCKER UNCHANGED:**
- IPR_2

**HARNESS BLOCKERS:**
- FDB_8
- Rel1Ext

**READY FOR NEXT REMEDIATION STEP:** **YES**  
**READY FOR FULL G1-004:** **NO**  
**PASS_OFFICIAL CLAIM SUPPORTED:** **NO**  
**G2 AUTHORIZED:** **NO**

STOP.
