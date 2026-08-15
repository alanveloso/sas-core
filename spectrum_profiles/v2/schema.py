"""Profile v2 spectrum section (G3-001). Other v2 sections arrive in later G3 tasks."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from primitives.frequency import FrequencyRange


class SpectrumSegment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1)
    low_hz: int
    high_hz: int

    @model_validator(mode="after")
    def _interval(self) -> SpectrumSegment:
        FrequencyRange(low_hz=self.low_hz, high_hz=self.high_hz)
        return self


class FixedWidthChannelization(BaseModel):
    """Assignment grid only (D13). RF aggregation resolution is a separate parameter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mechanism: str = Field(..., min_length=1)
    width_hz: int = Field(..., gt=0)
    origin_hz: int = Field(..., ge=0)
    role: str = Field(default="assignment")

    @model_validator(mode="after")
    def _role_and_mechanism(self) -> FixedWidthChannelization:
        if self.mechanism != "fixed_width_channelization":
            raise ValueError("unsupported channelization mechanism")
        if self.role != "assignment":
            raise ValueError("channelization.role must be 'assignment'")
        return self


class SpectrumRange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1)
    low_hz: int
    high_hz: int
    segments: tuple[SpectrumSegment, ...] = ()

    @model_validator(mode="after")
    def _range_and_segments(self) -> SpectrumRange:
        parent = FrequencyRange(low_hz=self.low_hz, high_hz=self.high_hz)
        ids = [seg.id for seg in self.segments]
        if len(ids) != len(set(ids)):
            raise ValueError(f"segment ids must be unique within range {self.id!r}")
        for seg in self.segments:
            child = FrequencyRange(low_hz=seg.low_hz, high_hz=seg.high_hz)
            if not parent.contains(child):
                raise ValueError(
                    f"segment {seg.id!r} is not contained in range {self.id!r}"
                )
        return self


class SpectrumSection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ranges: tuple[SpectrumRange, ...]
    channelization: FixedWidthChannelization | None = None

    @model_validator(mode="after")
    def _ranges(self) -> SpectrumSection:
        if not self.ranges:
            raise ValueError("spectrum.ranges must contain at least one range")
        ids = [item.id for item in self.ranges]
        if len(ids) != len(set(ids)):
            raise ValueError("spectrum range ids must be unique")
        ordered = sorted(self.ranges, key=lambda item: item.low_hz)
        for left, right in zip(ordered, ordered[1:], strict=False):
            a = FrequencyRange(low_hz=left.low_hz, high_hz=left.high_hz)
            b = FrequencyRange(low_hz=right.low_hz, high_hz=right.high_hz)
            if a.overlaps(b):
                raise ValueError("spectrum ranges must not overlap")
        return self


class ProfileMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    status: str = Field(default="custom")
    references: tuple[str, ...] = ()
    based_on: str | None = None


class ProfileV2SpectrumDocument(BaseModel):
    """Envelope + spectrum only. Additional v2 sections are added in later tasks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    api_version: str
    kind: str
    metadata: ProfileMetadata
    spectrum: SpectrumSection

    @model_validator(mode="after")
    def _envelope(self) -> ProfileV2SpectrumDocument:
        if self.api_version != "spectrum-access/v2":
            raise ValueError("api_version must be 'spectrum-access/v2'")
        if self.kind != "SpectrumProfile":
            raise ValueError("kind must be 'SpectrumProfile'")
        if self.metadata.status not in {"reference", "custom"}:
            raise ValueError("metadata.status must be 'reference' or 'custom'")
        return self
