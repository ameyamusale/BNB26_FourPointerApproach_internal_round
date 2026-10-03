from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from api.deps import read_validated_image
from models.claims import VerificationReport
from services import verification

router = APIRouter(prefix="/api/verify", tags=["verification"])


@router.post("", response_model=VerificationReport)
async def verify_artifact(file: UploadFile = File(...)):
    """Upload an artifact and receive structured evidence plus a trust state."""
    data = await read_validated_image(file)
    return verification.verify_bytes(data)
