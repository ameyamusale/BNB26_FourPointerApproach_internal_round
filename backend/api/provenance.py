from __future__ import annotations

from typing import List

from fastapi import APIRouter

from api.deps import to_http
from models.provenance import CreateEventRequest, Lineage, ProvenanceEvent
from services import provenance
from services.errors import ModelLedgerError

router = APIRouter(prefix="/api/provenance", tags=["provenance"])


@router.post("/events", response_model=ProvenanceEvent, status_code=201)
def create_event(req: CreateEventRequest):
    """Record a provenance event, optionally sign it, and commit it when blockchain is configured."""
    try:
        return provenance.add_event(req)
    except ModelLedgerError as exc:
        raise to_http(exc)


@router.get("/events", response_model=List[ProvenanceEvent])
def list_events():
    return provenance.list_events()


@router.get("/artifacts/{artifact_id}/events", response_model=List[ProvenanceEvent])
def artifact_events(artifact_id: str):
    try:
        return provenance.events_for_artifact(artifact_id)
    except ModelLedgerError as exc:
        raise to_http(exc)


@router.get("/artifacts/{artifact_id}/lineage", response_model=Lineage)
def artifact_lineage(artifact_id: str):
    try:
        return provenance.build_lineage(artifact_id)
    except ModelLedgerError as exc:
        raise to_http(exc)
