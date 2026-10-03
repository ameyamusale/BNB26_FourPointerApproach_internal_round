"""Phase 6 — controlled multi-model transformation pipeline.

Runs the exact scenario from the problem statement end-to-end:

    Model A --generate--> Artifact A --Model B upscale--> Artifact B
                                     --Editor resize/re-encode--> Artifact C

Every step creates a new artifact ID, a signed provenance event and (when the
chain is configured) a blockchain commitment. The pipeline is deterministic so
it can be re-run live during the demo.
"""
from __future__ import annotations

import io
import uuid
from typing import Any, Dict, List, Optional

from PIL import Image, ImageFilter

from models.artifact import ArtifactType
from models.model import RegisterModelRequest
from models.provenance import CreateEventRequest, ProvenanceAction
from services import artifact_registry, model_registry, provenance
from services.errors import DuplicateError, ModelLedgerError, ValidationFailure
from services.graph import build_graph
from services.hashing import sha256_bytes
from services.store import store

# Upload size guard for the demo editor input.
MAX_DEMO_INPUT_BYTES = 5 * 1024 * 1024


class DemoPipelineError(ModelLedgerError):
    pass


def _png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _register_with_event(data: bytes, *, action: ProvenanceAction, model_id: Optional[str],
                         application_id: Optional[str], parent_artifact_id: Optional[str],
                         metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Register an artifact and immediately record its creating provenance event."""
    artifact = artifact_registry.register_artifact(data, ArtifactType.IMAGE, model_id)
    event = provenance.add_event(
        CreateEventRequest(
            parent_artifact_id=parent_artifact_id,
            child_artifact_id=artifact.artifact_id,
            action=action,
            model_id=model_id,
            application_id=application_id,
            metadata=metadata or {},
        )
    )
    return {"artifact": artifact, "event": event}


def run_pipeline(image_bytes: bytes, seed: Optional[str] = None) -> Dict[str, Any]:
    """Execute the full demo pipeline on an uploaded image and return every step."""
    if not image_bytes:
        raise DemoPipelineError("A seed image is required")
    if len(image_bytes) > MAX_DEMO_INPUT_BYTES:
        raise DemoPipelineError("Seed image exceeds the 5 MB demo limit")
    try:
        base = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise DemoPipelineError(f"Could not decode the seed image: {type(exc).__name__}")

    seed = (seed or uuid.uuid4().hex[:6]).upper()
    steps: List[Dict[str, Any]] = []

    # --- Register the two demo models (reused across runs) ---
    models: Dict[str, Any] = {}
    for key, name, version, mtype in (
        ("generator", f"DemoGen-{seed}", "1.0.0", "text-to-image"),
        ("upscaler", f"DemoUpscale-{seed}", "2.0.0", "super-resolution"),
    ):
        try:
            models[key] = model_registry.register_model(
                RegisterModelRequest(name=name, version=version, model_type=mtype, creator_name="ModelLedger Demo")
            )
        except DuplicateError:
            existing = next(m for m in store.list_models() if m.name == name)
            models[key] = existing
        steps.append({"step": f"register_{key}", "model_id": models[key].model_id, "name": models[key].name,
                      "version": models[key].version, "blockchain_tx": models[key].blockchain_tx})

    # --- Step 1: Model A generates Artifact A ---
    # A per-run marker is embedded in the image so repeated pipeline runs with
    # the same seed image always produce new bytes (the registry forbids
    # duplicate exact hashes).
    base = base.copy()
    base.putpixel((0, 0), tuple(c % 256 for c in (int(uuid.uuid4().hex[:6], 16),) * 3))
    generated = _register_with_event(
        _png_bytes(base), action=ProvenanceAction.GENERATED, model_id=models["generator"].model_id,
        application_id=None, parent_artifact_id=None,
        metadata={"demo_seed": seed, "stage": "generation"},
    )
    art_a, ev_a = generated["artifact"], generated["event"]
    steps.append({"step": "generate", "artifact_id": art_a.artifact_id, "event_id": ev_a.event_id,
                  "action": ev_a.action.value, "sha256": art_a.exact_hash,
                  "robust_fingerprint": art_a.robust_fingerprint, "signed": bool(ev_a.signature),
                  "blockchain_tx": ev_a.blockchain_tx})

    # --- Step 2: Model B upscales Artifact A -> Artifact B ---
    upscaled_image = base.resize((base.width * 2, base.height * 2), Image.Resampling.LANCZOS)
    upscaled = _register_with_event(
        _png_bytes(upscaled_image), action=ProvenanceAction.UPSCALED, model_id=models["upscaler"].model_id,
        application_id="DemoStudio-Pipeline", parent_artifact_id=art_a.artifact_id,
        metadata={"scale_factor": 2.0, "stage": "upscale"},
    )
    art_b, ev_b = upscaled["artifact"], upscaled["event"]
    steps.append({"step": "upscale", "artifact_id": art_b.artifact_id, "event_id": ev_b.event_id,
                  "action": ev_b.action.value, "parent_artifact_id": art_a.artifact_id,
                  "sha256": art_b.exact_hash, "robust_fingerprint": art_b.robust_fingerprint,
                  "signed": bool(ev_b.signature), "blockchain_tx": ev_b.blockchain_tx})

    # --- Step 3: Editor application resizes + re-encodes Artifact B -> Artifact C ---
    # Slight unsharp-style adjustment guarantees the editor output differs byte-wise
    # from its input even for flat test images.
    edited_image = upscaled_image.filter(ImageFilter.GaussianBlur(radius=0.6))
    enhanced = Image.blend(upscaled_image, edited_image, 0.85)
    enhanced = enhanced.point(lambda p: min(255, p + 1))
    edited = _register_with_event(
        _png_bytes(enhanced), action=ProvenanceAction.RE_ENCODED, model_id=None,
        application_id="DemoEditor-App", parent_artifact_id=art_b.artifact_id,
        metadata={"operation": "resize+re-encode", "stage": "editor"},
    )
    art_c, ev_c = edited["artifact"], edited["event"]
    steps.append({"step": "editor", "artifact_id": art_c.artifact_id, "event_id": ev_c.event_id,
                  "action": ev_c.action.value, "parent_artifact_id": art_b.artifact_id,
                  "sha256": art_c.exact_hash, "robust_fingerprint": art_c.robust_fingerprint,
                  "signed": bool(ev_c.signature), "blockchain_tx": ev_c.blockchain_tx})

    graph = build_graph(art_c.artifact_id)
    lineage = provenance.build_lineage(art_c.artifact_id)

    return {
        "seed": seed,
        "models": {k: m.model_id for k, m in models.items()},
        "artifacts": {"generated": art_a.artifact_id, "upscaled": art_b.artifact_id, "final": art_c.artifact_id},
        "events": [ev_a.event_id, ev_b.event_id, ev_c.event_id],
        "steps": steps,
        "lineage": lineage,
        "graph": graph,
        "summary": {
            "multi_model": True,
            "depth": lineage.depth,
            "root_reached": lineage.root_reached,
            "final_artifact": art_c.artifact_id,
        },
    }


def register_transformed(parent_artifact_id: str, image_bytes: bytes, action: str,
                         model_id: Optional[str], application_id: Optional[str]) -> Dict[str, Any]:
    """Register one transformed artifact linked to a parent (the manual pipeline)."""
    if not image_bytes:
        raise DemoPipelineError("Transformed image bytes are required")
    try:
        action_enum = ProvenanceAction(action)
    except ValueError:
        raise ValidationFailure(f"Unknown transformation action: {action}")
    if action_enum == ProvenanceAction.GENERATED:
        raise ValidationFailure("Use plain artifact registration for GENERATED artifacts")
    if not model_id and not application_id:
        raise ValidationFailure("A transformation needs a model_id or application_id")
    result = _register_with_event(
        image_bytes, action=action_enum, model_id=model_id, application_id=application_id,
        parent_artifact_id=parent_artifact_id, metadata={"registered_via": "transform-api"},
    )
    return {"artifact": result["artifact"], "event": result["event"],
            "graph": build_graph(result["artifact"].artifact_id)}
