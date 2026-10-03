"""Phase 7 — Adversarial Lab: executable attack scenarios.

Each scenario corrupts real state (or registers forged claims) and then runs
the real verification engine, so the reported trust state changes for genuine,
inspectable reasons. The evidence behind every result is returned so judges can
audit exactly why the status flipped.
"""
from __future__ import annotations

import io
import uuid
from typing import Any, Dict, List, Optional

from PIL import Image

from models.artifact import ArtifactType
from models.model import RegisterModelRequest
from models.provenance import CreateEventRequest, ProvenanceAction
from services import artifact_registry, model_registry, provenance as provenance_service, verification
from services.errors import NotFoundError
from services.store import store

EXPECTED = {
    "tamper-artifact": "EXACT HASH MISMATCH -> UNVERIFIABLE",
    "forge-claim": "SIGNATURE INVALID / CLAIM NOT SUPPORTED -> CONFLICT",
    "remove-step": "BROKEN LINEAGE -> CONFLICT",
    "conflicting-claims": "PROVENANCE CONFLICT DETECTED -> CONFLICT",
    "revoke-model": "PROVENANCE AVAILABLE BUT MODEL REVOKED -> SELF_ASSERTED",
}


def _png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _sha256_hex(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


def _ensure_lab_model(name: str, version: str = "1.0") -> Any:
    """Register (or reuse) a lab model used by the attack scenarios."""
    for model in store.list_models():
        if model.name == name:
            return model
    return model_registry.register_model(RegisterModelRequest(name=name, version=version, creator_name="Adversarial Lab"))


def _ensure_lab_artifact(png_bytes: bytes, model_id: str) -> Any:
    """Register (or reuse) a clean lab artifact for an attack to act on."""
    existing = store.find_artifact_by_hash(_sha256_hex(png_bytes))
    if existing:
        return existing
    return artifact_registry.register_artifact(png_bytes, ArtifactType.IMAGE, model_id)


def _ensure_lab_event(artifact_id: str, model_id: str) -> Any:
    """Attach the GENERATED event once, so attacks are re-runnable."""
    existing = store.events_for_child(artifact_id)
    if existing:
        return existing[0]
    return provenance_service.add_event(
        CreateEventRequest(child_artifact_id=artifact_id, action=ProvenanceAction.GENERATED, model_id=model_id)
    )


def _verification_payload(report) -> Dict[str, Any]:
    return {
        "exact_hash": report.exact_hash,
        "artifact_id": report.artifact.artifact_id if report.artifact else None,
        "evidence": report.evidence.model_dump(),
        "checks": [c.model_dump() for c in report.checks],
        "decision": report.decision.model_dump(),
    }


# ---------------------------------------------------------------- attacks ----

def attack_tamper_artifact() -> Dict[str, Any]:
    """Attack A — modify a registered artifact after registration."""
    model = _ensure_lab_model("LabGen")
    original_bytes = _png_bytes(Image.new("RGB", (24, 24), (90, 90, 90)))
    art = _ensure_lab_artifact(original_bytes, model.model_id)
    _ensure_lab_event(art.artifact_id, model.model_id)

    tampered_bytes = _png_bytes(Image.new("RGB", (24, 24), (91, 90, 90)))
    report = verification.verify_bytes(tampered_bytes)
    return {
        "scenario": "tamper-artifact",
        "title": "Tampered artifact",
        "attack_description": "The image was altered after registration, so its exact SHA-256 no longer matches the registry entry.",
        "expected": EXPECTED["tamper-artifact"],
        "verification": _verification_payload(report),
        "registry_state": {
            "artifact_id": art.artifact_id,
            "registered_exact_hash": art.exact_hash,
            "submitted_exact_hash": report.exact_hash,
        },
    }


def attack_forge_claim() -> Dict[str, Any]:
    """Attack B — swap the recorded producing model on a signed provenance event."""
    uid = uuid.uuid4().hex[:6]
    real_model = _ensure_lab_model("LabGen")
    forged_model = _ensure_lab_model(f"ForgeTarget-{uid}")
    original_bytes = _png_bytes(Image.new("RGB", (24, 24), (60, 60, 200)))
    art = _ensure_lab_artifact(original_bytes, real_model.model_id)
    event = _ensure_lab_event(art.artifact_id, real_model.model_id)

    with store.lock, store._connect() as conn:
        conn.execute("UPDATE provenance_events SET model_id=? WHERE event_id=?", (forged_model.model_id, event.event_id))
        conn.commit()

    report = verification.verify_bytes(original_bytes)
    return {
        "scenario": "forge-claim",
        "title": "Forged provenance claim",
        "attack_description": "The producing model on the provenance event was replaced without re-creating the signature, so the claim is no longer supported by valid evidence.",
        "expected": EXPECTED["forge-claim"],
        "verification": _verification_payload(report),
        "registry_state": {
            "artifact_id": art.artifact_id,
            "true_model_id": real_model.model_id,
            "forged_model_id": forged_model.model_id,
            "event_id": event.event_id,
        },
        "note": "Configure MODELLEDGER_SIGNATURE_PRIVATE_KEY_PEM so events are signed; without signing, the forged claim shows as not-established evidence instead of an invalid signature.",
    }


def attack_remove_step() -> Dict[str, Any]:
    """Attack C — delete an artifact from the middle of a lineage chain."""
    model = _ensure_lab_model("LabGen")
    art1_bytes = _png_bytes(Image.new("RGB", (24, 24), (10, 120, 40)))
    art1 = _ensure_lab_artifact(art1_bytes, model.model_id)
    _ensure_lab_event(art1.artifact_id, model.model_id)

    art2_bytes = _png_bytes(Image.new("RGB", (24, 24), (10, 130, 40)))
    art2 = _ensure_lab_artifact(art2_bytes, model.model_id)
    existing = store.events_for_child(art2.artifact_id)
    if not existing:
        provenance_service.add_event(
            CreateEventRequest(parent_artifact_id=art1.artifact_id, child_artifact_id=art2.artifact_id,
                               action=ProvenanceAction.UPSCALED, model_id=model.model_id)
        )

    # Remove the parent artifact from the registry (lab-only direct store access).
    with store.lock, store._connect() as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM artifacts WHERE artifact_id=?", (art1.artifact_id,))
        conn.commit()

    report = verification.verify_bytes(art2_bytes)
    return {
        "scenario": "remove-step",
        "title": "Missing provenance step",
        "attack_description": "An artifact in the middle of the claimed lineage was removed from the registry, breaking the chain.",
        "expected": EXPECTED["remove-step"],
        "verification": _verification_payload(report),
        "registry_state": {
            "deleted_artifact_id": art1.artifact_id,
            "final_artifact_id": art2.artifact_id,
        },
    }


def attack_conflicting_claims() -> Dict[str, Any]:
    """Attack D — two incompatible origin claims for the same artifact."""
    uid = uuid.uuid4().hex[:6]
    model = _ensure_lab_model("LabGen")
    original_bytes = _png_bytes(Image.new("RGB", (24, 24), (200, 120, 10)))
    art = _ensure_lab_artifact(original_bytes, model.model_id)
    _ensure_lab_event(art.artifact_id, model.model_id)

    store.upsert_identity("CRT-LAB-A", "Lab Issuer A")
    store.upsert_identity("CRT-LAB-B", "Lab Issuer B")
    store.create_claim(f"CLM-{uid}-A", art.artifact_id, "ORIGIN_CLAIM", "CRT-LAB-A", "CRYPTO", "lab-sig-a", "ACTIVE")
    store.create_claim(f"CLM-{uid}-B", art.artifact_id, "ORIGIN_CLAIM", "CRT-LAB-B", "CRYPTO", "lab-sig-b", "ACTIVE")

    report = verification.verify_bytes(original_bytes)
    claims = store.list_claims(art.artifact_id)
    return {
        "scenario": "conflicting-claims",
        "title": "Conflicting origin claims",
        "attack_description": "Two different issuers registered incompatible origin claims for the same artifact.",
        "expected": EXPECTED["conflicting-claims"],
        "verification": _verification_payload(report),
        "claims": claims,
        "registry_state": {"artifact_id": art.artifact_id, "claim_count": len(claims)},
    }


def attack_revoke_model() -> Dict[str, Any]:
    """Attack E — revoke the producing model after registration."""
    uid = uuid.uuid4().hex[:6]
    model = _ensure_lab_model(f"RevokedLabGen-{uid}")
    shade = 90 + (int(uid[:2], 16) % 40)
    original_bytes = _png_bytes(Image.new("RGB", (24, 24), (140, shade, 20)))
    art = _ensure_lab_artifact(original_bytes, model.model_id)
    _ensure_lab_event(art.artifact_id, model.model_id)

    store.revoke_model(model.model_id)
    report = verification.verify_bytes(original_bytes)
    return {
        "scenario": "revoke-model",
        "title": "Revoked producing model",
        "attack_description": "The producing model was revoked after the artifact was registered. History is preserved but trust is downgraded.",
        "expected": EXPECTED["revoke-model"],
        "verification": _verification_payload(report),
        "registry_state": {"artifact_id": art.artifact_id, "model_id": model.model_id, "model_status": "REVOKED"},
    }


HANDLERS = {
    "tamper-artifact": attack_tamper_artifact,
    "forge-claim": attack_forge_claim,
    "remove-step": attack_remove_step,
    "conflicting-claims": attack_conflicting_claims,
    "revoke-model": attack_revoke_model,
}


def run(scenario_id: str, png_bytes: Optional[bytes] = None) -> Dict[str, Any]:
    """Run one attack scenario and return its full evidence payload."""
    handler = HANDLERS.get(scenario_id)
    if handler is None:
        raise NotFoundError(f"Unknown adversarial scenario: {scenario_id}")
    return handler()


TITLES = {
    "tamper-artifact": "Tamper with a registered artifact",
    "forge-claim": "Forge a provenance claim",
    "remove-step": "Remove a provenance step",
    "conflicting-claims": "Create two conflicting origin claims",
    "revoke-model": "Revoke the producing model",
}


def list_scenarios() -> List[Dict[str, Any]]:
    return [
        {"id": sid, "title": TITLES[sid], "expected": EXPECTED[sid], "implemented": True}
        for sid in HANDLERS
    ]
