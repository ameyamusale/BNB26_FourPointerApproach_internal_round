"""Shared API helpers: upload validation and domain-error -> HTTP mapping."""
from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, UploadFile

import config
from services.errors import DuplicateError, ModelLedgerError, NotFoundError, ValidationFailure


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
    return data


def to_http(exc: ModelLedgerError) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, DuplicateError):
        return HTTPException(status_code=409, detail={"message": str(exc), "existing_id": exc.existing_id})
    if isinstance(exc, ValidationFailure):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))
