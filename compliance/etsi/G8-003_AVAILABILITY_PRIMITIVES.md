# G8-003 — Availability / temporal constraint primitives

## Why first-class

| Regime | Need | Not modeled as |
| --- | --- | --- |
| eLSA (TS 103 652) | eLSRAI windows, validity, scheduled/on-demand, evacuation | CBSD heartbeat / Grant |
| CBRS | (optional future overlays) | Incumbent-as-access-class |
| BR SLP | Mostly static; no driver here | — |

Per G0-004/G0-005 D9/D12: `availability_constraint` is an authorization-family mechanism; **incumbent return = availability expiry**, not `preemption`.

## What shipped

| Symbol | Role |
| --- | --- |
| `AvailabilityConstraint` | Named window: mode × validity × frequency/geo/power scope × zone kind |
| `AvailabilityChangeEvent` | Event trigger (`updated` / `expired` / `evacuation`) for reevaluation |
| `availability_constraint` | Registry id on `AUTHORIZATION` axis |
| `temporal.availability` | Profile v2 closed config (`mode: scheduled\|on_demand`) |

## Explicitly out of scope

- eLSA1 protocol codec (G8-004)
- Full `eu_elsa.yaml` reference profile (later G8 slice)
- Wiring into Coordination Core request path / CPAS
- Treating availability expiry as class preemption

## Justification vs inventing from CBRS

Reuse: `TimeInterval`, `FrequencyRange`, geography, `TransmissionFootprint`, `snapshot_evaluate_apply` for reevaluation cycles.  
New: only the availability noun + event kinds required by ≥2 design pressures (eLSA matrix + D9 deferred name).
