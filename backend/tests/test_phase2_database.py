"""Phase 2 Database layer tests verifying all 15 specification requirements.

Entities verified:
- models
- artifacts
- provenance_events
- claims
- identities
"""
import sqlite3
import pytest
from datetime import datetime, timezone
from models.artifact import ArtifactRecord, ArtifactStatus, ArtifactType
from models.claims import VerificationEvidence
from models.model import ModelRecord, ModelStatus
from models.provenance import ProvenanceAction, ProvenanceEvent
from services.store import SQLiteStore, store


def test_phase2_1_and_2_create_and_retrieve_model():
    now = datetime.now(timezone.utc)
    store.upsert_identity("CRT-1", "Creator 1", "CREATOR")
    model = ModelRecord(
        model_id="MDL-DB-1",
        name="TestModel",
        version="1.0.0",
        model_type="image-generator",
        creator_id="CRT-1",
        creator_name="Creator 1",
        description="A test model",
        model_hash="11" * 32,
        metadata_hash="22" * 32,
        status=ModelStatus.ACTIVE,
        created_at=now,
    )
    store.insert_model(model)
    retrieved = store.get_model("MDL-DB-1")
    assert retrieved is not None
    assert retrieved.model_id == "MDL-DB-1"
    assert retrieved.name == "TestModel"
    assert retrieved.version == "1.0.0"
    assert retrieved.creator_id == "CRT-1"
    assert retrieved.creator_name == "Creator 1"
    assert retrieved.status == ModelStatus.ACTIVE


def test_phase2_3_update_and_retrieve_status():
    now = datetime.now(timezone.utc)
    model = ModelRecord(
        model_id="MDL-STATUS-1",
        name="StatusModel",
        version="1.0.0",
        model_type="text-to-image",
        creator_id="CRT-STATUS",
        creator_name="Creator Status",
        description=None,
        model_hash="33" * 32,
        metadata_hash="44" * 32,
        status=ModelStatus.ACTIVE,
        created_at=now,
    )
    store.insert_model(model)
    store.update_model_status("MDL-STATUS-1", "REVOKED")
    updated = store.get_model("MDL-STATUS-1")
    assert updated is not None
    assert updated.status == ModelStatus.REVOKED


def test_phase2_4_and_5_create_and_retrieve_artifact():
    now = datetime.now(timezone.utc)
    art = ArtifactRecord(
        artifact_id="ART-DB-1",
        artifact_type=ArtifactType.IMAGE,
        exact_hash="aa" * 32,
        robust_fingerprint="phash:0123456789abcdef",
        size_bytes=1024,
        storage_uri=None,
        model_id=None,
        status=ArtifactStatus.REGISTERED,
        created_at=now,
    )
    store.insert_artifact(art)
    retrieved = store.get_artifact("ART-DB-1")
    assert retrieved is not None
    assert retrieved.artifact_id == "ART-DB-1"
    assert retrieved.exact_hash == "aa" * 32
    assert retrieved.robust_fingerprint == "phash:0123456789abcdef"
    assert retrieved.size_bytes == 1024

    # by hash
    by_hash = store.find_artifact_by_hash("aa" * 32)
    assert by_hash is not None
    assert by_hash.artifact_id == "ART-DB-1"


def test_phase2_6_and_7_create_event_and_retrieve_history():
    now = datetime.now(timezone.utc)
    art1 = ArtifactRecord(
        artifact_id="ART-PARENT",
        artifact_type=ArtifactType.IMAGE,
        exact_hash="bb" * 32,
        robust_fingerprint="phash:1111111111111111",
        size_bytes=2048,
        storage_uri=None,
        model_id=None,
        status=ArtifactStatus.REGISTERED,
        created_at=now,
    )
    art2 = ArtifactRecord(
        artifact_id="ART-CHILD",
        artifact_type=ArtifactType.IMAGE,
        exact_hash="cc" * 32,
        robust_fingerprint="phash:2222222222222222",
        size_bytes=4096,
        storage_uri=None,
        model_id=None,
        status=ArtifactStatus.REGISTERED,
        created_at=now,
    )
    store.insert_artifact(art1)
    store.insert_artifact(art2)

    event = ProvenanceEvent(
        event_id="EVT-HIST-1",
        parent_artifact_id="ART-PARENT",
        child_artifact_id="ART-CHILD",
        model_id=None,
        application_id="App1",
        action=ProvenanceAction.UPSCALED,
        metadata_hash="dd" * 32,
        created_at=now,
    )
    store.insert_event(event)

    child_events = store.events_for_child("ART-CHILD")
    assert len(child_events) == 1
    assert child_events[0].event_id == "EVT-HIST-1"
    assert child_events[0].action == ProvenanceAction.UPSCALED

    art_history = store.events_for_artifact("ART-PARENT")
    assert len(art_history) == 1
    assert art_history[0].event_id == "EVT-HIST-1"


