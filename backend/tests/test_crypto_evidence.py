"""Tests for Phase 4 Cryptographic Evidence Layer.

Covers:
- Exact SHA-256 hashing (Section 10)
- Robust perceptual fingerprinting (Section 11)
- Digital signatures with secp256k1 (Section 12)
- Structured Evidence Object integrity (Section 13)
- Multi-state Trust Classifications (Section 14)
"""
import io
import pytest
from datetime import datetime, timezone
from PIL import Image
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from models.claims import EvidenceCheck, TrustDecision, TrustStatus, VerificationEvidence
from models.provenance import ProvenanceAction, ProvenanceEvent
from services.fingerprint import compute_robust_fingerprint, fingerprint_distance
from services.hashing import canonical_json_hash, is_sha256, sha256_bytes
from services.signature import canonical_event_payload, claim_hash, sign_event, verify_event_signature
from services.trust_engine import evaluate


def _generate_pem_key():
    key = ec.generate_private_key(ec.SECP256K1())
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    return pem


# --- Section 10: Exact Hashing ---

def test_exact_hash_consistency():
    data1 = b"ModelLedger Artifact 001 bytes"
    data2 = b"ModelLedger Artifact 002 bytes"
    data1_copy = b"ModelLedger Artifact 001 bytes"

    # same file -> same hash
    h1 = sha256_bytes(data1)
    h1_copy = sha256_bytes(data1_copy)
    assert h1 == h1_copy
    assert is_sha256(h1)

    # different file -> different hash
    h2 = sha256_bytes(data2)
    assert h1 != h2

    # modified file (even 1 byte changed) -> completely different hash
    modified = bytearray(data1)
    modified[0] ^= 0xFF
    h_mod = sha256_bytes(bytes(modified))
    assert h_mod != h1


# --- Section 11: Robust Fingerprint ---

