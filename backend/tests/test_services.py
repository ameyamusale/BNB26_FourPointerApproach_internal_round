import pytest

from models.claims import TrustStatus, VerificationEvidence
from models.model import RegisterModelRequest
from models.provenance import CreateEventRequest, ProvenanceAction
from services import artifact_registry, model_registry, provenance
from services.errors import DuplicateError, NotFoundError, ValidationFailure
from services.hashing import canonical_json_hash, is_sha256, sha256_bytes
from services.trust_engine import evaluate


def _model(name="VisionGen-X", version="1.0"):
    return model_registry.register_model(RegisterModelRequest(name=name, version=version, creator_name="Team Alpha"))


def test_sha256_known_vector():
    assert sha256_bytes(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert is_sha256(sha256_bytes(b"x")) and not is_sha256("nope")


def test_canonical_hash_ignores_key_order():
    assert canonical_json_hash({"a": 1, "b": 2}) == canonical_json_hash({"b": 2, "a": 1})


def test_model_registration_and_duplicate_prevention():
    m = _model()
    assert m.model_id.startswith("MDL-") and m.status.value == "ACTIVE"
    with pytest.raises(DuplicateError):
        _model()
    assert _model(version="2.0").model_id != m.model_id


def test_artifact_registration_and_duplicate_bytes(png):
    m = _model()
    a = artifact_registry.register_artifact(png(), model_id=m.model_id)
    assert a.exact_hash == sha256_bytes(png()) and a.robust_fingerprint and a.robust_fingerprint.startswith("phash:")
    with pytest.raises(DuplicateError):
        artifact_registry.register_artifact(png(), model_id=m.model_id)
    with pytest.raises(NotFoundError):
        artifact_registry.register_artifact(png((1, 2, 3)), model_id="MDL-NOPE")


def test_two_model_lineage(png):
    a_model, b_model = _model("A"), _model("B")
    a1 = artifact_registry.register_artifact(png((10, 0, 0)), model_id=a_model.model_id)
    provenance.add_event(CreateEventRequest(child_artifact_id=a1.artifact_id, action=ProvenanceAction.GENERATED, model_id=a_model.model_id))
    a2 = artifact_registry.register_artifact(png((20, 0, 0)), model_id=b_model.model_id)
    provenance.add_event(CreateEventRequest(parent_artifact_id=a1.artifact_id, child_artifact_id=a2.artifact_id, action=ProvenanceAction.UPSCALED, model_id=b_model.model_id))
    lineage = provenance.build_lineage(a2.artifact_id)
    assert [s.artifact_id for s in lineage.steps] == [a1.artifact_id, a2.artifact_id]
    assert lineage.depth == 1 and lineage.root_reached and not lineage.issues


def test_event_rules(png):
    m = _model()
    a = artifact_registry.register_artifact(png(), model_id=m.model_id)
    with pytest.raises(ValidationFailure):  # GENERATED must not have a parent
        provenance.add_event(CreateEventRequest(parent_artifact_id=a.artifact_id, child_artifact_id=a.artifact_id, action=ProvenanceAction.GENERATED, model_id=m.model_id))
    with pytest.raises(ValidationFailure):  # transform needs a parent
        provenance.add_event(CreateEventRequest(child_artifact_id=a.artifact_id, action=ProvenanceAction.RESIZED, model_id=m.model_id))
    provenance.add_event(CreateEventRequest(child_artifact_id=a.artifact_id, action=ProvenanceAction.GENERATED, model_id=m.model_id))
    with pytest.raises(DuplicateError):  # one creating event per artifact in Phase 1
        provenance.add_event(CreateEventRequest(child_artifact_id=a.artifact_id, action=ProvenanceAction.GENERATED, model_id=m.model_id))


def test_private_metadata_is_hashed_not_stored(png):
    m = _model()
    a = artifact_registry.register_artifact(png(), model_id=m.model_id)
    ev = provenance.add_event(CreateEventRequest(child_artifact_id=a.artifact_id, action=ProvenanceAction.GENERATED, model_id=m.model_id, metadata={"prompt": "secret cat"}))
    assert "secret" not in ev.model_dump_json()
    assert ev.metadata_hash == canonical_json_hash({"prompt": "secret cat"})


def test_trust_engine_matrix():
    full = VerificationEvidence(artifact_match=True, model_registered=True, signature_valid=True, parent_exists=True,
                                transformation_valid=True, blockchain_record=True, revoked=False)
    assert evaluate(full).status == TrustStatus.TRUSTED
    assert evaluate(VerificationEvidence(artifact_match=False)).status == TrustStatus.UNVERIFIABLE
    # unchecked evidence can never produce TRUSTED
    unchecked = full.model_copy(update={"blockchain_record": None})
    assert evaluate(unchecked).status == TrustStatus.SELF_ASSERTED
    assert evaluate(full.model_copy(update={"signature_valid": False})).status == TrustStatus.CONFLICT
    assert evaluate(full.model_copy(update={"parent_exists": False})).status == TrustStatus.CONFLICT
    revoked = evaluate(full.model_copy(update={"revoked": True}))
    assert revoked.status == TrustStatus.SELF_ASSERTED and "REVOKED" in revoked.flags
    assert evaluate(full, conflicts=["two origins"]).status == TrustStatus.CONFLICT


def test_sqlite_persistence_survives_new_store_instance(tmp_path):
    from services.store import SQLiteStore
    from models.model import RegisterModelRequest
    from services import model_registry
    from services.store import store

    model = _model("PersistentModel", "1.0")
    db_path = store.db_path
    assert db_path.endswith("modelledger.db")

    reopened = SQLiteStore(db_path)
    persisted = reopened.get_model(model.model_id)
    assert persisted is not None
    assert persisted.name == "PersistentModel"
    assert reopened.list_models()[0].model_id == model.model_id


def test_robust_fingerprint_is_stable_across_png_reencoding(png):
    from services.fingerprint import compute_robust_fingerprint, fingerprint_distance
    first = png((120, 80, 40), size=(16, 16))
    second = png((120, 80, 40), size=(32, 32))
    fp1 = compute_robust_fingerprint(first)
    fp2 = compute_robust_fingerprint(second)
    assert fp1 and fp2
    assert fingerprint_distance(fp1, fp2) <= 18


def test_signed_event_can_be_verified(png, monkeypatch):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from services import signature
    key = ec.generate_private_key(ec.SECP256K1())
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    monkeypatch.setattr("config.SIGNATURE_PRIVATE_KEY_PEM", pem)
    m = _model()
    a = artifact_registry.register_artifact(png(), model_id=m.model_id)
    event = provenance.add_event(CreateEventRequest(child_artifact_id=a.artifact_id, action=ProvenanceAction.GENERATED, model_id=m.model_id))
    assert event.signature and event.signature_public_key
    assert signature.verify_event_signature(event, event.signature_public_key) is True
    assert signature.claim_hash(event)


def test_tampered_signed_event_fails_verification(png, monkeypatch):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from services import signature
    key = ec.generate_private_key(ec.SECP256K1())
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    monkeypatch.setattr("config.SIGNATURE_PRIVATE_KEY_PEM", pem)
    m = _model()
    a = artifact_registry.register_artifact(png(), model_id=m.model_id)
    event = provenance.add_event(CreateEventRequest(child_artifact_id=a.artifact_id, action=ProvenanceAction.GENERATED, model_id=m.model_id))
    tampered = event.model_copy(update={"metadata_hash": "0" * 64})
    assert signature.verify_event_signature(tampered, tampered.signature_public_key) is False
