# G8-002 — Managed network / managed-consumer canonical representation

**UUT branch:** `generalization/g2`  
**Scope:** Canonical `ConsumerView` for network holders (area footprints + network identity).  
**Not claimed:** eLSA1 protocol (G8-004), `availability_constraint` (G8-003), or `eu_elsa` full profile YAML.

## Deliverable

- `adapters/managed_consumer.py` — `ManagedNetworkAdapter` (`kind=network`)
- Capabilities: `managed_area`, `network_identity`, plus shared `frequency_range` / `max_eirp`
- Profile v2: `requirements.network_capabilities` (closed set; no `geolocation`)
- Entry point: `spectrum_access.network_adapters` → `managed`
- Explicit **reject** of CBSD/Grant payload keys (`cbsdId`, `fccId`, `grantId`, …)

## Architecture

| Decision | Choice |
| --- | --- |
| Canonical noun | `ConsumerView` (holder + footprints) — D6 |
| Network ≠ device | `AdapterKind.NETWORK`; no `geolocation` |
| Fake CBSD | Forbidden — fail closed on CBSD-shaped keys |
| Protocol | Separate (`ProtocolAdapter` / G8-004) |

## Checks

`tests/unit/test_g8_002_managed_consumer.py` (+ related G4/G6 adapter suites).
