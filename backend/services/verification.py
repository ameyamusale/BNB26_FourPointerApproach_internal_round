"""Evidence-based artifact verification for ModelLedger (Phases 4, 8, 9)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from models.claims import EvidenceCheck, VerificationEvidence, VerificationReport
from models.model import ModelStatus
from services import blockchain, conflict_detector, signature, transformation
from services.artifact_registry import find_by_hash
from services.hashing import sha256_bytes
from services.provenance import build_lineage
from services.store import store
from services.trust_engine import evaluate

log = logging.getLogger("modelledger.verification")


def _check(key: str, label: str, value: Optional[bool], pass_msg: str, fail_msg: str) -> EvidenceCheck:
    if value is None:
        return EvidenceCheck(key=key, label=label, state="not_checked", detail="Not checked / evidence unavailable")
    return EvidenceCheck(key=key, label=label, state="pass" if value else "fail", detail=pass_msg if value else fail_msg)


def verify_bytes(data: bytes) -> VerificationReport:
    exact_hash = sha256_bytes(data)
    artifact = find_by_hash(exact_hash)
    chain_status = blockchain.status()
    now = datetime.now(timezone.utc)

    if artifact is None:
        evidence = VerificationEvidence(artifact_match=False)
        decision = evaluate(evidence)
        report = VerificationReport(
            exact_hash=exact_hash,
            evidence=evidence,
            checks=[_check("artifact_match", "Exact hash is registered", False, "", "No registered artifact has this SHA-256")],
            decision=decision,
            blockchain=chain_status,
            verified_at=now,
        )
        store.log_audit(
            action="VERIFICATION_PERFORMED",
            actor="Verifier",
            resource_id=exact_hash,
            details={"status": decision.status.value, "match": False},
        )
        return report

    model = store.get_model(artifact.model_id) if artifact.model_id else None
    lineage = build_lineage(artifact.artifact_id)
    own_events = [step.event for step in lineage.steps if step.event is not None]

    own_event = lineage.steps[-1].event if lineage.steps else None
    parent_exists: Optional[bool] = None
    if own_event is not None and own_event.parent_artifact_id:
        parent_exists = store.get_artifact(own_event.parent_artifact_id) is not None

    lineage_ok: Optional[bool]
    if own_event is None:
        lineage_ok = None
    elif any("does not exist" in issue or "Cycle" in issue for issue in lineage.issues):
        lineage_ok = False
    else:
        lineage_ok = True if lineage.root_reached else None

    sig_results = [signature.verify_event_signature(e, e.signature_public_key) for e in own_events]
    signature_valid = None if not sig_results or any(r is None for r in sig_results) else all(sig_results)

    tx_results = [transformation.check_transformation(e) for e in own_events if e.parent_artifact_id]
    transformation_valid = None if not tx_results or any(r is None for r in tx_results) else all(tx_results)

    model_chain = blockchain.has_record("model", model.model_id, model.model_hash) if model else None
    artifact_chain = blockchain.has_record("artifact", artifact.artifact_id, artifact.exact_hash)
    event_chain_results = [blockchain.has_record("provenance", e.event_id, signature.claim_hash(e)) for e in own_events]
    chain_parts = [artifact_chain] + event_chain_results
    if model:
        chain_parts.append(model_chain)
    blockchain_record = None if any(part is None for part in chain_parts) else all(bool(part) for part in chain_parts)

    db_revoked = bool(model and model.status == ModelStatus.REVOKED)
    chain_revoked_model = blockchain.is_revoked_model(model.model_id) if model else None
    chain_revoked_claims = [blockchain.is_revoked_claim(e.event_id) for e in own_events]
    if db_revoked or any(v is True for v in chain_revoked_claims) or chain_revoked_model is True:
        revoked: Optional[bool] = True
    elif model and chain_revoked_model is False and all(v is False for v in chain_revoked_claims):
        revoked = False
    elif model and not own_events and chain_revoked_model is False:
        revoked = False
    else:
        revoked = None

    model_registered = None if model is None else (bool(model_chain) if model_chain is not None else True)
    conflicts = conflict_detector.detect_conflicts(artifact.artifact_id)

    # Phase 8 — Proof of Creator verification
    creator_verified: Optional[bool] = None
    creator_commitment: Optional[str] = None
    creator_ident_info: Optional[Dict[str, Any]] = None

    if model:
        ident = store.get_identity(model.creator_id)
        if ident:
            creator_ident_info = {
                "identity_id": ident["identity_id"],
                "name": ident["name"],
                "wallet_address": ident.get("wallet_address"),
                "has_biometric": bool(ident.get("biometric_enrollment_reference")),
            }
        if model.creator_verified or any(getattr(e, "creator_verified", False) for e in own_events):
            creator_verified = True
            creator_commitment = model.biometric_commitment or next(
                (e.biometric_commitment for e in own_events if getattr(e, "biometric_commitment", None)), None
            )
        elif ident and ident.get("biometric_enrollment_reference"):
            # Creator is enrolled with biometrics, but this specific artifact/model was self-asserted
            creator_verified = False
        else:
            creator_verified = None

    evidence = VerificationEvidence(
        artifact_match=True,
        model_registered=model_registered,
        signature_valid=signature_valid,
        parent_exists=parent_exists,
        transformation_valid=transformation_valid,
        blockchain_record=blockchain_record,
        revoked=revoked,
        creator_verified=creator_verified,
        creator_biometric_commitment=creator_commitment,
    )
    decision = evaluate(evidence, conflicts)
    if lineage.issues and not lineage.root_reached:
        decision.reasons.extend(lineage.issues)

    checks: List[EvidenceCheck] = [
        _check("artifact_match", "Exact hash is registered", True, f"Matches {artifact.artifact_id}", ""),
        _check(
            "model_registered",
            "Claimed model is registered",
            evidence.model_registered,
            f"{model.name} v{model.version}" if model else "",
            "No registered model is linked to this artifact",
        ),
        _check(
            "parent_exists",
            "Lineage links are intact",
            lineage_ok,
            f"Chain of {lineage.depth + 1} artifact(s) reaches its GENERATED origin",
            "A parent artifact is missing or the chain loops",
        ),
        _check(
            "transformation_valid",
            "Transformation fingerprints are consistent",
            evidence.transformation_valid,
            "Transformation fingerprint is within the allowed distance",
            "Parent/child fingerprints are inconsistent",
        ),
        _check(
            "signature_valid",
            "Provenance signature valid",
            evidence.signature_valid,
            "ECDSA signature verified against the stored public key",
            "Signature invalid",
        ),
        _check(
            "blockchain_record",
            "On-chain records are consistent",
            evidence.blockchain_record,
            "Model, artifact and provenance commitments verified on-chain",
            "One or more on-chain commitments are missing or mismatched",
        ),
        _check(
            "revoked",
            "Not revoked",
            None if evidence.revoked is None else (not evidence.revoked),
            "Not revoked",
            "Model or provenance claim is revoked",
        ),
        _check(
            "creator_verified",
            "Proof of Creator (Biometric Authorization)",
            evidence.creator_verified,
            f"Authorized by {model.creator_name} ({creator_commitment[:14]}…)" if (model and creator_commitment) else "Biometric identity authorization confirmed",
            "Self-asserted (no biometric Proof of Creator authorization attached)",
        ),
    ]

    report = VerificationReport(
        exact_hash=exact_hash,
        artifact=artifact,
        model=model,
        lineage=lineage,
        evidence=evidence,
        checks=checks,
        decision=decision,
        blockchain=chain_status,
        creator_identity=creator_ident_info,
        verified_at=now,
    )

    store.log_audit(
        action="VERIFICATION_PERFORMED",
        actor="Verifier",
        resource_id=artifact.artifact_id,
        details={
            "status": decision.status.value,
            "exact_hash": exact_hash,
            "creator_verified": evidence.creator_verified,
            "blockchain_record": evidence.blockchain_record,
        },
    )

    return report
