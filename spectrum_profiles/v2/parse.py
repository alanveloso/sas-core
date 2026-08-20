"""Parse Profile v2 documents. Does not replace the CBRS v1 loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError
import yaml

from primitives.registry import MechanismAxis, MechanismRegistry, builtin_mechanism_registry
from spectrum_profiles.loader import (
    ProfileNotFoundError,
    ProfilePathError,
    ProfileValidationError,
)
from spectrum_profiles.v2.schema import ProfileV2SpectrumDocument
from spectrum_profiles.v2.semantics import validate_profile_v2_semantics
from spectrum_profiles.v2.trust import (
    ProfileLoadProvenance,
    ProfileTrustTier,
    assert_metadata_id_matches,
    assert_path_within,
    assert_yaml_profile_file,
    builtin_v2_profiles_dir,
    provenance_for,
    validate_profile_id,
)


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
        if parsed.temporal is not None and parsed.temporal.availability is not None:
            catalog.on_axis(
                MechanismAxis.AUTHORIZATION, parsed.temporal.availability.mechanism
            )
        if parsed.protection is not None:
            for mechanism_id in parsed.protection.mechanisms:
                contract = catalog.get(mechanism_id)
                if contract.axis not in {
                    MechanismAxis.PROTECTION,
                    MechanismAxis.GEOGRAPHY,
                }:
                    raise ValueError(
                        f"mechanism {mechanism_id!r} cannot be composed under protection"
                    )
        if parsed.coordination is not None:
            catalog.on_axis(MechanismAxis.COORDINATION, parsed.coordination.mechanism)
        if parsed.rf is not None:
            catalog.on_axis(MechanismAxis.RF, parsed.rf.policy)
            if parsed.rf.propagation_model is not None:
                catalog.on_axis(MechanismAxis.RF, parsed.rf.propagation_model)
        for item in parsed.constraints:
            mid = item.mechanism
            if mid in {"duplex_mode", "max_assignment_bandwidth"}:
                catalog.on_axis(MechanismAxis.SPECTRUM, mid)
            elif mid == "antenna_height_limit":
                catalog.on_axis(MechanismAxis.POWER, mid)
            elif mid == "forbidden_device_roles":
                catalog.on_axis(MechanismAxis.ACCESS, mid)
            else:
                raise ValueError(f"unsupported constraint mechanism {mid!r}")
            # Instantiates closed primitive (fail closed on bad params).
            item.to_primitive()
        validate_profile_v2_semantics(parsed, catalog)
    except ValueError as exc:
        raise ProfileValidationError(str(exc)) from exc
    return parsed


def load_profile_v2_document(
    path: Path,
    *,
    registry: MechanismRegistry | None = None,
) -> ProfileV2SpectrumDocument:
    """Load and validate a Profile v2 document from an explicit filesystem path.

    Operator-explicit paths are allowed (doctor / custom authoring). Callers that
    need a trust record should use :func:`load_profile_v2_document_with_provenance`.
    """
    resolved = assert_yaml_profile_file(path)
    try:
        document = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ProfileValidationError(f"profile v2 YAML error: {exc}") from exc
    except OSError as exc:
        raise ProfileValidationError(f"profile v2 read error: {exc}") from exc
    return parse_profile_v2_spectrum(document, registry=registry)


def load_profile_v2_document_with_provenance(
    path: Path,
    *,
    registry: MechanismRegistry | None = None,
    trust_tier: ProfileTrustTier = ProfileTrustTier.OPERATOR_EXPLICIT,
) -> tuple[ProfileV2SpectrumDocument, ProfileLoadProvenance]:
    """Like :func:`load_profile_v2_document`, plus immutable load provenance."""
    resolved = assert_yaml_profile_file(path)
    if trust_tier is ProfileTrustTier.BUILTIN_V2:
        assert_path_within(resolved, builtin_v2_profiles_dir())
    parsed = load_profile_v2_document(resolved, registry=registry)
    return parsed, provenance_for(
        parsed, source_path=resolved, trust_tier=trust_tier
    )


def load_profile_v2(
    profile_id: str,
    *,
    registry: MechanismRegistry | None = None,
) -> ProfileV2SpectrumDocument:
    """Load a v2 YAML from ``profiles/v2``. Does not replace ``load_profile``."""
    try:
        validate_profile_id(profile_id)
    except ProfilePathError as exc:
        raise ProfileValidationError(str(exc)) from exc
    root = builtin_v2_profiles_dir()
    path = assert_path_within(root / f"{profile_id}.yaml", root)
    if not path.is_file():
        raise ProfileNotFoundError(f"profile v2 '{profile_id}' not found")
    parsed = load_profile_v2_document(path, registry=registry)
    assert_metadata_id_matches(parsed, profile_id)
    return parsed


def load_profile_v2_with_provenance(
    profile_id: str,
    *,
    registry: MechanismRegistry | None = None,
) -> tuple[ProfileV2SpectrumDocument, ProfileLoadProvenance]:
    """Builtin-tree load with provenance (trust_tier=builtin_v2)."""
    parsed = load_profile_v2(profile_id, registry=registry)
    root = builtin_v2_profiles_dir()
    path = assert_path_within(root / f"{profile_id}.yaml", root)
    return parsed, provenance_for(
        parsed, source_path=path, trust_tier=ProfileTrustTier.BUILTIN_V2
    )
