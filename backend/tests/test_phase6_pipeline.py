"""Phase 6 — multi-model transformation pipeline tests."""
import io

from PIL import Image

from models.artifact import ArtifactType
from models.provenance import ProvenanceAction
from services import artifact_registry, demo_pipeline, provenance
from services.errors import ValidationFailure


def _png(color=(100, 100, 100), size=(32, 32)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_pipeline_creates_multi_model_lineage():
    result = demo_pipeline.run_pipeline(_png(), seed="P6TEST")

    assert result["summary"]["multi_model"] is True
    assert result["summary"]["root_reached"] is True
    assert result["summary"]["depth"] == 2

    # Three artifacts, generated -> upscaled -> re-encoded.
    assert set(result["artifacts"]) == {"generated", "upscaled", "final"}
    assert result["artifacts"]["generated"] != result["artifacts"]["upscaled"] != result["artifacts"]["final"]

    # Two distinct models plus an editor application participated.
    assert result["models"]["generator"] != result["models"]["upscaler"]

    actions = [s.get("action") for s in result["steps"] if s.get("action")]
    assert actions == ["GENERATED", "UPSCALED", "RE_ENCODED"]

    # The full lineage of the final artifact is reconstructable.
    lineage = provenance.build_lineage(result["artifacts"]["final"])
    assert [s.artifact_id for s in lineage.steps] == [
        result["artifacts"]["generated"], result["artifacts"]["upscaled"], result["artifacts"]["final"],
    ]
    assert lineage.root_reached is True and not lineage.issues

    actions_on_chain = [s.event.action for s in lineage.steps if s.event]
    assert actions_on_chain == [ProvenanceAction.GENERATED, ProvenanceAction.UPSCALED, ProvenanceAction.RE_ENCODED]


def test_pipeline_is_rerunnable():
    r1 = demo_pipeline.run_pipeline(_png((10, 10, 10)), seed="P6RERUN")
    r2 = demo_pipeline.run_pipeline(_png((10, 10, 10)), seed="P6RERUN")
    # Models are reused, artifacts are new each run.
    assert r1["models"]["generator"] == r2["models"]["generator"]
    assert r1["artifacts"]["final"] != r2["artifacts"]["final"]


def test_pipeline_rejects_bad_input():
    import pytest
    from services.errors import ModelLedgerError
    with pytest.raises(ModelLedgerError):
        demo_pipeline.run_pipeline(b"")
    with pytest.raises(ModelLedgerError):
        demo_pipeline.run_pipeline(b"not an image")


def test_register_transformed(png):
    model = None
    from models.model import RegisterModelRequest
    from services import model_registry
    model = model_registry.register_model(RegisterModelRequest(name="TransformModel", version="1.0", creator_name="T"))
    parent = artifact_registry.register_artifact(png((3, 3, 3)), ArtifactType.IMAGE, model.model_id)

    result = demo_pipeline.register_transformed(parent.artifact_id, png((4, 4, 4)), "UPSCALED", model.model_id, None)
    assert result["event"].parent_artifact_id == parent.artifact_id
    assert result["event"].action == ProvenanceAction.UPSCALED
    assert result["graph"]["edges"]

    import pytest
    with pytest.raises(ValidationFailure):
        demo_pipeline.register_transformed(parent.artifact_id, png((5, 5, 5)), "GENERATED", model.model_id, None)
    with pytest.raises(ValidationFailure):
        demo_pipeline.register_transformed(parent.artifact_id, png((6, 6, 6)), "NOT-ACTION", model.model_id, None)
