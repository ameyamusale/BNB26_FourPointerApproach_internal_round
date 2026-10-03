"""Shared API helpers: upload validation and domain-error -> HTTP mapping (Phase 9 Hardening)."""
from __future__ import annotations

import io
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image

import config
from services.errors import DuplicateError, ModelLedgerError, NotFoundError, ValidationError, ValidationFailure


async def read_validated_image(file: UploadFile) -> bytes:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in config.ALLOWED_ARTIFACT_EXTENSIONS:
        allowed = ", ".join(sorted(config.ALLOWED_ARTIFACT_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {allowed}")
    data = await file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit")
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Pillow integrity verification (prevents decompression bombs and corrupt files)
    try:
        im = Image.open(io.BytesIO(data))
        im.verify()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid or corrupted image payload: {exc}")

    return data


def to_http(exc: ModelLedgerError) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, DuplicateError):
        return HTTPException(status_code=409, detail={"message": str(exc), "existing_id": exc.existing_id})
    if isinstance(exc, ValidationFailure):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, ValidationError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))