def test_phase2_8_and_9_create_and_retrieve_claim():
    now = datetime.now(timezone.utc)
    art = ArtifactRecord(
        artifact_id="ART-CLAIM-1",
        artifact_type=ArtifactType.IMAGE,
        exact_hash="ee" * 32,
        robust_fingerprint=None,
        size_bytes=512,
        storage_uri=None,
        model_id=None,
        status=ArtifactStatus.REGISTERED,
        created_at=now,
    )
    store.insert_artifact(art)

    evidence = VerificationEvidence(artifact_match=True, model_registered=True, signature_valid=True)
    store.create_claim(
        claim_id="CLM-1",
        artifact_id="ART-CLAIM-1",
        claim_type="PROVENANCE_ORIGIN",
        issuer_id=None,
        evidence_type="CRYPTOGRAPHIC",
        signature="sig_test_base64",
        status="ACTIVE",
        evidence=evidence,
    )

    claim = store.get_claim("CLM-1")
    assert claim is not None
    assert claim["claim_id"] == "CLM-1"
    assert claim["artifact_id"] == "ART-CLAIM-1"
    assert claim["status"] == "ACTIVE"
    assert "artifact_match" in claim["evidence_json"]

    claims_list = store.list_claims("ART-CLAIM-1")
    assert len(claims_list) == 1
    assert claims_list[0]["claim_id"] == "CLM-1"


def test_phase2_10_and_11_create_and_retrieve_identity():
    store.upsert_identity(
        identity_id="ID-CREATOR-99",
        name="Alice Creator",
        role="DEVELOPER",
        wallet_address="0x1111111111111111111111111111111111111111",
    )
    ident = store.get_identity("ID-CREATOR-99")
    assert ident is not None
    assert ident["identity_id"] == "ID-CREATOR-99"
    assert ident["name"] == "Alice Creator"
    assert ident["role"] == "DEVELOPER"
    assert ident["wallet_address"] == "0x1111111111111111111111111111111111111111"
    assert ident["status"] == "ACTIVE"

    all_idents = store.list_identities()
    assert any(i["identity_id"] == "ID-CREATOR-99" for i in all_idents)


def test_phase2_12_parent_child_relationship():
    now = datetime.now(timezone.utc)
    p = ArtifactRecord(
        artifact_id="ART-P",
        artifact_type=ArtifactType.IMAGE,
        exact_hash="10" * 32,
        robust_fingerprint="phash:1234",
        size_bytes=100,
        created_at=now,
    )
    c = ArtifactRecord(
        artifact_id="ART-C",
        artifact_type=ArtifactType.IMAGE,
        exact_hash="20" * 32,
        robust_fingerprint="phash:5678",
        size_bytes=200,
        created_at=now,
    )
    store.insert_artifact(p)
    store.insert_artifact(c)

    ev = ProvenanceEvent(
        event_id="EVT-PC",
        parent_artifact_id="ART-P",
        child_artifact_id="ART-C",
        action=ProvenanceAction.RESIZED,
        metadata_hash="30" * 32,
        created_at=now,
    )
    store.insert_event(ev)

    events = store.events_for_child("ART-C")
    assert len(events) == 1
    assert events[0].parent_artifact_id == "ART-P"


def test_phase2_13_duplicate_handling():
    now = datetime.now(timezone.utc)
    art1 = ArtifactRecord(
        artifact_id="ART-DUP-1",
        artifact_type=ArtifactType.IMAGE,
        exact_hash="dd" * 32,
        robust_fingerprint=None,
        size_bytes=100,
        created_at=now,
    )
    art2 = ArtifactRecord(
        artifact_id="ART-DUP-2",
        artifact_type=ArtifactType.IMAGE,
        exact_hash="dd" * 32,  # same exact hash!
        robust_fingerprint=None,
        size_bytes=100,
        created_at=now,
    )
    store.insert_artifact(art1)
    with pytest.raises(sqlite3.IntegrityError):
        store.insert_artifact(art2)


def test_phase2_14_invalid_references_rejected_by_foreign_keys():
    now = datetime.now(timezone.utc)
    # Child artifact does not exist
    ev = ProvenanceEvent(
        event_id="EVT-INV-REF",
        parent_artifact_id=None,
        child_artifact_id="ART-DOES-NOT-EXIST",
        action=ProvenanceAction.GENERATED,
        metadata_hash="40" * 32,
        created_at=now,
    )
    with pytest.raises(sqlite3.IntegrityError):
        store.insert_event(ev)


def test_phase2_15_restart_persistence(tmp_path):
    # Simulate stopping backend and restarting backend by reopening database file in new store
    db_file = tmp_path / "persistence_test.db"
    store1 = SQLiteStore(db_file)

    now = datetime.now(timezone.utc)
    m = ModelRecord(
        model_id="MDL-PERSIST",
        name="PersistModel",
        version="1.0",
        model_type="image",
        creator_id="CRT-P",
        creator_name="Persist Creator",
        description="Persistent",
        model_hash="50" * 32,
        metadata_hash="60" * 32,
        status=ModelStatus.ACTIVE,
        created_at=now,
    )
    store1.insert_model(m)

    art = ArtifactRecord(
        artifact_id="ART-PERSIST",
        artifact_type=ArtifactType.IMAGE,
        exact_hash="70" * 32,
        robust_fingerprint="phash:abcd",
        size_bytes=1234,
        model_id="MDL-PERSIST",
        created_at=now,
    )
    store1.insert_artifact(art)

    # Simulate backend shutdown (discard store1) and start up new instance
    del store1

    store2 = SQLiteStore(db_file)
    retrieved_m = store2.get_model("MDL-PERSIST")
    retrieved_a = store2.get_artifact("ART-PERSIST")

    assert retrieved_m is not None
    assert retrieved_m.name == "PersistModel"
    assert retrieved_a is not None
    assert retrieved_a.exact_hash == "70" * 32
