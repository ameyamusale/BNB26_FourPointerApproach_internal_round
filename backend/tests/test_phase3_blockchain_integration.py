"""Tests for Phase 3 Blockchain Integration.

Validates:
- Real connection to local Hardhat node & deployed ModelLedgerRegistry contract
- On-chain model registration, tx receipt, stored tx hash, and on-chain retrieval
- On-chain artifact registration, tx receipt, stored tx hash, and on-chain retrieval
- On-chain provenance event, tx receipt, stored tx hash, and on-chain retrieval
- Model revocation and claim revocation on-chain
- Consistency between off-chain database and on-chain state
- Explicit offline mode behavior: never fakes successful verification
"""
import uuid
import pytest
from datetime import datetime, timezone
import config
from models.artifact import ArtifactType
from models.model import RegisterModelRequest
from models.provenance import CreateEventRequest, ProvenanceAction
from services import artifact_registry, blockchain, model_registry, provenance, signature, verification
from services.hashing import sha256_bytes

HARDHAT_RPC = "http://127.0.0.1:8545"
DEPLOYED_CONTRACT = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
HARDHAT_DEV_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


@pytest.fixture
def chain_env(monkeypatch):
    monkeypatch.setattr(config, "BLOCKCHAIN_RPC_URL", HARDHAT_RPC)
    monkeypatch.setattr(config, "CONTRACT_ADDRESS", DEPLOYED_CONTRACT)
    monkeypatch.setattr(config, "BLOCKCHAIN_TX_PRIVATE_KEY", HARDHAT_DEV_KEY)


def test_blockchain_status_connected(chain_env):
    st = blockchain.status()
    assert st["connected"] is True
    assert st["mode"] == "on-chain"
    assert st["contract_address"].lower() == DEPLOYED_CONTRACT.lower()
    assert "block" in st
    assert st["chain_id"] == 31337  # Hardhat chain id


def test_blockchain_offline_mode_reports_explicit_offline(monkeypatch):
    monkeypatch.setattr(config, "BLOCKCHAIN_RPC_URL", "")
    monkeypatch.setattr(config, "CONTRACT_ADDRESS", "")
    st = blockchain.status()
    assert st["connected"] is False
    assert st["mode"] == "offline"
    assert blockchain.has_record("model", "MDL-TEST") is None
    assert blockchain.has_record("artifact", "ART-TEST") is None
    assert blockchain.has_record("provenance", "EVT-TEST") is None


def test_model_registration_on_chain(chain_env):
    uid = uuid.uuid4().hex[:6]
    req = RegisterModelRequest(name=f"ChainModel-{uid}", version="1.0.0", creator_name="Chain Dev")
    model = model_registry.register_model(req)

    assert model.blockchain_tx is not None
    assert model.blockchain_tx.startswith("0x")

    # Verify on-chain record via has_record
    assert blockchain.has_record("model", model.model_id, model.model_hash) is True

    # Retrieve full struct directly from smart contract
    on_chain = blockchain.get_model(model.model_id)
    assert on_chain is not None
    assert on_chain["model_hash"] == model.model_hash
    assert on_chain["revoked"] is False


def test_artifact_registration_on_chain(chain_env, png):
    uid = uuid.uuid4().hex[:6]
    model = model_registry.register_model(RegisterModelRequest(name=f"ArtModel-{uid}", version="1.0", creator_name="Dev"))
    data = png((12, 34, 56))
    art = artifact_registry.register_artifact(data, ArtifactType.IMAGE, model_id=model.model_id)

    assert art.blockchain_tx is not None
    assert art.blockchain_tx.startswith("0x")

    # Verify on-chain via has_record
    assert blockchain.has_record("artifact", art.artifact_id, art.exact_hash) is True

    # Retrieve full struct directly from smart contract
    on_chain = blockchain.get_artifact(art.artifact_id)
    assert on_chain is not None
    assert on_chain["exact_hash"] == art.exact_hash
    assert on_chain["model_id"] == model.model_id
    assert on_chain["revoked"] is False


def test_provenance_event_on_chain(chain_env, png):
    uid = uuid.uuid4().hex[:6]
    model = model_registry.register_model(RegisterModelRequest(name=f"ProvModel-{uid}", version="1.0", creator_name="Dev"))
    art1 = artifact_registry.register_artifact(png((10, 20, 30)), ArtifactType.IMAGE, model_id=model.model_id)
    art2 = artifact_registry.register_artifact(png((40, 50, 60)), ArtifactType.IMAGE, model_id=model.model_id)

    event = provenance.add_event(
        CreateEventRequest(
            parent_artifact_id=art1.artifact_id,
            child_artifact_id=art2.artifact_id,
            action=ProvenanceAction.UPSCALED,
            model_id=model.model_id,
            application_id="ChainUpscaler",
        )
    )

    assert event.blockchain_tx is not None
    assert event.blockchain_tx.startswith("0x")

    # Check on-chain validity
    claim = signature.claim_hash(event)
    assert blockchain.has_record("provenance", event.event_id, claim) is True

    # Retrieve on-chain event details
    on_chain_event = blockchain.get_provenance_event(event.event_id)
    assert on_chain_event is not None
    assert on_chain_event["child_artifact_id"] == art2.artifact_id
    assert on_chain_event["parent_artifact_id"] == art1.artifact_id
    assert on_chain_event["action"] == "UPSCALED"
    assert on_chain_event["revoked"] is False

    # Check artifact event IDs array
    events_list = blockchain.get_artifact_events(art2.artifact_id)
    assert events_list is not None
    assert event.event_id in events_list


def test_revocation_on_chain(chain_env, png):
    uid = uuid.uuid4().hex[:6]
    model = model_registry.register_model(RegisterModelRequest(name=f"RevokeModel-{uid}", version="1.0", creator_name="Dev"))
    art = artifact_registry.register_artifact(png((77, 88, 99)), ArtifactType.IMAGE, model_id=model.model_id)
    event = provenance.add_event(CreateEventRequest(child_artifact_id=art.artifact_id, action=ProvenanceAction.GENERATED, model_id=model.model_id))

    # Revoke model on-chain
    rev_model_res = blockchain.revoke_model(model.model_id)
    assert rev_model_res["committed"] is True
    assert blockchain.is_revoked_model(model.model_id) is True

    # Revoke claim on-chain
    rev_claim_res = blockchain.revoke_claim(event.event_id)
    assert rev_claim_res["committed"] is True
    assert blockchain.is_revoked_claim(event.event_id) is True
