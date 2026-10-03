"""Domain schema: AI model registered with ModelLedger."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ModelStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"  # revocation endpoint arrives in Phase 3/7; history is never deleted


class RegisterModelRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80, examples=["VisionGen-X"])
    version: str = Field(..., min_length=1, max_length=32, examples=["2.1.0"])
    model_type: str = Field("image-generator", min_length=1, max_length=40)
    creator_name: str = Field(..., min_length=1, max_length=80, examples=["Team Alpha"])
    description: Optional[str] = Field(None, max_length=500)
    # Optional: SHA-256 of the model weights, computed client-side so the binary never
    # leaves the creator's machine. If omitted, the server commits to the metadata only.
    model_hash: Optional[str] = Field(None, pattern=r"^[0-9a-fA-F]{64}$")


class ModelRecord(BaseModel):
    model_id: str
    name: str
    version: str
    model_type: str
    creator_id: str
    creator_name: str
    description: Optional[str] = None
    model_hash: str
    metadata_hash: str
    status: ModelStatus = ModelStatus.ACTIVE
    created_at: datetime
    blockchain_tx: Optional[str] = None
