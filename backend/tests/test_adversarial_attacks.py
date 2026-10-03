"""Adversarial and Failure Scenario Tests (Section 16).

Verifies the 7 required attack scenarios:
- Attack 1: Tampered artifact
- Attack 2: Forged provenance claim
- Attack 3: Missing provenance step
- Attack 4: Conflicting claims
- Attack 5: Revoked model
- Attack 6: Invalid signature
- Attack 7: Unauthorized blockchain mutation
"""
import io
import uuid
import pytest
from datetime import datetime, timezone
from PIL import Image
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

import config
from models.artifact import ArtifactType
from models.claims import TrustStatus, VerificationEvidence
from models.model import RegisterModelRequest
from models.provenance import CreateEventRequest, ProvenanceAction, ProvenanceEvent
from services import artifact_registry, blockchain, model_registry, provenance, signature, verification
from services.store import store

HARDHAT_RPC = "http://127.0.0.1:8545"
DEPLOYED_CONTRACT = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
HARDHAT_DEV_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
HARDHAT_UNAUTHORIZED_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"  # Hardhat Account #1


@pytest.fixture
def chain_and_crypto_env(monkeypatch):
    monkeypatch.setattr(config, "BLOCKCHAIN_RPC_URL", HARDHAT_RPC)
    monkeypatch.setattr(config, "CONTRACT_ADDRESS", DEPLOYED_CONTRACT)
    monkeypatch.setattr(config, "BLOCKCHAIN_TX_PRIVATE_KEY", HARDHAT_DEV_KEY)

    key = ec.generate_private_key(ec.SECP256K1())
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    monkeypatch.setattr(config, "SIGNATURE_PRIVATE_KEY_PEM", pem)


def test_attack_1_tampered_artifact(chain_and_crypto_env, png):
    """Attack 1: Register an artifact, modify the file, and verify.

    Expected:
    - Exact hash mismatch
    - NOT falsely TRUSTED
    - Result is UNVERIFIABLE
    """
    uid = uuid.uuid4().hex[:6]
    model = model_registry.register_model(RegisterModelRequest(name=f"Atk1Model-{uid}", version="1.0", creator_name="Dev"))
    original_bytes = png((100, 150, 200), size=(16, 16))
    art = artifact_registry.register_artifact(original_bytes, ArtifactType.IMAGE, model_id=model.model_id)
    provenance.add_event(CreateEventRequest(child_artifact_id=art.artifact_id, action=ProvenanceAction.GENERATED, model_id=model.model_id))

    # Tamper with the artifact: alter pixels
    tampered_bytes = png((101, 150, 200), size=(16, 16))

    report = verification.verify_bytes(tampered_bytes)
    assert report.evidence.artifact_match is False
    assert report.decision.status == TrustStatus.UNVERIFIABLE
    assert report.decision.status != TrustStatus.TRUSTED
    assert report.artifact is None


def test_attack_2_forged_provenance_claim(chain_and_crypto_env, png):
    """Attack 2: An attacker modifies a provenance claim to assert a different model without a valid signature.

    Expected:
    - Signature invalid / claim unsupported
    - CONFLICT / Inconsistent trust state
    """
    uid = uuid.uuid4().hex[:6]
    m1 = model_registry.register_model(RegisterModelRequest(name=f"RealModel-{uid}", version="1.0", creator_name="Dev"))
    m2 = model_registry.register_model(RegisterModelRequest(name=f"ForgedModel-{uid}", version="1.0", creator_name="Attacker"))

    art = artifact_registry.register_artifact(png((50, 50, 50)), ArtifactType.IMAGE, model_id=m1.model_id)
    event = provenance.add_event(CreateEventRequest(child_artifact_id=art.artifact_id, action=ProvenanceAction.GENERATED, model_id=m1.model_id))

    # Attacker tries to forge the event to point to m2 in the database without re-signing with creator key
    with store.lock, store._connect() as conn:
        conn.execute("UPDATE provenance_events SET model_id=? WHERE event_id=?", (m2.model_id, event.event_id))
        conn.commit()

    report = verification.verify_bytes(png((50, 50, 50)))
    assert report.evidence.signature_valid is False
    assert report.decision.status == TrustStatus.CONFLICT
    assert "INCONSISTENT" in report.decision.flags


def test_attack_3_missing_provenance_step(chain_and_crypto_env, png):
    """Attack 3: Remove or break a provenance step in the lineage.

    Expected:
    - Broken lineage detected
    - Inconsistent / CONFLICT result
    """
    uid = uuid.uuid4().hex[:6]
    m = model_registry.register_model(RegisterModelRequest(name=f"LineageModel-{uid}", version="1.0", creator_name="Dev"))
    art1 = artifact_registry.register_artifact(png((10, 10, 10)), ArtifactType.IMAGE, model_id=m.model_id)
    provenance.add_event(CreateEventRequest(child_artifact_id=art1.artifact_id, action=ProvenanceAction.GENERATED, model_id=m.model_id))

    art2 = artifact_registry.register_artifact(png((20, 20, 20)), ArtifactType.IMAGE, model_id=m.model_id)
    provenance.add_event(CreateEventRequest(parent_artifact_id=art1.artifact_id, child_artifact_id=art2.artifact_id, action=ProvenanceAction.UPSCALED, model_id=m.model_id))

    # Break lineage: parent artifact is removed from database
    with store.lock, store._connect() as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM artifacts WHERE artifact_id=?", (art1.artifact_id,))
        conn.commit()

    report = verification.verify_bytes(png((20, 20, 20)))
    assert report.evidence.parent_exists is False
    assert report.decision.status == TrustStatus.CONFLICT