def test_robust_fingerprint_preserves_legitimate_transformations():
    # Create base image with distinct geometric features
    img = Image.new("RGB", (64, 64), (20, 40, 80))
    for x in range(20, 44):
        for y in range(20, 44):
            img.putpixel((x, y), (220, 180, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    original_bytes = buf.getvalue()

    # Transformation 1: resize to 32x32
    resized_img = img.resize((32, 32), Image.Resampling.LANCZOS)
    buf_resized = io.BytesIO()
    resized_img.save(buf_resized, format="PNG")
    resized_bytes = buf_resized.getvalue()

    # Exact hash MUST change
    assert sha256_bytes(original_bytes) != sha256_bytes(resized_bytes)

    # Robust fingerprint MUST be sufficiently associated
    fp_orig = compute_robust_fingerprint(original_bytes)
    fp_resized = compute_robust_fingerprint(resized_bytes)
    assert fp_orig is not None and fp_resized is not None
    dist = fingerprint_distance(fp_orig, fp_resized)
    assert dist is not None
    assert dist <= 10  # very close for resize

    # Completely unrelated image
    unrelated_img = Image.new("RGB", (64, 64), (255, 255, 255))
    for x in range(0, 64, 2):
        for y in range(0, 64, 2):
            unrelated_img.putpixel((x, y), (0, 0, 0))
    buf_unrelated = io.BytesIO()
    unrelated_img.save(buf_unrelated, format="PNG")
    fp_unrelated = compute_robust_fingerprint(buf_unrelated.getvalue())

    unrelated_dist = fingerprint_distance(fp_orig, fp_unrelated)
    assert unrelated_dist is not None
    assert unrelated_dist > 18  # Not treated as the same content


# --- Section 12: Digital Signatures ---

def test_digital_signatures_flow(monkeypatch):
    pem1 = _generate_pem_key()
    pem2 = _generate_pem_key()

    monkeypatch.setattr("config.SIGNATURE_PRIVATE_KEY_PEM", pem1)

    now = datetime.now(timezone.utc)
    event = ProvenanceEvent(
        event_id="EVT-SIG-1",
        parent_artifact_id="ART-1",
        child_artifact_id="ART-2",
        model_id="MDL-1",
        application_id="App1",
        action=ProvenanceAction.UPSCALED,
        metadata_hash="aa" * 32,
        created_at=now,
    )

    # Valid claim -> sign -> verify -> PASS
    signed = sign_event(event)
    assert signed is not None
    sig_b64, pubkey_b64 = signed
    event_with_sig = event.model_copy(update={"signature": sig_b64, "signature_public_key": pubkey_b64})

    assert verify_event_signature(event_with_sig, pubkey_b64) is True

    # Modified claim -> old signature -> verify -> FAIL
    tampered_event = event_with_sig.model_copy(update={"metadata_hash": "ff" * 32})
    assert verify_event_signature(tampered_event, pubkey_b64) is False

    # Wrong key -> verify -> FAIL
    monkeypatch.setattr("config.SIGNATURE_PRIVATE_KEY_PEM", pem2)
    wrong_key_signed = sign_event(event)
    assert wrong_key_signed is not None
    wrong_sig_b64, _ = wrong_key_signed
    wrong_key_event = event.model_copy(update={"signature": wrong_sig_b64, "signature_public_key": pubkey_b64})
    assert verify_event_signature(wrong_key_event, pubkey_b64) is False

    # Wrong payload / corrupted signature
    corrupted_event = event.model_copy(update={"signature": "bad_signature_bytes", "signature_public_key": pubkey_b64})
    assert verify_event_signature(corrupted_event, pubkey_b64) is False


# --- Section 13: Structured Evidence Object ---

def test_evidence_object_structure():
    ev = VerificationEvidence(
        artifact_match=True,
        model_registered=True,
        signature_valid=True,
        parent_exists=True,
        transformation_valid=True,
        blockchain_record=True,
        revoked=False,
    )
    dumped = ev.model_dump()
    assert dumped["artifact_match"] is True
    assert dumped["model_registered"] is True
    assert dumped["signature_valid"] is True
    assert dumped["parent_exists"] is True
    assert dumped["transformation_valid"] is True
    assert dumped["blockchain_record"] is True
    assert dumped["revoked"] is False

    # Tri-state check: when unchecked, values are None
    ev_unchecked = VerificationEvidence(artifact_match=True)
    assert ev_unchecked.signature_valid is None
    assert ev_unchecked.blockchain_record is None
    assert ev_unchecked.model_registered is None


# --- Section 14: Trust States ---

def test_trust_states_decision_matrix():
    # 1. TRUSTED requires all affirmative evidence
    fully_trusted_ev = VerificationEvidence(
        artifact_match=True,
        model_registered=True,
        signature_valid=True,
        parent_exists=True,
        transformation_valid=True,
        blockchain_record=True,
        revoked=False,
    )
    decision = evaluate(fully_trusted_ev)
    assert decision.status == TrustStatus.TRUSTED

    # 2. Missing blockchain record -> cannot be TRUSTED, must be SELF_ASSERTED
    no_chain_ev = fully_trusted_ev.model_copy(update={"blockchain_record": None})
    decision_no_chain = evaluate(no_chain_ev)
    assert decision_no_chain.status == TrustStatus.SELF_ASSERTED

    # 3. Missing signature -> cannot be TRUSTED
    no_sig_ev = fully_trusted_ev.model_copy(update={"signature_valid": None})
    decision_no_sig = evaluate(no_sig_ev)
    assert decision_no_sig.status == TrustStatus.SELF_ASSERTED

    # 4. Unknown artifact -> UNVERIFIABLE
    unknown_ev = VerificationEvidence(artifact_match=False)
    decision_unknown = evaluate(unknown_ev)
    assert decision_unknown.status == TrustStatus.UNVERIFIABLE

    # 5. CONFLICT / INCONSISTENT on broken signature
    invalid_sig_ev = fully_trusted_ev.model_copy(update={"signature_valid": False})
    decision_invalid_sig = evaluate(invalid_sig_ev)
    assert decision_invalid_sig.status == TrustStatus.CONFLICT
    assert "INCONSISTENT" in decision_invalid_sig.flags

    # 6. CONFLICT on broken lineage
    broken_lineage_ev = fully_trusted_ev.model_copy(update={"parent_exists": False})
    assert evaluate(broken_lineage_ev).status == TrustStatus.CONFLICT

    # 7. Revoked model -> history retained, status SELF_ASSERTED with REVOKED flag
    revoked_ev = fully_trusted_ev.model_copy(update={"revoked": True})
    decision_revoked = evaluate(revoked_ev)
    assert decision_revoked.status == TrustStatus.SELF_ASSERTED
    assert "REVOKED" in decision_revoked.flags
