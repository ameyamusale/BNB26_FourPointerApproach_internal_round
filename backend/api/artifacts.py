from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.deps import read_validated_image, to_http
from models.artifact import ArtifactRecord, ArtifactType
from models.provenance import CreateEventRequest, ProvenanceAction, ProvenanceEvent
from pydantic import BaseModel
from services import artifact_registry, provenance
from services.errors import ModelLedgerError

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


class RegisteredArtifact(BaseModel):
    artifact: ArtifactRecord
    event: Optional[ProvenanceEvent] = None


@router.post("", response_model=RegisteredArtifact, status_code=201)
async def register_artifact(
    file: UploadFile = File(...),
    model_id: Optional[str] = Form(None),
    parent_artifact_id: Optional[str] = Form(None),
    action: Optional[ProvenanceAction] = Form(None),
    application_id: Optional[str] = Form(None),
):
    """Register an artifact by fingerprinting the upload (the file itself is not kept).

    If a model_id (or application_id) is given, the matching provenance event is
    recorded too: GENERATED when there is no parent, otherwise `action` is required.
    """
    data = await read_validated_image(file)
    wants_event = bool(model_id or application_id or parent_artifact_id)
    if parent_artifact_id and not action:
        raise HTTPException(status_code=422, detail="`action` is required when parent_artifact_id is given")
    if wants_event and not parent_artifact_id and not model_id:
        raise HTTPException(status_code=422, detail="A GENERATED artifact needs a model_id")
    try:
        if parent_artifact_id:
            artifact_registry.get_artifact(parent_artifact_id)  # fail before registering anything
        artifact = artifact_registry.register_artifact(data, ArtifactType.IMAGE, model_id)
        event = None
        if wants_event:
            event = provenance.add_event(
                CreateEventRequest(
                    parent_artifact_id=parent_artifact_id,
                    child_artifact_id=artifact.artifact_id,
                    action=action or ProvenanceAction.GENERATED,
                    model_id=model_id,
                    application_id=application_id,
                )
            )
        return RegisteredArtifact(artifact=artifact, event=event)
    except ModelLedgerError as exc:
        raise to_http(exc)


@router.get("", response_model=List[ArtifactRecord])
def list_artifacts():
    return artifact_registry.list_artifacts()


@router.get("/{artifact_id}", response_model=ArtifactRecord)
def get_artifact(artifact_id: str):
    try:
        return artifact_registry.get_artifact(artifact_id)
    except ModelLedgerError as exc:
        raise to_http(exc)
