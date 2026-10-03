"""Domain schema: verification evidence, trust states and reports."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from models.artifact import ArtifactRecord
from models.model import ModelRecord
from models.provenance import Lineage


class TrustStatus(str, Enum):
    TRUSTED = "TRUSTED"
    SELF_ASSERTED = "SELF_ASSERTED"
    UNVERIFIABLE = "UNVERIFIABLE"
    CONFLICT = "CONFLICT"


class VerificationEvidence(BaseModel):
    """Tri-state evidence: True = passed, False = failed, None = NOT CHECKED.

    None is deliberately distinct from True so that an unavailable check
    (e.g. blockchain offline) can never be shown as a success.
    """

    artifact_match: Optional[bool] = None
    model_registered: Optional[bool] = None
    signature_valid: Optional[bool] = None
    parent_exists: Optional[bool] = None
    transformation_valid: Optional[bool] = None
    blockchain_record: Optional[bool] = None
    revoked: Optional[bool] = None


class EvidenceCheck(BaseModel):
    key: str
    label: str
    state: str  # "pass" | "fail" | "not_checked"
    detail: str = ""


class TrustDecision(BaseModel):
    status: TrustStatus
    reasons: List[str] = Field(default_factory=list)
    flags: List[str] = Field(default_factory=list)


class VerificationReport(BaseModel):
    exact_hash: str
    artifact: Optional[ArtifactRecord] = None
    model: Optional[ModelRecord] = None
    lineage: Optional[Lineage] = None
    evidence: VerificationEvidence
    checks: List[EvidenceCheck]
    decision: TrustDecision
    blockchain: Dict[str, Any]
    verified_at: datetime
