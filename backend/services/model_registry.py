"""Model registry with off-chain persistence, audit logging, and Proof of Creator support."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import List

from models.model import ModelRecord, ModelStatus, RegisterModelRequest
from services import blockchain
from services.creator_auth import validate_authorization_token
from services.errors import DuplicateError, NotFoundError, ValidationError
from services.hashing import canonical_json_hash
from services.store import store


def _creator_id(name: str) -> str:
    return "CRT-" + hashlib.sha256(name.strip().lower().encode()).hexdigest()[:10]


def register_model(req: RegisterModelRequest) -> ModelRecord:
    creator_id = _creator_id(req.creator_name)
    creator_verified = False
    biometric_commitment = None

    if req.creator_auth_token:
        token_info = validate_authorization_token(req.creator_auth_token)
        if not token_info:
            raise ValidationError("Invalid, forged, or expired Proof of Creator authorization token")
        creator_verified = True
        biometric_commitment = token_info.get("biometric_commitment")
        creator_id = token_info.get("creator_id", creator_id)

    metadata = {
        "name": req.name.strip(),
        "version": req.version.strip(),
        "model_type": req.model_type.strip(),
        "creator_id": creator_id,
    }
    if req.private_prompt_commitment:
        metadata["prompt_commitment"] = req.private_prompt_commitment.strip()

    metadata_hash = canonical_json_hash(metadata)
    with store.lock:
        existing = next((m for m in store.models.values() if m.metadata_hash == metadata_hash), None)
        if existing:
            raise DuplicateError(f"Model {req.name} v{req.version} by {req.creator_name} is already registered", existing.model_id)
        record = ModelRecord(
            model_id="MDL-" + uuid.uuid4().hex[:8].upper(),
            name=metadata["name"],
            version=metadata["version"],
            model_type=metadata["model_type"],
            creator_id=creator_id,
            creator_name=req.creator_name.strip(),
            description=req.description,
            model_hash=(req.model_hash or metadata_hash).lower(),
            metadata_hash=metadata_hash,
            status=ModelStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            creator_verified=creator_verified,
            biometric_commitment=biometric_commitment,
            private_prompt_commitment=req.private_prompt_commitment,
        )
        try:
            store.insert_model(record)
        except Exception as exc:
            if "UNIQUE constraint failed" in str(exc):
                existing = next((m for m in store.models.values() if m.metadata_hash == metadata_hash), None)
                raise DuplicateError("This model is already registered", existing.model_id if existing else None)
            raise

    # Audit log
    store.log_audit(
        action="MODEL_REGISTERED",
        actor=record.creator_name,
        resource_id=record.model_id,
        details={
            "name": record.name,
            "version": record.version,
            "creator_verified": creator_verified,
            "biometric_commitment": biometric_commitment,
            "model_hash": record.model_hash,
        },
    )

    chain = blockchain.register_model(record.model_id, record.model_hash, record.metadata_hash)
    if chain.get("committed"):
        store.update_model_blockchain_tx(record.model_id, chain["tx_hash"])
        record = store.get_model(record.model_id) or record
    return record


def get_model(model_id: str) -> ModelRecord:
    record = store.get_model(model_id)
    if record is None:
        raise NotFoundError(f"Model {model_id} not found")
    return record


def list_models() -> List[ModelRecord]:
    return store.list_models()
