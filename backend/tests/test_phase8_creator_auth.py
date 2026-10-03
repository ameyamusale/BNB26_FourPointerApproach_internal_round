"""Tests for Phase 8: Proof of Creator (Facial Biometric Authentication & Authorization).

Validates:
- Face detection and multi-factor liveness analysis
- Anti-spoofing rejection of flat/corrupt probes
- Privacy-preserving biometric commitment (no raw vectors on-chain)
- Creator enrollment and profile retrieval
- Live face matching against enrolled template (similarity score threshold)
- Cryptographic authorization token generation and HMAC validation
- Model registration bound to Proof of Creator
- End-to-end artifact verification with biometric Proof of Creator evidence
- Adversarial attack scenario: biometric spoof / impersonation attack
"""
import io
import uuid
import pytest
from PIL import Image

from models.artifact import ArtifactType
from models.claims import TrustStatus
from models.model import RegisterModelRequest
from models.provenance import CreateEventRequest, ProvenanceAction
from services import adversarial, artifact_registry, creator_auth, model_registry, provenance, verification
from services.store import store


def _make_face_image(base_color=(190, 140, 110), size=(64, 64)) -> bytes:
    """Create a synthetic face image fixture with eyes and mouth features."""
    img = Image.new("RGB", size, base_color)
    # Eyes
    for y in range(18, 26):
        for x in (18, 19, 44, 45):
            img.putpixel((x, y), (20, 20, 20))
    # Nose gradient
    for y in range(28, 38):
        img.putpixel((32, y), (140, 90, 60))
    # Mouth
    for y in range(42, 48):
        for x in range(22, 42):
            img.putpixel((x, y), (150, 40, 40))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_flat_spoof(color=(0, 255, 0), size=(64, 64)) -> bytes:
    """Create a flat synthetic spoof image (no facial texture or structure)."""
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_face_detection_and_embedding():
    face_bytes = _make_face_image()
    det = creator_auth.detect_face(face_bytes)
    assert det["detected"] is True
    assert det["face_crop"] is not None
    assert len(det["box"]) == 4

    emb = creator_auth.extract_face_embedding(det["face_crop"])
    assert len(emb) == 256
    # Vector is unit normalized
    import numpy as np
    norm = np.linalg.norm(emb)
    assert abs(norm - 1.0) < 1e-4


def test_liveness_analysis_live_vs_flat():
    face_bytes = _make_face_image()
    live_res = creator_auth.analyze_liveness(face_bytes)
    assert "liveness_score" in live_res
    assert "signals" in live_res
    assert live_res["signals"]["laplacian_variance"] > 0

    flat_bytes = _make_flat_spoof()
    flat_res = creator_auth.analyze_liveness(flat_bytes)
    # Flat image has zero texture variance and should fail or score extremely low
    assert flat_res["signals"]["laplacian_variance"] < 10.0


def test_creator_enrollment():
    uid = uuid.uuid4().hex[:6]
    cid = f"CRT-DEV-{uid}"
    face_bytes = _make_face_image()

    enroll = creator_auth.enroll_creator(cid, "Alice Tester", face_bytes, "0x1234567890123456789012345678901234567890")
    assert enroll["creator_id"] == cid
    assert enroll["name"] == "Alice Tester"
    assert enroll["biometric_commitment"].startswith("0x")
    assert len(enroll["biometric_commitment"]) == 66  # 0x + 64 hex chars
    assert enroll["status"] == "ENROLLED"

    # Stored in store
    ident = store.get_identity(cid)
    assert ident is not None
    assert ident["biometric_enrollment_reference"] is not None


def test_biometric_verification_match_and_mismatch():
    uid = uuid.uuid4().hex[:6]
    cid = f"CRT-TEST-{uid}"
    face1 = _make_face_image(base_color=(190, 140, 110))
    creator_auth.enroll_creator(cid, "Bob Builder", face1)

    # 1. Matching probe (same face)
    probe_match = creator_auth.verify_creator_face(cid, face1)
    assert probe_match["matched"] is True
    assert probe_match["similarity"] >= 0.95
    assert probe_match["verdict"] == "VERIFIED"

    # 2. Non-matching probe (different face / spoof)
    spoof = _make_flat_spoof(color=(50, 50, 200))
    probe_mismatch = creator_auth.verify_creator_face(cid, spoof)
    assert probe_mismatch["matched"] is False


def test_authorization_token_flow():
    uid = uuid.uuid4().hex[:6]
    cid = f"CRT-AUTH-{uid}"
    face = _make_face_image()
    creator_auth.enroll_creator(cid, "Carol Singer", face)

    # Issue token
    auth = creator_auth.authorize_creator(cid, face)
    assert auth["status"] == "AUTHORIZED"
    token = auth["authorization_token"]
    assert token is not None

    # Validate token
    token_info = creator_auth.validate_authorization_token(token)
    assert token_info is not None
    assert token_info["creator_id"] == cid
    assert token_info["creator_name"] == "Carol Singer"
    assert token_info["biometric_commitment"] == auth["biometric_commitment"]

    # Forged token is rejected
    assert creator_auth.validate_authorization_token("forged.token.data") is None
    tampered_token = token[:-5] + "XXXXX"
    assert creator_auth.validate_authorization_token(tampered_token) is None


def test_model_registration_with_proof_of_creator(png):
    uid = uuid.uuid4().hex[:6]
    cid = f"CRT-POC-{uid}"
    face = _make_face_image()
    creator_auth.enroll_creator(cid, "Dave Architect", face)
    auth = creator_auth.authorize_creator(cid, face)

    # Register model using valid Proof of Creator token
    req = RegisterModelRequest(
        name=f"CreatorModel-{uid}",
        version="1.0",
        creator_name="Dave Architect",
        creator_auth_token=auth["authorization_token"],
    )
    model = model_registry.register_model(req)
    assert model.creator_verified is True
    assert model.biometric_commitment == auth["biometric_commitment"]

    # Register artifact from this model
    art = artifact_registry.register_artifact(png((60, 70, 80)), ArtifactType.IMAGE, model_id=model.model_id)
    provenance.add_event(
        CreateEventRequest(
            child_artifact_id=art.artifact_id,
            action=ProvenanceAction.GENERATED,
            model_id=model.model_id,
            creator_auth_token=auth["authorization_token"],
        )
    )

    # Verify artifact: Proof of Creator check passes!
    report = verification.verify_bytes(png((60, 70, 80)))
    assert report.evidence.creator_verified is True
    assert report.evidence.creator_biometric_commitment == auth["biometric_commitment"]

    poc_check = next((c for c in report.checks if c.key == "creator_verified"), None)
    assert poc_check is not None
    assert poc_check.state == "pass"
    assert "Dave Architect" in poc_check.detail
    assert "PROOF_OF_CREATOR_VERIFIED" in report.decision.flags


def test_adversarial_biometric_spoof_attack():
    res = adversarial.run("biometric-spoof")
    assert res["scenario"] == "biometric-spoof"
    v = res["verification"]
    assert v["decision"]["status"] == "REJECTED"
    assert "SPOOF_DETECTED" in v["decision"]["flags"]
    assert any(c["key"] == "biometric_match" and c["state"] == "fail" for c in v["checks"])
