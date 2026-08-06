"""Parse CBSD batch payloads with per-item schema validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from schemas.common import winnf_code_from_validation_errors
from services.error_handlers import INVALID_VALUE, MAXIMUM_BATCH_SIZE

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class BatchParseResult:
    """Parallel arrays: schema_error_code[i] set means item i failed schema."""

    schema_error_codes: list[int | None]
    items_for_service: list[dict[str, Any]]
    service_index_map: list[int]  # service position → original batch index

    @property
    def batch_size(self) -> int:
        return len(self.schema_error_codes)


def _payload_for_service(raw: dict[str, Any], parsed: BaseModel) -> dict[str, Any]:
    """Dump validated model while preserving nested extras from the raw item."""
    dumped = parsed.model_dump(mode="python")
    for key in ("installationParam", "airInterface", "measReport", "cbsdInfo"):
        raw_nested = raw.get(key)
        dumped_nested = dumped.get(key)
        if isinstance(raw_nested, dict) and isinstance(dumped_nested, dict):
            # Raw extras first, then validated/coerced known fields win on overlap.
            dumped[key] = {**raw_nested, **dumped_nested}
        elif isinstance(raw_nested, dict) and dumped_nested is None:
            dumped[key] = dict(raw_nested)
    return dumped


def parse_item_batch(
    raw_items: Any,
    *,
    item_model: type[T],
    max_batch_size: int = MAXIMUM_BATCH_SIZE,
) -> BatchParseResult:
    if not isinstance(raw_items, list):
        raise ValueError("batch must be a list")
    if len(raw_items) > max_batch_size:
        raise ValueError(f"batch exceeds MaximumBatchSize ({max_batch_size})")

    codes: list[int | None] = []
    items_for_service: list[dict[str, Any]] = []
    service_index_map: list[int] = []

    for idx, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            codes.append(INVALID_VALUE)
            continue
        try:
            parsed = item_model.model_validate(raw)
        except ValidationError as exc:
            codes.append(winnf_code_from_validation_errors(list(exc.errors())))
            continue
        codes.append(None)
        items_for_service.append(_payload_for_service(raw, parsed))
        service_index_map.append(idx)

    return BatchParseResult(
        schema_error_codes=codes,
        items_for_service=items_for_service,
        service_index_map=service_index_map,
    )


def merge_schema_and_service_responses(
    *,
    schema_error_codes: list[int | None],
    service_index_map: list[int],
    service_responses: list[dict[str, Any]],
    echo_from_raw: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build a full-length batch response preserving request cardinality."""
    out: list[dict[str, Any] | None] = [None] * len(schema_error_codes)
    for idx, code in enumerate(schema_error_codes):
        if code is None:
            continue
        item: dict[str, Any] = {"response": {"responseCode": code}}
        if echo_from_raw and idx < len(echo_from_raw):
            raw = echo_from_raw[idx]
            for key in ("cbsdId", "grantId"):
                if isinstance(raw, dict) and key in raw and raw[key] is not None:
                    item[key] = raw[key]
        out[idx] = item

    if len(service_responses) != len(service_index_map):
        raise ValueError("service response count mismatch")
    for service_pos, origin_idx in enumerate(service_index_map):
        out[origin_idx] = service_responses[service_pos]

    merged: list[dict[str, Any]] = []
    for slot in out:
        if slot is None:
            merged.append({"response": {"responseCode": INVALID_VALUE}})
        else:
            merged.append(slot)
    return merged
