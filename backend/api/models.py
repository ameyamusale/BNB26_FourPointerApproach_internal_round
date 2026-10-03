from __future__ import annotations

from typing import List

from fastapi import APIRouter

from api.deps import to_http
from models.model import ModelRecord, RegisterModelRequest
from services import blockchain, model_registry
from services.errors import ModelLedgerError, ValidationFailure
from services.store import store

router = APIRouter(prefix="/api/models", tags=["models"])


@router.post("", response_model=ModelRecord, status_code=201)
def register_model(req: RegisterModelRequest):
    try:
        return model_registry.register_model(req)
    except ModelLedgerError as exc:
        raise to_http(exc)


@router.get("", response_model=List[ModelRecord])
def list_models():
    return model_registry.list_models()


@router.get("/{model_id}", response_model=ModelRecord)
def get_model(model_id: str):
    try:
        return model_registry.get_model(model_id)
    except ModelLedgerError as exc:
        raise to_http(exc)


@router.post("/{model_id}/revoke", response_model=ModelRecord)
def revoke_model(model_id: str):
    try:
        model = model_registry.get_model(model_id)
        chain = blockchain.revoke_model(model_id)
        if blockchain.is_configured() and not chain.get("committed"):
            raise ValidationFailure(f"Model revocation was not committed on-chain: {chain.get('reason', 'unknown error')}")
        store.revoke_model(model_id)
        return store.get_model(model_id)
    except ModelLedgerError as exc:
        raise to_http(exc)
