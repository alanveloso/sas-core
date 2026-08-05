"""Typed spectrum profile schema for CBRS / WInnForum configuration."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _validate_quantity_params(params: dict[str, Any], *, where: str) -> dict[str, Any]:
    """Reject non-numeric / negative Hz and metre quantities in free-form param maps."""
    for key, value in params.items():
        if not (key.endswith("_hz") or key.endswith("_m")):
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{where}.{key} must be a number")
        if value < 0:
            raise ValueError(f"{where}.{key} must be non-negative")

    low = params.get("low_hz")
    high = params.get("high_hz")
    if low is not None and high is not None and low >= high:
        raise ValueError(f"{where}.low_hz must be strictly less than {where}.high_hz")
    return params


class BandPlan(BaseModel):
    """Contiguous frequency allocation expressed in hertz."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    low_hz: int = Field(..., description="Lower band edge in Hz.")
    high_hz: int = Field(..., description="Upper band edge in Hz.")
    unit: Literal["Hz"] = Field(default="Hz", description="Frequency unit; only Hz is supported.")

    @model_validator(mode="after")
    def _validate_interval(self) -> BandPlan:
        if self.low_hz < 0 or self.high_hz < 0:
            raise ValueError("band_plan frequencies must be non-negative")
        if self.low_hz >= self.high_hz:
            raise ValueError("band_plan.low_hz must be strictly less than band_plan.high_hz")
        return self


class ProtectionRule(BaseModel):
    """Named RF/protection rule with validated quantity parameters."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(..., min_length=1)
    enabled: bool = True
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("params")
    @classmethod
    def _validate_params(cls, params: dict[str, Any]) -> dict[str, Any]:
        return _validate_quantity_params(params, where="protection.params")


class EntityParams(BaseModel):
    """Per-entity configuration knobs (e.g. FSS, ESC, DPA)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_type: str = Field(..., min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("params")
    @classmethod
    def _validate_params(cls, params: dict[str, Any]) -> dict[str, Any]:
        return _validate_quantity_params(params, where="entity.params")


class SpectrumProfile(BaseModel):
    """Versioned spectrum operating profile loaded from an allowed directory."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    description: str | None = None
    rule_applied: str = Field(..., min_length=1)
    band_plan: BandPlan
    protections: list[ProtectionRule] = Field(default_factory=list)
    entities: list[EntityParams] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_collections(self) -> SpectrumProfile:
        names = [rule.name for rule in self.protections]
        if len(names) != len(set(names)):
            raise ValueError("protection rule names must be unique")
        entity_types = [entity.entity_type for entity in self.entities]
        if len(entity_types) != len(set(entity_types)):
            raise ValueError("entity_type values must be unique")

        band = self.band_plan
        for rule in self.protections:
            low = rule.params.get("low_hz")
            high = rule.params.get("high_hz")
            if low is not None and (low < band.low_hz or low > band.high_hz):
                raise ValueError(
                    f"protection '{rule.name}' low_hz is outside band_plan"
                )
            if high is not None and (high < band.low_hz or high > band.high_hz):
                raise ValueError(
                    f"protection '{rule.name}' high_hz is outside band_plan"
                )
        return self

    def get_protection(self, name: str) -> ProtectionRule | None:
        for rule in self.protections:
            if rule.name == name:
                return rule
        return None

    def get_entity(self, entity_type: str) -> EntityParams | None:
        for entity in self.entities:
            if entity.entity_type == entity_type:
                return entity
        return None
