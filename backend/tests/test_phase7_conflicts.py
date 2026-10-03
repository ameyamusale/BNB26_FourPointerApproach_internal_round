"""Phase 7 — conflict detector + adversarial lab API tests.

The API-level attacks run the real verification engine. Blockchain stays
unconfigured in this suite, so evidence shows as explicitly not-checked and the
expected statuses are the offline ones (never a false TRUSTED).
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from models.artifact import ArtifactRecord, ArtifactType
from models.claims import TrustStatus
from models.model import RegisterModelRequest
from models.provenance import ProvenanceAction, ProvenanceEvent
from services import artifact_registry, conflict_detector, model_registry
from services.store import store


def _bare_artifact(artifact_id: str, exact_hash: str, model_id: str) -> ArtifactRecord:
    rec = ArtifactRecord(
        artifact_id=artifact_id, artifact_type=ArtifactType.IMAGE, exact_hash=exact_hash,
        robust_fingerprint=None, size_bytes=10, model_id=model_id,
        created_at=datetime.now(timezone.utc),
    )
    store.insert_artifact(rec)
    return rec


def test_conflict_detector_competing_issuers():
    model = model_registry.register_model(RegisterModelRequest(name="ConflictDetectorModel", version="1.0", creator_name="C"))
    rec = _bare_artifact("ART-CDET-1", "f" * 64, model.model_id)
    store.upsert_identity("CRT-CD-1", "Issuer One")
    store.upsert_identity("CRT-CD-2", "Issuer Two")
    store.create_claim("CLM-CD-1", rec.artifact_id, "ORIGIN_CLAIM", "CRT-CD-1", "CRYPTO", "s1", "ACTIVE")
    store.create_claim("CLM-CD-2", rec.artifact_id, "ORIGIN_CLAIM", "CRT-CD-2", "CRYPTO", "s2", "ACTIVE")
    conflicts = conflict_detector.detect_conflicts(rec.artifact_id)
    assert any("competing issuers" in c for c in conflicts)


def test_conflict_detector_competing_origin_models():
    m1 = model_registry.register_model(RegisterModelRequest(name="CDModelA", version="1.0", creator_name="C"))
    m2 = model_registry.register_model(RegisterModelRequest(name="CDModelB", version="1.0", creator_name="C"))
    rec = _bare_artifact("ART-CDET-2", "e" * 64, m1.model_id)
    ev = ProvenanceEvent(
        event_id="EVT-CDET-2", parent_artifact_id=None, child_artifact_id=rec.artifact_id,
        action=ProvenanceAction.GENERATED, model_id=m2.model_id,
        metadata_hash="d" * 64, created_at=datetime.now(timezone.utc),
    )
    store.insert_event(ev)
    conflicts = conflict_detector.detect_conflicts(rec.artifact_id)
    assert any("Incompatible origin claims" in c for c in conflicts)


def test_conflict_detector_quiet_when_consistent(png):
    model = model_registry.register_model(RegisterModelRequest(name="CDQuietModel", version="1.0", creator_name="C"))
    art = artifact_registry.register_artifact(png((7, 7, 7)), model_id=model.model_id)
    assert conflict_detector.detect_conflicts(art.artifact_id) == []


# --------------------------- API-level adversarial lab ---------------------------

@pytest.fixture
def client():
    from main import app
    return TestClient(app)


EXPECTED_STATUS = {
    "tamper-artifact": TrustStatus.UNVERIFIABLE,
    "forge-claim": TrustStatus.CONFLICT,
    "remove-step": TrustStatus.CONFLICT,
    "conflicting-claims": TrustStatus.CONFLICT,
    "revoke-model": TrustStatus.SELF_ASSERTED,
}


@pytest.mark.parametrize("scenario_id", sorted(EXPECTED_STATUS))
def test_adversarial_attack_via_api(client, scenario_id):
    r = client.post(f"/api/adversarial/run/{scenario_id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scenario"] == scenario_id
    assert body["verification"]["decision"]["status"] == EXPECTED_STATUS[scenario_id].value
    # The evidence behind the decision is always included.
    assert body["verification"]["checks"]
    assert body["verification"]["evidence"]
    # A trust state is never claimed without reasons.
    assert body["verification"]["decision"]["reasons"]


def test_adversarial_unknown_scenario(client):
    assert client.post("/api/adversarial/run/does-not-exist").status_code == 404


def test_adversarial_scenarios_catalogue(client):
    scenarios = client.get("/api/adversarial/scenarios").json()
    assert all(sid in [s["id"] for s in scenarios] for sid in EXPECTED_STATUS)
    assert all(s["implemented"] for s in scenarios)
