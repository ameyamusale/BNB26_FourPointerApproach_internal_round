"""Artifact registry: exact SHA-256 + robust fingerprint + optional blockchain commitment."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from models.artifact import ArtifactRecord, ArtifactStatus, ArtifactType
from services import blockchain
from services.errors import DuplicateError, NotFoundError
from services.fingerprint import compute_robust_fingerprint
from services.hashing import sha256_bytes
from services.model_registry import get_model
from services.store import store


def register_artifact(data: bytes, artifact_type: ArtifactType = ArtifactType.IMAGE, model_id: Optional[str] = None) -> ArtifactRecord:
    if model_id:
        get_model(model_id)
    exact_hash = sha256_bytes(data)
    with store.lock:
        existing = store.find_artifact_by_hash(exact_hash)
        if existing:
            raise DuplicateError(f"These exact bytes are already registered as {existing.artifact_id}", existing.artifact_id)
        record = ArtifactRecord(
            artifact_id="ART-" + uuid.uuid4().hex[:8].upper(), artifact_type=artifact_type,
            exact_hash=exact_hash, robust_fingerprint=compute_robust_fingerprint(data, artifact_type),
            size_bytes=len(data), model_id=model_id, status=ArtifactStatus.REGISTERED,
            created_at=datetime.now(timezone.utc),
        )
        try:
            store.insert_artifact(record)
        except Exception as exc:
            if "UNIQUE constraint failed: artifacts.exact_hash" in str(exc):
                existing = store.find_artifact_by_hash(exact_hash)
                raise DuplicateError("These exact bytes are already registered", existing.artifact_id if existing else None)
            raise

    chain = blockchain.register_artifact(record.artifact_id, record.exact_hash, record.robust_fingerprint, record.model_id)
    if chain.get("committed"):
        store.update_artifact_blockchain_tx(record.artifact_id, chain["tx_hash"])
        record = store.get_artifact(record.artifact_id) or record
    return record


def get_artifact(artifact_id: str) -> ArtifactRecord:
    record = store.get_artifact(artifact_id)
    if record is None:
        raise NotFoundError(f"Artifact {artifact_id} not found")
    return record


def list_artifacts() -> List[ArtifactRecord]:
    return store.list_artifacts()


def find_by_hash(exact_hash: str) -> Optional[ArtifactRecord]:
    return store.find_artifact_by_hash(exact_hash)
