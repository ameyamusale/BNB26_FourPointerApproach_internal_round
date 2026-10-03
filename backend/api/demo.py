"""Phase 6 API: the controlled multi-model transformation pipeline."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.deps import read_validated_image, to_http
from services import demo_pipeline
from services.errors import ModelLedgerError

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/pipeline")
async def run_pipeline(
    file: UploadFile = File(...),
    seed: Optional[str] = Form(None),
):
    """Run the Model A -> Artifact A -> Model B -> Artifact B -> Editor -> Artifact C demo."""
    data = await read_validated_image(file)
    try:
        return demo_pipeline.run_pipeline(data, seed=seed)
    except ModelLedgerError as exc:
        raise to_http(exc)


@router.post("/transform")
async def register_transform(
    file: UploadFile = File(...),
    parent_artifact_id: str = Form(...),
    action: str = Form(...),
    model_id: Optional[str] = Form(None),
    application_id: Optional[str] = Form(None),
):
    """Register one transformed artifact linked to a parent artifact."""
    data = await read_validated_image(file)
    if not model_id and not application_id:
        raise HTTPException(status_code=422, detail="A transformation needs model_id or application_id")
    try:
        return demo_pipeline.register_transformed(parent_artifact_id, data, action, model_id, application_id)
    except ModelLedgerError as exc:
        raise to_http(exc)
