"""Proof of Creator API endpoints (Phase 8).

Handles:
- Creator enrollment with facial biometrics
- Live face & anti-spoof liveness verification
- Creator authorization token issuance
- Registered creator profiles & commitments
"""
from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from services import creator_auth
from services.errors import NotFoundError, ValidationError
from services.store import store

router = APIRouter(prefix="/api/creator", tags=["creator"])


class CreatorProfileResponse(BaseModel):
    identity_id: str
    name: str
    wallet_address: Optional[str] = None
    role: str
    has_biometric: bool
    status: str
    created_at: str


class AuthorizeResponse(BaseModel):
    authorization_token: str
    token_id: str
    creator_id: str
    creator_name: str
    biometric_commitment: str
    similarity: float
    liveness_score: float
    expires_at: str
    status: str


def _extract_image_bytes(file: Optional[UploadFile], image_base64: Optional[str]) -> bytes:
    if file and file.filename:
        return file.file.read()
    if image_base64:
        # Strip data URI prefix if present (e.g. data:image/png;base64,...)
        if "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]
        try:
            return base64.b64decode(image_base64)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {exc}")
    raise HTTPException(status_code=400, detail="Must provide either an image file upload or image_base64 data")


@router.post("/enroll", status_code=status.HTTP_201_CREATED)
def enroll_creator_endpoint(
    name: str = Form(..., min_length=1, max_length=80),
    identity_id: Optional[str] = Form(None),
    wallet_address: Optional[str] = Form(None),
    image_base64: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Enroll a creator identity with facial biometric credentials."""
    img_bytes = _extract_image_bytes(file, image_base64)
    cid = identity_id.strip() if identity_id else ""
    try:
        res = creator_auth.enroll_creator(cid, name.strip(), img_bytes, wallet_address)
        return res
    except ValidationError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Enrollment error: {exc}")


@router.post("/verify-face")
def verify_face_endpoint(
    creator_id: str = Form(...),
    image_base64: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Verify a live facial probe against the creator's enrolled template."""
    img_bytes = _extract_image_bytes(file, image_base64)
    try:
        res = creator_auth.verify_creator_face(creator_id.strip(), img_bytes)
        return res
    except NotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except ValidationError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Verification error: {exc}")


@router.post("/authorize", response_model=AuthorizeResponse)
def authorize_creator_endpoint(
    creator_id: str = Form(...),
    image_base64: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Verify facial biometrics and issue a signed Proof of Creator authorization token."""
    img_bytes = _extract_image_bytes(file, image_base64)
    try:
        res = creator_auth.authorize_creator(creator_id.strip(), img_bytes)
        return res
    except NotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except ValidationError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Authorization error: {exc}")


@router.get("/identities", response_model=List[CreatorProfileResponse])
def list_creator_identities():
    """List all registered identities and their biometric enrollment status."""
    rows = store.list_identities()
    return [
        CreatorProfileResponse(
            identity_id=r["identity_id"],
            name=r["name"],
            wallet_address=r.get("wallet_address"),
            role=r.get("role", "CREATOR"),
            has_biometric=bool(r.get("biometric_enrollment_reference")),
            status=r.get("status", "ACTIVE"),
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.get("/{identity_id}")
def get_creator_identity(identity_id: str):
    """Get creator profile and public biometric commitment."""
    ident = store.get_identity(identity_id)
    if not ident:
        raise HTTPException(status_code=404, detail=f"Creator {identity_id} not found")
    
    biometric_info = None
    if ident.get("biometric_enrollment_reference"):
        try:
            import json
            ref = json.loads(ident["biometric_enrollment_reference"])
            biometric_info = {
                "enrolled": True,
                "biometric_commitment": ref.get("commitment"),
                "enrolled_at": ref.get("enrolled_at"),
                "liveness_score": ref.get("liveness_score"),
            }
        except Exception:
            biometric_info = {"enrolled": True}

    return {
        "identity_id": ident["identity_id"],
        "name": ident["name"],
        "wallet_address": ident.get("wallet_address"),
        "role": ident.get("role", "CREATOR"),
        "status": ident.get("status", "ACTIVE"),
        "created_at": ident["created_at"],
        "biometrics": biometric_info,
    }


@router.post("/liveness-check")
def liveness_check_endpoint(
    image_base64: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Run standalone anti-spoofing liveness analysis on a camera capture or image."""
    img_bytes = _extract_image_bytes(file, image_base64)
    det = creator_auth.detect_face(img_bytes)
    if not det["detected"]:
        return {
            "face_detected": False,
            "liveness_passed": False,
            "verdict": "NO_FACE_DETECTED",
            "message": "No face found in the image frame",
        }
    liveness = creator_auth.analyze_liveness(img_bytes, det["face_crop"])
    return {
        "face_detected": True,
        "face_box": det["box"],
        "confidence": det["confidence"],
        "liveness": liveness,
    }
