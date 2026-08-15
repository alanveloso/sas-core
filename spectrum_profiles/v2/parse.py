"""Parse Profile v2 spectrum documents. Does not replace the CBRS v1 loader."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from primitives.registry import MechanismAxis, MechanismRegistry, builtin_mechanism_registry
from spectrum_profiles.loader import ProfileValidationError
from spectrum_profiles.v2.schema import ProfileV2SpectrumDocument


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
        raise ProfileValidationError(f"profile v2 spectrum failed validation: {exc}") from exc
    if parsed.spectrum.channelization is not None:
        catalog = registry or builtin_mechanism_registry()
        catalog.on_axis(
            MechanismAxis.SPECTRUM, parsed.spectrum.channelization.mechanism
        )
    return parsed
