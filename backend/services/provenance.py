"""Provenance events, cryptographic signing, audit logging, and Proof of Creator support."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from models.provenance import CreateEventRequest, Lineage, LineageStep, ProvenanceAction, ProvenanceEvent
from services import blockchain, signature
from services.artifact_registry import get_artifact
from services.creator_auth import validate_authorization_token
from services.errors import DuplicateError, NotFoundError, ValidationFailure
from services.hashing import canonical_json_hash
from services.model_registry import get_model
from services.store import store


def add_event(req: CreateEventRequest) -> ProvenanceEvent:
    child = get_artifact(req.child_artifact_id)
    if req.action == ProvenanceAction.GENERATED and req.parent_artifact_id:
        raise ValidationFailure("GENERATED events cannot have a parent artifact")
    if req.action != ProvenanceAction.GENERATED and not req.parent_artifact_id:
        raise ValidationFailure(f"{req.action.value} events require a parent artifact")
    if req.parent_artifact_id:
        get_artifact(req.parent_artifact_id)
    if req.model_id:
        get_model(req.model_id)
    existing = store.events_for_child(child.artifact_id)
    if existing:
        raise DuplicateError(f"{child.artifact_id} already has a creating event ({existing[0].event_id}).", existing[0].event_id)

    creator_verified = False
    biometric_commitment = None
    if req.creator_auth_token:
        token_info = validate_authorization_token(req.creator_auth_token)
        if token_info:
            creator_verified = True
            biometric_commitment = token_info.get("biometric_commitment")

    event = ProvenanceEvent(
        event_id="EVT-" + uuid.uuid4().hex[:8].upper(),
        parent_artifact_id=req.parent_artifact_id,
        child_artifact_id=req.child_artifact_id,
        action=req.action,
        model_id=req.model_id,
        application_id=req.application_id,
        metadata_hash=canonical_json_hash(req.metadata),
        created_at=datetime.now(timezone.utc),
        creator_verified=creator_verified,
        biometric_commitment=biometric_commitment,
    )

    signed = signature.sign_event(event)
    if signed:
        event.signature, event.signature_public_key = signed

    store.insert_event(event)

    # Audit log
    store.log_audit(
        action="PROVENANCE_EVENT_CREATED",
        actor=req.application_id or req.model_id or "System",
        resource_id=event.event_id,
        details={
            "action": event.action.value,
            "child_artifact_id": event.child_artifact_id,
            "parent_artifact_id": event.parent_artifact_id,
            "creator_verified": creator_verified,
            "biometric_commitment": biometric_commitment,
        },
    )

    claim = signature.claim_hash(event)
    chain = blockchain.add_provenance_event(
        event.event_id,
        event.parent_artifact_id,
        event.child_artifact_id,
        event.model_id,
        event.application_id,
        event.action.value,
        event.metadata_hash,
        claim,
    )
    if chain.get("committed"):
        store.update_event_evidence(event.event_id, blockchain_tx=chain["tx_hash"])
    return store.events_for_child(event.child_artifact_id)[0]


def get_event(event_id: str) -> ProvenanceEvent:
    for event in store.list_events():
        if event.event_id == event_id:
            return event
    raise NotFoundError(f"Provenance event {event_id} not found")


def events_for_artifact(artifact_id: str) -> List[ProvenanceEvent]:
    get_artifact(artifact_id)
    return store.events_for_artifact(artifact_id)


def list_events() -> List[ProvenanceEvent]:
    return store.list_events()


def build_lineage(artifact_id: str) -> Lineage:
    get_artifact(artifact_id)
    steps: List[LineageStep] = []
    issues: List[str] = []
    seen = set()
    current = artifact_id
    root_reached = False
    while current:
        if current in seen:
            issues.append(f"Cycle detected at {current}")
            break
        seen.add(current)
        events = store.events_for_child(current)
        if not events:
            steps.append(LineageStep(artifact_id=current, event=None))
            issues.append(f"{current} has no recorded provenance event")
            break
        event = events[0]
        steps.append(LineageStep(artifact_id=current, event=event))
        if event.parent_artifact_id is None:
            root_reached = event.action == ProvenanceAction.GENERATED
            break
        if store.get_artifact(event.parent_artifact_id) is None:
            issues.append(f"Parent {event.parent_artifact_id} of {current} does not exist")
            break
        current = event.parent_artifact_id
    steps.reverse()
    return Lineage(artifact_id=artifact_id, steps=steps, depth=max(len(steps) - 1, 0), root_reached=root_reached, issues=issues)
