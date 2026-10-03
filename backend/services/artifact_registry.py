"""Artifact registry: validation hardening, exact SHA-256 + robust fingerprint + audit logging."""
from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from PIL import Image

import config
from models.artifact import ArtifactRecord, ArtifactStatus, ArtifactType
from services import blockchain
from services.errors import DuplicateError, NotFoundError, ValidationFailure
from services.fingerprint import compute_robust_fingerprint
from services.hashing import sha256_bytes
from services.model_registry import get_model
from services.store import store


def validate_artifact_payload(data: bytes, artifact_type: ArtifactType = ArtifactType.IMAGE) -> None:
    """Phase 9 hardening: validate file size, header magic numbers, and image integrity."""
    if not data or len(data) == 0:
        raise ValidationFailure("Artifact data cannot be empty")
    if len(data) > config.MAX_UPLOAD_BYTES:
        max_mb = config.MAX_UPLOAD_BYTES // (1024 * 1024)
        raise ValidationFailure(f"Artifact size ({len(data)} bytes) exceeds maximum limit ({max_mb} MB)")
    if artifact_type == ArtifactType.IMAGE:
        # Pillow integrity verification (prevents decompression bombs and truncated files)
        try:
            im = Image.open(io.BytesIO(data))
            im.verify()
        except Exception as exc:
            raise ValidationFailure(f"Artifact payload is corrupt or not a recognized image format: {exc}")


def register_artifact(data: bytes, artifact_type: ArtifactType = ArtifactType.IMAGE, model_id: Optional[str] = None) -> ArtifactRecord:
    validate_artifact_payload(data, artifact_type)
    if model_id:
        get_model(model_id)
    exact_hash = sha256_bytes(data)
    with store.lock:
        existing = store.find_artifact_by_hash(exact_hash)
        if existing:
            raise DuplicateError(f"These exact bytes are already registered as {existing.artifact_id}", existing.artifact_id)
        record = ArtifactRecord(
            artifact_id="ART-" + uuid.uuid4().hex[:8].upper(),
            artifact_type=artifact_type,
            exact_hash=exact_hash,
            robust_fingerprint=compute_robust_fingerprint(data, artifact_type),
            size_bytes=len(data),
            model_id=model_id,
            status=ArtifactStatus.REGISTERED,
            created_at=datetime.now(timezone.utc),
        )
        try:
            store.insert_artifact(record)
        except Exception as exc:
            if "UNIQUE constraint failed: artifacts.exact_hash" in str(exc):
                existing = store.find_artifact_by_hash(exact_hash)
                raise DuplicateError("These exact bytes are already registered", existing.artifact_id if existing else None)
            raise

    # Audit log
    store.log_audit(
        action="ARTIFACT_REGISTERED",
        actor=model_id or "System",
        resource_id=record.artifact_id,
        details={
            "exact_hash": exact_hash,
            "robust_fingerprint": record.robust_fingerprint,
            "size_bytes": record.size_bytes,
            "model_id": model_id,
        },
    )

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
