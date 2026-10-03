"""Domain schema: provenance events and lineage."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProvenanceAction(str, Enum):
    GENERATED = "GENERATED"
    UPSCALED = "UPSCALED"
    EDITED = "EDITED"
    RESIZED = "RESIZED"
    CROPPED = "CROPPED"
    FILTERED = "FILTERED"
    RE_ENCODED = "RE_ENCODED"
    PUBLISHED = "PUBLISHED"


class CreateEventRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    parent_artifact_id: Optional[str] = None  # None only for GENERATED
    child_artifact_id: str
    action: ProvenanceAction
    model_id: Optional[str] = None
    application_id: Optional[str] = Field(None, max_length=80)
    # Private details (prompts, parameters...) go here. Only their hash is stored.
    metadata: Dict[str, Any] = Field(default_factory=dict)
    creator_auth_token: Optional[str] = Field(None, description="Proof of Creator authorization token")


class ProvenanceEvent(BaseModel):
    model_config = {"protected_namespaces": ()}

    event_id: str
    parent_artifact_id: Optional[str] = None
    child_artifact_id: str
    action: ProvenanceAction
    model_id: Optional[str] = None
    application_id: Optional[str] = None
    metadata_hash: str
    signature: Optional[str] = None       # Phase 4
    blockchain_tx: Optional[str] = None   # Phase 3
    signature_public_key: Optional[str] = None  # Phase 4 verification key
    created_at: datetime
    creator_verified: bool = False
    biometric_commitment: Optional[str] = None


class LineageStep(BaseModel):
    artifact_id: str
    event: Optional[ProvenanceEvent] = None  # the event that produced this artifact


class Lineage(BaseModel):
    artifact_id: str
    steps: List[LineageStep]  # ordered root -> artifact
    depth: int
    root_reached: bool        # True when the chain starts at a GENERATED event
    issues: List[str] = Field(default_factory=list)
