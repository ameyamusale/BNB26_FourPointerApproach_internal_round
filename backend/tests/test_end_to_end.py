"""End-to-end integration test verifying the complete 17-step ModelLedger workflow.

Executes live:
- Off-chain SQLite database
- Local Hardhat blockchain node & smart contract deployment
- ECDSA secp256k1 digital signatures
- Exact SHA-256 and robust perceptual fingerprints
- Two-model transformation pipeline (Model A generator -> Artifact A -> Model B upscaler -> Artifact B)
- End-to-end verification producing TRUSTED trust status
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
from models.claims import TrustStatus
from models.model import RegisterModelRequest
from models.provenance import CreateEventRequest, ProvenanceAction
from services import artifact_registry, blockchain, model_registry, provenance, signature, verification
from services.fingerprint import compute_robust_fingerprint
from services.hashing import sha256_bytes
from services.store import store

HARDHAT_RPC = "http://127.0.0.1:8545"
DEPLOYED_CONTRACT = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
HARDHAT_DEV_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


@pytest.fixture
def e2e_env(monkeypatch):
    # Setup blockchain configuration
    monkeypatch.setattr(config, "BLOCKCHAIN_RPC_URL", HARDHAT_RPC)
    monkeypatch.setattr(config, "CONTRACT_ADDRESS", DEPLOYED_CONTRACT)
    monkeypatch.setattr(config, "BLOCKCHAIN_TX_PRIVATE_KEY", HARDHAT_DEV_KEY)

    # Setup ECDSA secp256k1 signing key
    key = ec.generate_private_key(ec.SECP256K1())
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    monkeypatch.setattr(config, "SIGNATURE_PRIVATE_KEY_PEM", pem)


def test_complete_end_to_end_workflow(e2e_env):
    uid = uuid.uuid4().hex[:6]

    # --- STEP 1: Register Creator / Identity ---
    creator_id = f"CRT-E2E-{uid}"
    store.upsert_identity(
        identity_id=creator_id,
        name="Lead AI Studio",
        role="CREATOR",
        wallet_address="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
    )
    ident = store.get_identity(creator_id)
    assert ident is not None
    assert ident["name"] == "Lead AI Studio"

    # --- STEP 2: Register Model A ---
    model_a_req = RegisterModelRequest(
        name=f"VisionGen-Alpha-{uid}",
        version="1.0.0",
        model_type="text-to-image",
        creator_name="Lead AI Studio",
        description="Generative foundation model",
    )
    model_a = model_registry.register_model(model_a_req)
    assert model_a.model_id.startswith("MDL-")
    assert model_a.blockchain_tx is not None

    # --- STEP 3: Model Commitment on Blockchain ---
    assert blockchain.has_record("model", model_a.model_id, model_a.model_hash) is True

    # --- STEP 4: Create Artifact A (Generated image) ---
    img_a = Image.new("RGB", (48, 48), (30, 60, 120))
    for x in range(12, 36):
        for y in range(12, 36):
            img_a.putpixel((x, y), (240, 190, 40))
    buf_a = io.BytesIO()
    img_a.save(buf_a, format="PNG")
    artifact_a_bytes = buf_a.getvalue()

    # --- STEP 5: Calculate SHA-256 ---
    hash_a = sha256_bytes(artifact_a_bytes)

    # --- STEP 6: Calculate Robust Fingerprint ---
    fp_a = compute_robust_fingerprint(artifact_a_bytes)
    assert fp_a is not None

    # Register Artifact A in registry (auto-commits to chain)
    art_a = artifact_registry.register_artifact(artifact_a_bytes, ArtifactType.IMAGE, model_id=model_a.model_id)
    assert art_a.exact_hash == hash_a
    assert art_a.blockchain_tx is not None

    # --- STEP 7 & 8 & 9: Create Provenance Claim, Sign Claim, Commit to Blockchain ---
    event_a = provenance.add_event(
        CreateEventRequest(
            child_artifact_id=art_a.artifact_id,
            action=ProvenanceAction.GENERATED,
            model_id=model_a.model_id,
            metadata={"prompt_commitment": "high resolution cosmic panorama"},
        )
    )
    assert event_a.signature is not None
    assert event_a.signature_public_key is not None
    assert event_a.blockchain_tx is not None

    # --- STEP 10: Create Transformation through Model B ---
    model_b_req = RegisterModelRequest(
        name=f"ClarityEnhance-Beta-{uid}",
        version="2.0.0",
        model_type="super-resolution",
        creator_name="Lead AI Studio",
        description="Upscaler & Detail Enhancer",
    )
    model_b = model_registry.register_model(model_b_req)
    assert model_b.blockchain_tx is not None

    # Upscale / legitimate transformation of Artifact A -> Artifact B
    img_b = img_a.resize((64, 64), Image.Resampling.LANCZOS)
    buf_b = io.BytesIO()
    img_b.save(buf_b, format="PNG")
    artifact_b_bytes = buf_b.getvalue()

    # --- STEP 11: Create Artifact B ---
    hash_b = sha256_bytes(artifact_b_bytes)
    assert hash_b != hash_a  # Exact hash changed due to resize
    art_b = artifact_registry.register_artifact(artifact_b_bytes, ArtifactType.IMAGE, model_id=model_b.model_id)
    assert art_b.blockchain_tx is not None

    # --- STEP 12 & 13: Create Signed Transformation Event and Commit to Blockchain ---
    event_b = provenance.add_event(
        CreateEventRequest(
            parent_artifact_id=art_a.artifact_id,
            child_artifact_id=art_b.artifact_id,
            action=ProvenanceAction.UPSCALED,
            model_id=model_b.model_id,
            application_id="StudioPipeline-v1",
            metadata={"scale_factor": 1.33},
        )
    )
    assert event_b.signature is not None
    assert event_b.blockchain_tx is not None

    # --- STEP 14: Verifier uploads final Artifact B ---
    report = verification.verify_bytes(artifact_b_bytes)

    # --- STEP 15: Reconstruct Lineage ---
    assert report.lineage is not None
    assert [s.artifact_id for s in report.lineage.steps] == [art_a.artifact_id, art_b.artifact_id]
    assert report.lineage.depth == 1
    assert report.lineage.root_reached is True
    assert not report.lineage.issues

    # --- STEP 16: Verify All Evidence ---
    evidence = report.evidence
    assert evidence.artifact_match is True
    assert evidence.model_registered is True
    assert evidence.signature_valid is True
    assert evidence.parent_exists is True
    assert evidence.transformation_valid is True
    assert evidence.blockchain_record is True
    assert evidence.revoked is False

    # Check evidence checks
    check_states = {c.key: c.state for c in report.checks}
    assert check_states["artifact_match"] == "pass"
    assert check_states["model_registered"] == "pass"
    assert check_states["parent_exists"] == "pass"
    assert check_states["transformation_valid"] == "pass"
    assert check_states["signature_valid"] == "pass"
    assert check_states["blockchain_record"] == "pass"
    assert check_states["revoked"] == "pass"

    # --- STEP 17: Produce Final Trust Status ---
    assert report.decision.status == TrustStatus.TRUSTED
    assert "All required evidence is present, consistent and verified." in report.decision.reasons
