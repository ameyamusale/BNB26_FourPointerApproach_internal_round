"""Phase 5 API: provenance graphs and model/artifact passports."""
from __future__ import annotations

from fastapi import APIRouter

from api.deps import to_http
from services import graph, passport
from services.errors import ModelLedgerError

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/full")
def full_graph():
    """Whole-registry graph for the dashboard/audit views."""
    return graph.build_full_graph()


@router.get("/artifacts/{artifact_id}")
def artifact_graph(artifact_id: str):
    try:
        return graph.build_graph(artifact_id)
    except ModelLedgerError as exc:
        raise to_http(exc)


@router.get("/models/{model_id}/passport")
def model_passport(model_id: str):
    try:
        return passport.model_passport(model_id)
    except ModelLedgerError as exc:
        raise to_http(exc)


@router.get("/artifacts/{artifact_id}/passport")
def artifact_passport(artifact_id: str):
    try:
        return passport.artifact_passport(artifact_id)
    except ModelLedgerError as exc:
        raise to_http(exc)
