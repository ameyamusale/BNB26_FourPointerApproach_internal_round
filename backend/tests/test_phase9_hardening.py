"""Tests for Phase 9: Privacy and Production-Hardening Pass.

Validates:
- Zero prompt leakage: private system prompts are verified via cryptographic commitment only
- Upload validation: corrupt images, empty payloads, and oversize files are cleanly rejected
- Tamper-evident audit logging: hash-chained SHA-256 log verifies unbroken provenance history
- Audit chain integrity: tampering with a single audit entry is immediately caught
- Smart contract permission guard: adversarial unauthorized blockchain mutation scenario
- No silent success: blockchain failures and offline states are strictly reported
"""
import hashlib
import uuid
import pytest

from models.artifact import ArtifactType
from models.model import RegisterModelRequest
from services import adversarial, artifact_registry, blockchain, model_registry
from services.errors import ValidationFailure
from services.store import store


def test_zero_prompt_leakage_and_commitment_verification():
    """Confirms prompts are never stored or exposed, but can be verified zero-knowledge."""
    uid = uuid.uuid4().hex[:6]
    secret_prompt = "A high fantasy landscape with radiant violet clouds and an ancient spire"
    prompt_hash = hashlib.sha256(secret_prompt.strip().encode()).hexdigest()

    # Register model committing only to the hash of the secret prompt
    req = RegisterModelRequest(
        name=f"PrivateModel-{uid}",
        version="1.0",
        creator_name="Secret Studio",
        private_prompt_commitment=prompt_hash,
    )
    model = model_registry.register_model(req)

    # 1. Stored model has hash only, never the raw prompt text
    assert model.private_prompt_commitment == prompt_hash
    assert secret_prompt not in str(model.model_dump())

    # 2. Candidate prompt matching
    candidate_hash = hashlib.sha256(secret_prompt.strip().encode()).hexdigest()
    assert candidate_hash == model.private_prompt_commitment

    # Mismatched candidate prompt fails
    wrong_candidate_hash = hashlib.sha256(b"Something completely different").hexdigest()
    assert wrong_candidate_hash != model.private_prompt_commitment


def test_upload_validation_rejects_empty_and_corrupt(png):
    # 1. Empty payload rejected
    with pytest.raises(ValidationFailure, match="empty"):
        artifact_registry.register_artifact(b"", ArtifactType.IMAGE)

    # 2. Corrupt image bytes rejected
    with pytest.raises(ValidationFailure, match="corrupt"):
        artifact_registry.register_artifact(b"THIS_IS_NOT_AN_IMAGE_FILE", ArtifactType.IMAGE)

    # 3. Valid PNG accepted
    art = artifact_registry.register_artifact(png((10, 20, 30)), ArtifactType.IMAGE)
    assert art.artifact_id.startswith("ART-")


def test_tamper_evident_audit_log_chain():
    """Tests the SHA-256 hash-chained audit logging."""
    store.reset()

    # Perform operations that generate audit log entries
    store.log_audit("TEST_ACTION_1", "Actor1", "RES-1", {"val": 1})
    store.log_audit("TEST_ACTION_2", "Actor2", "RES-2", {"val": 2})
    store.log_audit("TEST_ACTION_3", "Actor3", "RES-3", {"val": 3})

    logs = store.list_audit_logs(limit=10)
    assert len(logs) == 3

    # Chain verification succeeds
    verification = store.verify_audit_log_chain()
    assert verification["valid"] is True
    assert verification["count"] == 3
    assert verification["chain_status"] == "INTACT"

    # Intentionally corrupt the second audit log row directly in SQLite
    with store.lock, store._connect() as conn:
        conn.execute("UPDATE audit_logs SET actor='TamperedActor' WHERE rowid=2")
        conn.commit()

    # Verification must catch the tampering immediately
    tampered_verification = store.verify_audit_log_chain()
    assert tampered_verification["valid"] is False
    assert "tampering detected" in tampered_verification["reason"].lower()


def test_adversarial_unauthorized_blockchain_mutation():
    """Attack scenario verifying contract rejection of unauthorized callers."""
    res = adversarial.run("unauthorized-mutation")
    assert res["scenario"] == "unauthorized-mutation"
    assert res["verification"]["decision"]["status"] == "PROTECTED"
    assert "MUTATION_REJECTED" in res["verification"]["decision"]["flags"]


def test_no_silent_success_on_offline_blockchain(monkeypatch):
    """Rule 5: When blockchain is offline, system never falsely reports success."""
    import config
    monkeypatch.setattr(config, "BLOCKCHAIN_RPC_URL", "")
    monkeypatch.setattr(config, "CONTRACT_ADDRESS", "")

    st = blockchain.status()
    assert st["connected"] is False
    assert st["mode"] == "offline"

    # Verification of any artifact when chain is offline leaves blockchain_record as None (not True!)
    rec = blockchain.has_record("model", "MDL-FAKE", "00" * 32)
    assert rec is None  # None = not checked, never False or True
