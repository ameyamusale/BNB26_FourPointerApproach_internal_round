"""Domain schema: an AI-generated (or transformed) artifact."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ArtifactType(str, Enum):
    IMAGE = "IMAGE"  # MVP modality. Other modalities can be added later.


class ArtifactStatus(str, Enum):
    REGISTERED = "REGISTERED"
    REVOKED = "REVOKED"


class ArtifactRecord(BaseModel):
    artifact_id: str
    artifact_type: ArtifactType = ArtifactType.IMAGE
    exact_hash: str                      # SHA-256 of the exact bytes
    robust_fingerprint: Optional[str] = None  # Phase 4 (None = not computed)
    size_bytes: int
    storage_uri: Optional[str] = None    # Phase 1 stores hashes only, never the file
    model_id: Optional[str] = None       # claimed originating model
    status: ArtifactStatus = ArtifactStatus.REGISTERED
    created_at: datetime
    blockchain_tx: Optional[str] = None
