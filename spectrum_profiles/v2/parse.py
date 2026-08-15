"""Parse Profile v2 documents. Does not replace the CBRS v1 loader."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from primitives.registry import MechanismAxis, MechanismRegistry, builtin_mechanism_registry
from spectrum_profiles.loader import ProfileValidationError
from spectrum_profiles.v2.schema import ProfileV2SpectrumDocument


def _catalog(registry: MechanismRegistry | None) -> MechanismRegistry:
    return registry or builtin_mechanism_registry()


def parse_profile_v2_spectrum(
    document: Any,
    *,
    registry: MechanismRegistry | None = None,
) -> ProfileV2SpectrumDocument:
    if not isinstance(document, dict):
        raise ProfileValidationError("profile v2 document must be a mapping")
    try:
        parsed = ProfileV2SpectrumDocument.model_validate(document)
    except ValidationError as exc:
        raise ProfileValidationError(f"profile v2 failed validation: {exc}") from exc
    catalog = _catalog(registry)
    try:
        if parsed.spectrum.channelization is not None:
            catalog.on_axis(
                MechanismAxis.SPECTRUM, parsed.spectrum.channelization.mechanism
            )
        if parsed.access is not None:
            catalog.on_axis(MechanismAxis.ACCESS, parsed.access.mechanism)
        if parsed.authorization is not None:
            catalog.on_axis(MechanismAxis.AUTHORIZATION, parsed.authorization.mechanism)
        if parsed.power is not None:
            catalog.on_axis(MechanismAxis.POWER, parsed.power.mechanism)
        if parsed.geography is not None:
            catalog.on_axis(MechanismAxis.GEOGRAPHY, parsed.geography.mechanism)
        if parsed.temporal is not None and parsed.temporal.reevaluation is not None:
            catalog.on_axis(
                MechanismAxis.TEMPORAL, parsed.temporal.reevaluation.mechanism
            )
    except ValueError as exc:
        raise ProfileValidationError(str(exc)) from exc
    return parsed
