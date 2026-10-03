"""Artifact and zero-knowledge prompt commitment verification (Phases 4, 8, 9)."""
from __future__ import annotations

import hashlib
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from api.deps import read_validated_image
from models.claims import VerificationReport
from services import verification
from services.store import store

router = APIRouter(prefix="/api/verify", tags=["verification"])


class PromptVerificationRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_id: Optional[str] = None
    prompt_commitment: Optional[str] = None
    candidate_prompt: Optional[str] = None
    prompt_text: Optional[str] = None


class PromptVerificationResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_id: Optional[str] = None
    matches_commitment: bool
    valid: bool
    prompt_hash: str
    computed_hash: str
    expected_commitment: Optional[str] = None
    note: str


@router.post("", response_model=VerificationReport)
async def verify_artifact(file: UploadFile = File(...)):
    """Upload an artifact and receive structured evidence plus a trust state."""
    data = await read_validated_image(file)
    return verification.verify_bytes(data)


@router.post("/prompt-commitment", response_model=PromptVerificationResponse)
def verify_prompt_commitment(req: PromptVerificationRequest):
    """Phase 9 Privacy Guard: Verify if a prompt produced a model WITHOUT revealing private text publicly."""
    text_to_check = req.candidate_prompt or req.prompt_text or ""
    if not text_to_check.strip():
        raise HTTPException(status_code=400, detail="Must provide candidate_prompt or prompt_text to verify.")

    prompt_hash = hashlib.sha256(text_to_check.strip().encode()).hexdigest()
    expected = req.prompt_commitment

    if req.model_id:
        model = store.get_model(req.model_id)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model {req.model_id} not found")
        expected = model.private_prompt_commitment or expected

    if not expected:
        return PromptVerificationResponse(
            model_id=req.model_id,
            matches_commitment=False,
            valid=False,
            prompt_hash=prompt_hash,
            computed_hash=prompt_hash,
            expected_commitment=None,
            note="No expected prompt commitment hash provided or recorded for this model.",
        )

    matches = (prompt_hash.lower() == expected.lower().strip())
    return PromptVerificationResponse(
        model_id=req.model_id,
        matches_commitment=matches,
        valid=matches,
        prompt_hash=prompt_hash,
        computed_hash=prompt_hash,
        expected_commitment=expected,
        note="Prompt matches the registered cryptographic commitment exactly." if matches else "Prompt does not match recorded commitment.",
    )
