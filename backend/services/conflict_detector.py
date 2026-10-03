"""Conflict Detector (Phase 7).

Phase 1 allows a single creating event per artifact, so contradictory origin
claims cannot be stored yet. Phase 7 relaxes that and fills this in.
"""
from __future__ import annotations

from typing import List


def detect_conflicts(artifact_id: str) -> List[str]:
    from services.store import store
    claims = store.list_claims(artifact_id)
    conflicts: List[str] = []
    if len(claims) > 1:
        issuers = {c.get("issuer_id") for c in claims if c.get("issuer_id")}
        if len(issuers) > 1:
            conflicts.append(f"Multiple competing issuers assert claims on artifact {artifact_id}: {list(issuers)}")
        statuses = {c.get("status") for c in claims}
        if "DISPUTED" in statuses or "CONFLICT" in statuses:
            conflicts.append(f"Artifact {artifact_id} has claims flagged as DISPUTED/CONFLICT")
    return conflicts
