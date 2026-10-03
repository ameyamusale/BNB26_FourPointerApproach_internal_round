"""Transformation-aware evidence using robust artifact fingerprints."""
from __future__ import annotations

from typing import Optional

from models.provenance import ProvenanceAction, ProvenanceEvent
from services.fingerprint import fingerprint_distance
from services.store import store

CONTENT_PRESERVING = {
    ProvenanceAction.UPSCALED, ProvenanceAction.RESIZED, ProvenanceAction.CROPPED,
    ProvenanceAction.RE_ENCODED, ProvenanceAction.FILTERED, ProvenanceAction.EDITED,
}

MAX_PHASH_DISTANCE = 18


def check_transformation(event: ProvenanceEvent) -> Optional[bool]:
    if not event.parent_artifact_id:
        return None
    parent = store.get_artifact(event.parent_artifact_id)
    child = store.get_artifact(event.child_artifact_id)
    if parent is None or child is None:
        return False
    if event.action not in CONTENT_PRESERVING:
        return None
    distance = fingerprint_distance(parent.robust_fingerprint, child.robust_fingerprint)
    return None if distance is None else distance <= MAX_PHASH_DISTANCE
