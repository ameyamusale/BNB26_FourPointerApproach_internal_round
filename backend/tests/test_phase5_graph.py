"""Phase 5 — provenance graph and passport tests."""
import pytest

from models.model import RegisterModelRequest
from models.provenance import CreateEventRequest, ProvenanceAction
from services import artifact_registry, graph, model_registry, passport, provenance
from services.errors import NotFoundError


def _setup_chain(png, name="GraphModel"):
    model = model_registry.register_model(RegisterModelRequest(name=name, version="1.0", creator_name="Team Alpha"))
    art1 = artifact_registry.register_artifact(png((10, 10, 10)), model_id=model.model_id)
    provenance.add_event(CreateEventRequest(child_artifact_id=art1.artifact_id, action=ProvenanceAction.GENERATED, model_id=model.model_id))
    art2 = artifact_registry.register_artifact(png((20, 20, 20)), model_id=model.model_id)
    provenance.add_event(CreateEventRequest(parent_artifact_id=art1.artifact_id, child_artifact_id=art2.artifact_id,
                                            action=ProvenanceAction.UPSCALED, model_id=model.model_id))
    return model, art1, art2


def test_build_graph(png):
    model, art1, art2 = _setup_chain(png)
    g = graph.build_graph(art2.artifact_id)

    kinds = {n["id"] for n in g["nodes"]}
    assert "artifact:" + art1.artifact_id in kinds
    assert "artifact:" + art2.artifact_id in kinds
    assert "model:" + model.model_id in kinds
    assert len(g["edges"]) == 2
    labels = [e["label"] for e in g["edges"]]
    assert "GENERATED" in labels and "UPSCALED" in labels
    assert all(e["source"] and e["target"] for e in g["edges"])
    assert g["root_reached"] is True


def test_build_full_graph(png):
    model, art1, art2 = _setup_chain(png, name="FullGraphModel")
    g = graph.build_full_graph()
    node_ids = {n["id"] for n in g["nodes"]}
    assert "model:" + model.model_id in node_ids
    assert "artifact:" + art2.artifact_id in node_ids
    assert len(g["edges"]) >= 2


def test_model_passport(png):
    model, art1, art2 = _setup_chain(png, name="PassportModel")
    p = passport.model_passport(model.model_id)
    assert p["model"].model_id == model.model_id
    assert p["artifacts_count"] == 2
    assert p["events_count"] == 2
    assert p["status"] == "ACTIVE"
    with pytest.raises(NotFoundError):
        passport.model_passport("MDL-NOPE")


def test_artifact_passport(png):
    model, art1, art2 = _setup_chain(png, name="ArtPassportModel")
    p = passport.artifact_passport(art2.artifact_id)
    assert p["artifact"].artifact_id == art2.artifact_id
    assert p["transformation_count"] == 1
    assert p["provenance_depth"] == 1
    assert len(p["events"]) >= 1  # at least the artifact's own creating event
    assert p["graph"]["nodes"]
    with pytest.raises(NotFoundError):
        passport.artifact_passport("ART-NOPE")
