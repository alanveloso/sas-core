"""CBSD-to-SAS v1.2 routes with per-item schema validation."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from schemas.deregistration import DeregistrationRequestItem
from schemas.grant import GrantRequestItem
from schemas.heartbeat import HeartbeatRequestItem
from schemas.registration import RegistrationRequestItem
from schemas.relinquishment import RelinquishmentRequestItem
from schemas.spectrum_inquiry import SpectrumInquiryRequestItem
from services.cbsd_batch import merge_schema_and_service_responses, parse_item_batch
from services.deregistration_service import process_deregistration
from services.error_handlers import INVALID_VALUE, MAXIMUM_BATCH_SIZE, MISSING_PARAM
from services.grant_service import process_grant
from services.heartbeat_service import process_heartbeat
from services.mtls_auth import load_client_certificate, sha1_fingerprint_colon
from services.registration_service import process_registration
from services.relinquishment_service import process_relinquishment
from services.spectrum_inquiry_service import process_spectrum_inquiry

router = APIRouter(prefix="/v1.2", tags=["cbsd-sas"])

_REQUEST_KEYS = {
    "registration": "registrationRequest",
    "spectrumInquiry": "spectrumInquiryRequest",
    "grant": "grantRequest",
    "heartbeat": "heartbeatRequest",
    "relinquishment": "relinquishmentRequest",
    "deregistration": "deregistrationRequest",
}

_RESPONSE_KEYS = {
    "registration": "registrationResponse",
    "spectrumInquiry": "spectrumInquiryResponse",
    "grant": "grantResponse",
    "heartbeat": "heartbeatResponse",
    "relinquishment": "relinquishmentResponse",
    "deregistration": "deregistrationResponse",
}


def _client_cert_hash(request: Request) -> str | None:
    cert = load_client_certificate(request)
    if cert is None:
        return None
    return sha1_fingerprint_colon(cert)


def _single_code_response(procedure: str, code: int) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={_RESPONSE_KEYS[procedure]: [{"response": {"responseCode": code}}]},
    )


def _run_batch(
    *,
    procedure: str,
    response_key: str,
    body: dict[str, Any],
    item_model: type,
    run_service: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
) -> JSONResponse:
    request_key = _REQUEST_KEYS[procedure]
    raw_items = body.get(request_key)
    if raw_items is None:
        # Protocol envelope (HTTP 200), not FastAPI 400 → WINNF remap ambiguity.
        return _single_code_response(procedure, MISSING_PARAM)
    if not isinstance(raw_items, list):
        return _single_code_response(procedure, INVALID_VALUE)
    try:
        parsed = parse_item_batch(
            raw_items, item_model=item_model, max_batch_size=MAXIMUM_BATCH_SIZE
        )
    except ValueError as exc:
        message = str(exc)
        if "MaximumBatchSize" in message:
            # Spec allows HTTP error for oversized batches (do not remap to HTTP 200).
            return JSONResponse(
                status_code=400,
                content={
                    "detail": message,
                    "responseCode": INVALID_VALUE,
                },
            )
        return _single_code_response(procedure, INVALID_VALUE)

    service_responses = (
        run_service(parsed.items_for_service) if parsed.items_for_service else []
    )
    merged = merge_schema_and_service_responses(
        schema_error_codes=parsed.schema_error_codes,
        service_index_map=parsed.service_index_map,
        service_responses=service_responses,
        echo_from_raw=raw_items,
    )
    return JSONResponse({response_key: merged})


@router.post("/registration")
def registration(
    request: Request,
    body: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    return _run_batch(
        procedure="registration",
        response_key="registrationResponse",
        body=body,
        item_model=RegistrationRequestItem,
        run_service=lambda items: process_registration(
            db, items, certificate_hash=_client_cert_hash(request)
        ),
    )


@router.post("/grant")
def grant(
    request: Request,
    body: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    return _run_batch(
        procedure="grant",
        response_key="grantResponse",
        body=body,
        item_model=GrantRequestItem,
        run_service=lambda items: process_grant(
            db, items, certificate_hash=_client_cert_hash(request)
        ),
    )


@router.post("/heartbeat")
def heartbeat(
    body: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    return _run_batch(
        procedure="heartbeat",
        response_key="heartbeatResponse",
        body=body,
        item_model=HeartbeatRequestItem,
        run_service=lambda items: process_heartbeat(db, items),
    )


@router.post("/spectrumInquiry")
def spectrum_inquiry(
    request: Request,
    body: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    return _run_batch(
        procedure="spectrumInquiry",
        response_key="spectrumInquiryResponse",
        body=body,
        item_model=SpectrumInquiryRequestItem,
        run_service=lambda items: process_spectrum_inquiry(
            db, items, certificate_hash=_client_cert_hash(request)
        ),
    )


@router.post("/relinquishment")
def relinquishment(
    body: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    return _run_batch(
        procedure="relinquishment",
        response_key="relinquishmentResponse",
        body=body,
        item_model=RelinquishmentRequestItem,
        run_service=lambda items: process_relinquishment(db, items),
    )


@router.post("/deregistration")
def deregistration(
    body: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    return _run_batch(
        procedure="deregistration",
        response_key="deregistrationResponse",
        body=body,
        item_model=DeregistrationRequestItem,
        run_service=lambda items: process_deregistration(db, items),
    )
