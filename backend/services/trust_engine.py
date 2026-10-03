"""Trust Engine: maps structured evidence to a trust state (Phases 4, 7, 8)."""
from __future__ import annotations

from typing import List

from models.claims import TrustDecision, TrustStatus, VerificationEvidence


def evaluate(evidence: VerificationEvidence, conflicts: List[str] | None = None) -> TrustDecision:
    reasons: List[str] = []
    flags: List[str] = []
    conflicts = conflicts or []

    # 1. Contradictions always win.
    contradictions = list(conflicts)
    if evidence.signature_valid is False:
        contradictions.append("A provenance signature failed validation")
    if evidence.parent_exists is False:
        contradictions.append("Lineage is broken: a referenced parent artifact is missing")
    if evidence.transformation_valid is False:
        contradictions.append("A recorded transformation does not match the artifacts")
    if contradictions:
        return TrustDecision(status=TrustStatus.CONFLICT, reasons=contradictions, flags=["INCONSISTENT"])

    # 2. Nothing registered -> we cannot say anything about the origin.
    if not evidence.artifact_match:
        return TrustDecision(
            status=TrustStatus.UNVERIFIABLE,
            reasons=["No registered artifact matches these exact bytes, so no provenance can be established."],
        )

    # 3. A claim exists. Is it backed by enough evidence?
    if evidence.revoked:
        flags.append("REVOKED")
        reasons.append("The originating model or claim has been revoked; the history is kept but no longer trusted.")

    if evidence.creator_verified is True:
        flags.append("PROOF_OF_CREATOR_VERIFIED")
        reasons.append("Claimed origin is authorized by biometric Proof of Creator.")

    required = {
        "model is registered": evidence.model_registered,
        "signature is valid": evidence.signature_valid,
        "blockchain record exists": evidence.blockchain_record,
        "not revoked": None if evidence.revoked is None else (not evidence.revoked),
    }
    missing = [name for name, ok in required.items() if ok is not True]

    if not missing:
        trusted_reasons = ["All required evidence is present, consistent and verified."]
        if "PROOF_OF_CREATOR_VERIFIED" in flags:
            trusted_reasons.append("Biometric Proof of Creator confirmed and bound to cryptographic provenance.")
        return TrustDecision(
            status=TrustStatus.TRUSTED,
            reasons=trusted_reasons,
            flags=flags,
        )

    for name in missing:
        state = required[name]
        reasons.append(f"Not established: {name}" + (" (not checked yet)" if state is None else " (failed)"))
    return TrustDecision(status=TrustStatus.SELF_ASSERTED, reasons=reasons, flags=flags)