def test_attack_4_conflicting_claims(chain_and_crypto_env, png):
    """Attack 4: Create competing, incompatible provenance claims for the same artifact.

    Expected:
    - Provenance conflict detected
    - CONFLICT trust status
    """
    uid = uuid.uuid4().hex[:6]
    m = model_registry.register_model(RegisterModelRequest(name=f"ConflictModel-{uid}", version="1.0", creator_name="Dev"))
    art = artifact_registry.register_artifact(png((80, 80, 80)), ArtifactType.IMAGE, model_id=m.model_id)
    provenance.add_event(CreateEventRequest(child_artifact_id=art.artifact_id, action=ProvenanceAction.GENERATED, model_id=m.model_id))

    # Register competing claims in the claims store
    store.upsert_identity("CRT-DEV-1", "Dev 1")
    store.upsert_identity("CRT-DEV-2", "Dev 2")
    store.create_claim("CLM-CONF-1", art.artifact_id, "ORIGIN_CLAIM", "CRT-DEV-1", "CRYPTO", "sig1", "ACTIVE")
    store.create_claim("CLM-CONF-2", art.artifact_id, "ORIGIN_CLAIM", "CRT-DEV-2", "CRYPTO", "sig2", "ACTIVE")

    report = verification.verify_bytes(png((80, 80, 80)))
    assert report.decision.status == TrustStatus.CONFLICT
    assert any("Multiple competing issuers" in r for r in report.decision.reasons)


def test_attack_5_revoked_model(chain_and_crypto_env, png):
    """Attack 5: Register model, create provenance, revoke model.

    Expected:
    - Provenance history exists
    - Revoked state is visible
    - Result is NOT TRUSTED (downgraded to SELF_ASSERTED with REVOKED flag)
    """
    uid = uuid.uuid4().hex[:6]
    m = model_registry.register_model(RegisterModelRequest(name=f"RevModel-{uid}", version="1.0", creator_name="Dev"))
    art = artifact_registry.register_artifact(png((90, 90, 90)), ArtifactType.IMAGE, model_id=m.model_id)
    provenance.add_event(CreateEventRequest(child_artifact_id=art.artifact_id, action=ProvenanceAction.GENERATED, model_id=m.model_id))

    # Revoke model both in store and on blockchain
    store.revoke_model(m.model_id)
    blockchain.revoke_model(m.model_id)

    report = verification.verify_bytes(png((90, 90, 90)))
    assert report.evidence.revoked is True
    assert report.decision.status != TrustStatus.TRUSTED
    assert report.decision.status == TrustStatus.SELF_ASSERTED
    assert "REVOKED" in report.decision.flags


def test_attack_6_invalid_signature():
    """Attack 6: Modifying the signed payload directly causes signature verification failure.

    Expected:
    - Signature verification failure
    """
    key = ec.generate_private_key(ec.SECP256K1())
    now = datetime.now(timezone.utc)
    ev = ProvenanceEvent(
        event_id="EVT-ATK-6",
        parent_artifact_id=None,
        child_artifact_id="ART-ATK-6",
        model_id="MDL-ATK-6",
        action=ProvenanceAction.GENERATED,
        metadata_hash="11" * 32,
        created_at=now,
    )
    # Sign original payload
    payload = signature.canonical_event_payload(ev)
    sig = key.sign(payload, ec.ECDSA(signature.hashes.SHA256()))
    import base64
    sig_b64 = base64.b64encode(sig).decode()
    pub_bytes = key.public_key().public_bytes(signature.serialization.Encoding.PEM, signature.serialization.PublicFormat.SubjectPublicKeyInfo)
    pub_b64 = base64.b64encode(pub_bytes).decode()

    ev_signed = ev.model_copy(update={"signature": sig_b64, "signature_public_key": pub_b64})
    assert signature.verify_event_signature(ev_signed, pub_b64) is True

    # Tamper with action
    ev_tampered = ev_signed.model_copy(update={"action": ProvenanceAction.UPSCALED})
    assert signature.verify_event_signature(ev_tampered, pub_b64) is False


def test_attack_7_unauthorized_blockchain_mutation(monkeypatch, png):
    """Attack 7: An unauthorized account attempts to revoke a model owned by another issuer.

    Expected:
    - Blockchain transaction reverted / rejected
    """
    # 1. Register with authorized owner (Account #0)
    monkeypatch.setattr(config, "BLOCKCHAIN_RPC_URL", HARDHAT_RPC)
    monkeypatch.setattr(config, "CONTRACT_ADDRESS", DEPLOYED_CONTRACT)
    monkeypatch.setattr(config, "BLOCKCHAIN_TX_PRIVATE_KEY", HARDHAT_DEV_KEY)

    uid = uuid.uuid4().hex[:6]
    model = model_registry.register_model(RegisterModelRequest(name=f"SecureModel-{uid}", version="1.0", creator_name="Owner"))
    assert model.blockchain_tx is not None

    # 2. Try to revoke using unauthorized key (Account #1)
    monkeypatch.setattr(config, "BLOCKCHAIN_TX_PRIVATE_KEY", HARDHAT_UNAUTHORIZED_KEY)
    rev_res = blockchain.revoke_model(model.model_id)

    assert rev_res["committed"] is False
    assert rev_res["success"] is False
    assert "Not model issuer" in str(rev_res.get("reason", ""))
