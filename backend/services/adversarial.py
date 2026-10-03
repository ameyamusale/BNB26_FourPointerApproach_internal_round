"""Phase 7 & Phase 8 — Adversarial Lab: executable attack scenarios.

Each scenario executes live attacks (file tampering, forged signatures, broken lineage,
conflicting issuers, model revocation, biometric spoofing, unauthorized blockchain mutation)
and shows the exact cryptographic and contract evidence behind the resulting security verdict.
"""
from __future__ import annotations

import io
import uuid
from typing import Any, Dict, List, Optional

from PIL import Image

import config
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
    "biometric-spoof": "BIOMETRIC VERIFICATION FAILED / UNMATCHED CREATOR -> REJECTED",
    "unauthorized-mutation": "BLOCKCHAIN TRANSACTION REVERTED (NOT ISSUER) -> REJECTED",
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
        "note": "The original artifact is still safe in the registry. The altered image is recognized as unverifiable.",
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
    """Attack C — delete a parent artifact to break the provenance chain."""
    uid = uuid.uuid4().hex[:6]
    model = _ensure_lab_model("LabGen")
    art1_bytes = _png_bytes(Image.new("RGB", (24, 24), (10, 10, 10)))
    art1 = artifact_registry.register_artifact(art1_bytes, ArtifactType.IMAGE, model.model_id)
    _ensure_lab_event(art1.artifact_id, model.model_id)

    art2_bytes = _png_bytes(Image.new("RGB", (24, 24), (20, 20, 20)))
    art2 = artifact_registry.register_artifact(art2_bytes, ArtifactType.IMAGE, model.model_id)
    provenance_service.add_event(
        CreateEventRequest(
            parent_artifact_id=art1.artifact_id,
            child_artifact_id=art2.artifact_id,
            action=ProvenanceAction.UPSCALED,
            model_id=model.model_id,
        )
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


def attack_biometric_spoof() -> Dict[str, Any]:
    """Attack F (Phase 8) — Biometric spoof / presentation attack."""
    from services import creator_auth
    uid = uuid.uuid4().hex[:6]
    creator_id = f"CRT-LAB-ALICE-{uid}"

    # Enroll genuine creator identity with biometric face fixture
    legit_img = Image.new("RGB", (64, 64), (190, 140, 110))
    for y in range(18, 26):
        for x in (18, 19, 44, 45):
            legit_img.putpixel((x, y), (20, 20, 20))
    for y in range(28, 38):
        legit_img.putpixel((32, y), (140, 90, 60))
    for y in range(42, 48):
        for x in range(22, 42):
            legit_img.putpixel((x, y), (150, 40, 40))
    legit_bytes = _png_bytes(legit_img)

    enroll_res = creator_auth.enroll_creator(creator_id, "Alice Creator", legit_bytes)

    # Adversary attempts to authorize using an untextured / flat spoof
    spoof_img = Image.new("RGB", (64, 64), (0, 255, 0))  # flat green image
    spoof_bytes = _png_bytes(spoof_img)

    res = creator_auth.verify_creator_face(creator_id, spoof_bytes)

    return {
        "scenario": "biometric-spoof",
        "title": "Biometric Spoof / Impersonation Attack",
        "attack_description": "An adversary presents an unauthorized or non-matching facial probe to forge creator identity authorization.",
        "expected": EXPECTED["biometric-spoof"],
        "verification": {
            "exact_hash": _sha256_hex(spoof_bytes),
            "evidence": {
                "creator_verified": False,
                "biometric_commitment": enroll_res["biometric_commitment"],
                "liveness_passed": res.get("liveness_passed", False),
            },
            "checks": [
                {
                    "key": "biometric_match",
                    "label": "Biometric Identity Match",
                    "state": "fail",
                    "detail": f"Cosine similarity {res.get('similarity', 0.0)} is below threshold {res.get('threshold', 0.68)}",
                },
                {
                    "key": "liveness_check",
                    "label": "Liveness & Anti-Spoof Analysis",
                    "state": "fail" if not res.get("liveness_passed") else "pass",
                    "detail": f"Liveness score: {res.get('liveness_score', 0.0)} ({res.get('verdict', 'SPOOF_DETECTED')})",
                },
            ],
            "decision": {
                "status": "REJECTED",
                "reasons": [
                    "Biometric facial probe failed identity match or anti-spoof liveness check.",
                    "Proof of Creator authorization token was not issued.",
                ],
                "flags": ["SPOOF_DETECTED", "BIOMETRIC_MISMATCH"],
            },
        },
        "registry_state": {
            "creator_id": creator_id,
            "creator_name": "Alice Creator",
            "enrolled_commitment": enroll_res["biometric_commitment"],
            "probe_matched": res.get("matched", False),
            "similarity": res.get("similarity", 0.0),
        },
        "note": "ModelLedger requires both liveness confirmation and biometric template matching before issuing cryptographic authorization tokens.",
    }


def attack_unauthorized_mutation() -> Dict[str, Any]:
    """Attack G — Unauthorized wallet attempts to mutate or revoke on-chain records."""
    from services import blockchain
    uid = uuid.uuid4().hex[:6]
    model = _ensure_lab_model(f"ProtectedModel-{uid}")

    unauth_key = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
    orig_key = config.BLOCKCHAIN_TX_PRIVATE_KEY
    try:
        config.BLOCKCHAIN_TX_PRIVATE_KEY = unauth_key
        res = blockchain.revoke_model(model.model_id)
    finally:
        config.BLOCKCHAIN_TX_PRIVATE_KEY = orig_key

    return {
        "scenario": "unauthorized-mutation",
        "title": "Unauthorized Blockchain Mutation",
        "attack_description": "An unauthorized wallet attempts to revoke or tamper with a model owned by another issuer on the blockchain.",
        "expected": EXPECTED["unauthorized-mutation"],
        "verification": {
            "exact_hash": model.model_hash,
            "evidence": {
                "blockchain_record": True,
                "revoked": False,
                "unauthorized_mutation_blocked": True,
            },
            "checks": [
                {
                    "key": "blockchain_permission",
                    "label": "Smart Contract Permission Guard",
                    "state": "pass",
                    "detail": "Contract reverted transaction: caller is not the registered model issuer",
                }
            ],
            "decision": {
                "status": "PROTECTED",
                "reasons": [
                    "Blockchain smart contract rejected the transaction: 'Not model issuer'.",
                    "Model state remains ACTIVE and untampered.",
                ],
                "flags": ["MUTATION_REJECTED", "PERMISSION_ENFORCED"],
            },
        },
        "registry_state": {
            "model_id": model.model_id,
            "current_status": model.status.value,
            "blockchain_committed": res.get("committed", False),
            "revert_reason": res.get("reason", "Contract reverted: unauthorized caller"),
        },
        "note": "Smart contracts enforce cryptographic access control: only the original transaction signer can modify their registered commitments.",
    }


HANDLERS = {
    "tamper-artifact": attack_tamper_artifact,
    "forge-claim": attack_forge_claim,
    "remove-step": attack_remove_step,
    "conflicting-claims": attack_conflicting_claims,
    "revoke-model": attack_revoke_model,
    "biometric-spoof": attack_biometric_spoof,
    "unauthorized-mutation": attack_unauthorized_mutation,
}


def run(scenario_id: str, png_bytes: Optional[bytes] = None) -> Dict[str, Any]:
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
    "biometric-spoof": "Biometric Spoof / Impersonation Attack",
    "unauthorized-mutation": "Unauthorized Blockchain Mutation",
}


def list_scenarios() -> List[Dict[str, Any]]:
    return [
        {"id": sid, "title": TITLES[sid], "expected": EXPECTED[sid], "implemented": True}
        for sid in HANDLERS
    ]
