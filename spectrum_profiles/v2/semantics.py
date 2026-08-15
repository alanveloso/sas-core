"""Closed semantic checks for Profile v2 (G3-004). No expression language."""

from __future__ import annotations

from primitives.registry import MechanismRegistry
from spectrum_profiles.v2.schema import ProfileV2SpectrumDocument

_RF_PROTECTION = frozenset({"single_link_threshold", "aggregate_linear_power"})


def validate_profile_v2_semantics(
    parsed: ProfileV2SpectrumDocument, catalog: MechanismRegistry
) -> None:
    data_caps = (
        set(parsed.data.required_capabilities) if parsed.data is not None else set()
    )
    device_caps = (
        set(parsed.requirements.device_capabilities)
        if parsed.requirements is not None
        else set()
    )
    protection_ids = (
        parsed.protection.mechanisms if parsed.protection is not None else ()
    )

    rf = parsed.rf
    if rf is not None:
        policy = catalog.get(rf.policy)
        if policy.slot != "rf_policy":
            raise ValueError("rf.policy must use an rf_policy registry slot")
        if rf.propagation_model is not None:
            model = catalog.get(rf.propagation_model)
            if model.slot != "rf_model":
                raise ValueError("rf.propagation_model must use an rf_model registry slot")
        if rf.required:
            if "terrain" not in data_caps:
                raise ValueError("rf.required requires data capability 'terrain'")
            if "geolocation" not in device_caps:
                raise ValueError("rf.required requires device capability 'geolocation'")

    if any(item in _RF_PROTECTION for item in protection_ids):
        if rf is None or not rf.required:
            raise ValueError(
                "single_link_threshold/aggregate_linear_power require rf.required"
            )
