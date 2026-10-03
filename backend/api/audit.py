"""Audit Log API router (Phase 9 — Production Hardening & Tamper-Evident History)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from services.store import store

router = APIRouter(prefix="/api/audit", tags=["audit"])


class AuditLogEntry(BaseModel):
    log_id: str
    timestamp: str
    action: str
    actor: str
    resource_id: Optional[str] = None
    details: Dict[str, Any]
    prev_hash: str
    log_hash: str


@router.get("/logs", response_model=List[AuditLogEntry])
def get_audit_logs(limit: int = Query(100, ge=1, le=500)):
    """Retrieve the recent tamper-evident audit logs."""
    return store.list_audit_logs(limit=limit)


@router.get("/verify-chain")
def verify_audit_log_chain():
    """Verify cryptographic integrity of the SHA-256 audit log hash chain."""
    return store.verify_audit_log_chain()
