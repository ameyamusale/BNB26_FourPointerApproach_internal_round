"""Model and Artifact passports (Phase 5 UI feature).

A passport assembles everything the system knows about one model or artifact
into a single verifiable profile: identity, hashes, lineage, events and
blockchain references.
"""
from __future__ import annotations

from typing import Optional

from models.claims import TrustStatus
from services import blockchain
from services.errors import NotFoundError
from services.graph import build_graph
from services.provenance import build_lineage
from services.store import store


def model_passport(model_id: str) -> dict:
    model = store.get_model(model_id)
    if model is None:
        raise NotFoundError(f"Model {model_id} not found")

    artifacts = [a for a in store.list_artifacts() if a.model_id == model_id]
    events = [e for e in store.list_events() if e.model_id == model_id]

    return {
        "model": model,
        "artifacts_count": len(artifacts),
        "events_count": len(events),
        "artifacts": artifacts,
        "events": events,
        "status": model.status.value,
        "blockchain": {
            "tx": model.blockchain_tx,
            "record": blockchain.get_model(model_id),
        },
    }


def artifact_passport(artifact_id: str) -> dict:
    artifact = store.get_artifact(artifact_id)
    if artifact is None:
        raise NotFoundError(f"Artifact {artifact_id} not found")

    lineage = build_lineage(artifact_id)
    graph = build_graph(artifact_id)
    events = store.events_for_artifact(artifact_id)
    children = [e for e in events if e.parent_artifact_id == artifact_id]
    claims = store.list_claims(artifact_id)
    model = store.get_model(artifact.model_id) if artifact.model_id else None

    return {
        "artifact": artifact,
        "model": model,
        "lineage": lineage,
        "graph": graph,
        "events": events,
        "children": children,
        "transformation_count": lineage.depth,
        "provenance_depth": lineage.depth,
        "claims": claims,
        "trust": trust_summary(artifact_id),
        "blockchain": {
            "artifact_tx": artifact.blockchain_tx,
            "record": blockchain.get_artifact(artifact_id),
            "event_ids": blockchain.get_artifact_events(artifact_id),
        },
    }


def trust_summary(artifact_id: str) -> dict:
    """Lightweight trust view for a passport (full crypto verification needs bytes
    and runs through /api/verify)."""
    artifact = store.get_artifact(artifact_id)
    if artifact is None:
        raise NotFoundError(f"Artifact {artifact_id} not found")
    lineage = build_lineage(artifact_id)
    model = store.get_model(artifact.model_id) if artifact.model_id else None
    revoked = bool(model and model.status.value == "REVOKED")
    claims = store.list_claims(artifact_id)
    competing = len({c.get("issuer_id") for c in claims if c.get("issuer_id")}) > 1
    if competing or lineage.issues:
        status = TrustStatus.CONFLICT
    elif revoked:
        status = TrustStatus.SELF_ASSERTED
    else:
        status = TrustStatus.SELF_ASSERTED
    return {
        "status": status.value,
        "lineage_issues": lineage.issues,
        "revoked": revoked,
        "competing_claims": competing,
        "note": "Run /api/verify with the artifact bytes for the full cryptographic decision.",
    }
