def _reg_model(client, name="VisionGen-X", version="2.1.0"):
    r = client.post("/api/models", json={"name": name, "version": version, "creator_name": "Team Alpha"})
    assert r.status_code == 201, r.text
    return r.json()


def _reg_artifact(client, data, **form):
    return client.post("/api/artifacts", files={"file": ("img.png", data, "image/png")}, data=form)


def test_health_and_status(client):
    assert client.get("/health").json()["status"] == "ok"
    s = client.get("/api/status").json()
    assert s["service"] == "ModelLedger" and s["implemented_phase"] == 4
    assert s["blockchain"]["connected"] is False and s["blockchain"]["mode"] in {"offline", "dependency-missing", "rpc-unreachable", "error"}
    assert s["storage"]["mode"] == "sqlite" and s["storage"]["persistent"] is True


def test_frontend_served(client):
    assert "ModelLedger" in client.get("/").text


def test_register_and_fetch_model(client):
    m = _reg_model(client)
    assert client.get(f"/api/models/{m['model_id']}").json()["name"] == "VisionGen-X"
    assert len(client.get("/api/models").json()) == 1
    assert client.post("/api/models", json={"name": "VisionGen-X", "version": "2.1.0", "creator_name": "Team Alpha"}).status_code == 409
    assert client.get("/api/models/MDL-MISSING").status_code == 404
    assert client.post("/api/models", json={"name": "", "version": "1", "creator_name": "x"}).status_code == 422


def test_upload_validation(client):
    r = client.post("/api/artifacts", files={"file": ("doc.pdf", b"%PDF", "application/pdf")})
    assert r.status_code == 400
    r = client.post("/api/artifacts", files={"file": ("a.png", b"", "image/png")})
    assert r.status_code == 400


def test_full_two_model_flow_and_verification(client, png):
    a, b = _reg_model(client, "ModelA", "1.0"), _reg_model(client, "ModelB", "2.0")
    r1 = _reg_artifact(client, png((10, 10, 10)), model_id=a["model_id"])
    assert r1.status_code == 201 and r1.json()["event"]["action"] == "GENERATED"
    art1 = r1.json()["artifact"]["artifact_id"]
    r2 = _reg_artifact(client, png((20, 20, 20)), model_id=b["model_id"], parent_artifact_id=art1, action="UPSCALED")
    assert r2.status_code == 201, r2.text
    art2 = r2.json()["artifact"]["artifact_id"]

    lineage = client.get(f"/api/provenance/artifacts/{art2}/lineage").json()
    assert [s["artifact_id"] for s in lineage["steps"]] == [art1, art2] and lineage["root_reached"]

    # Verify the final artifact: honest result, NOT trusted, blockchain not claimed.
    v = client.post("/api/verify", files={"file": ("x.png", png((20, 20, 20)), "image/png")}).json()
    assert v["artifact"]["artifact_id"] == art2
    assert v["evidence"]["artifact_match"] is True and v["evidence"]["model_registered"] is True
    assert v["evidence"]["blockchain_record"] is None and v["evidence"]["signature_valid"] is None
    assert v["decision"]["status"] == "SELF_ASSERTED"
    states = {c["key"]: c["state"] for c in v["checks"]}
    assert states["blockchain_record"] == "not_checked" and states["signature_valid"] == "not_checked"
    assert states["artifact_match"] == "pass" and states["transformation_valid"] == "pass"


def test_tampered_or_unknown_artifact_is_unverifiable(client, png):
    m = _reg_model(client)
    _reg_artifact(client, png((5, 5, 5)), model_id=m["model_id"])
    v = client.post("/api/verify", files={"file": ("x.png", png((6, 5, 5)), "image/png")}).json()
    assert v["decision"]["status"] == "UNVERIFIABLE" and v["artifact"] is None


def test_bad_references_are_rejected_without_side_effects(client, png):
    r = _reg_artifact(client, png(), model_id="MDL-NOPE")
    assert r.status_code == 404
    m = _reg_model(client)
    r = _reg_artifact(client, png((1, 1, 1)), model_id=m["model_id"], parent_artifact_id="ART-NOPE", action="EDITED")
    assert r.status_code == 404
    assert client.get("/api/artifacts").json() == []
    r = _reg_artifact(client, png((2, 2, 2)), parent_artifact_id="ART-X")  # missing action
    assert r.status_code == 422


def test_adversarial_catalogue_only(client):
    scenarios = client.get("/api/adversarial/scenarios").json()
    assert len(scenarios) == 5 and not any(s["implemented"] for s in scenarios)
    assert client.post("/api/adversarial/run/tamper-artifact").status_code == 501
    assert client.post("/api/adversarial/run/nope").status_code == 404


def test_phase4_status_reports_real_implemented_features(client):
    s = client.get("/api/status").json()
    assert s["implemented_phase"] == 4
    assert s["signatures"]["implemented"] is True
    assert s["robust_fingerprint"]["implemented"] is True
