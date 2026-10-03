"""Conflict Detector (Phase 7).

Finds incompatible provenance claims so the trust engine can raise the
CONFLICT / INCONSISTENT state instead of silently picking one story.
"""
from __future__ import annotations

from typing import List


def detect_conflicts(artifact_id: str) -> List[str]:
    from services.store import store
    claims = store.list_claims(artifact_id)
    conflicts: List[str] = []

    # Competing issuer claims registered on the same artifact.
    if len(claims) > 1:
        issuers = {c.get("issuer_id") for c in claims if c.get("issuer_id")}
        if len(issuers) > 1:
            conflicts.append(f"Multiple competing issuers assert claims on artifact {artifact_id}: {sorted(i for i in issuers if i)}")
        statuses = {c.get("status") for c in claims}
        if "DISPUTED" in statuses or "CONFLICT" in statuses:
            conflicts.append(f"Artifact {artifact_id} has claims flagged as DISPUTED/CONFLICT")

    # Competing origin-model claims: the artifact row and/or multiple creating
    # events attribute the same artifact to different models.
    events = store.events_for_child(artifact_id)
    claimed_models = {e.model_id for e in events if e.model_id}
    artifact = store.get_artifact(artifact_id)
    if artifact and artifact.model_id:
        claimed_models.add(artifact.model_id)
    if len(claimed_models) > 1:
        conflicts.append(
            f"Incompatible origin claims for {artifact_id}: artifact is attributed to models {sorted(claimed_models)}"
        )

    return conflicts
