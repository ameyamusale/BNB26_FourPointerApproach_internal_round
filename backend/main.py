"""ModelLedger API composition / startup (Phases 0 through 10).

Run from the backend/ folder:  uvicorn main:app --reload
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import config
from api import (
    adversarial,
    artifacts,
    audit,
    creator,
    demo,
    graph,
    models as models_api,
    provenance,
    verification,
)
from services import blockchain, fingerprint, signature
from services.store import store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(title=config.APP_NAME, description=config.APP_TAGLINE, version=config.APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(models_api.router)
app.include_router(artifacts.router)
app.include_router(provenance.router)
app.include_router(verification.router)
app.include_router(adversarial.router)
app.include_router(graph.router)
app.include_router(demo.router)
app.include_router(creator.router)
app.include_router(audit.router)

app.mount("/static", StaticFiles(directory=str(config.FRONTEND_DIR)), name="static")


# ---------------------------------------------------------------------------
# UI pages (Phases 5 through 10). Plain HTML pages served by FastAPI.
# ---------------------------------------------------------------------------
PAGES = {
    "/dashboard": "dashboard.html",
    "/models": "models.html",
    "/artifacts": "artifacts.html",
    "/verify": "verify.html",
    "/audit": "audit.html",
    "/adversarial-lab": "adversarial.html",
    "/adversarial": "adversarial.html",
    "/proof-of-creator": "creator.html",
    "/creator": "creator.html",
}


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(config.FRONTEND_DIR / "dashboard.html")


def _page_factory(filename: str):
    def page() -> FileResponse:
        return FileResponse(config.FRONTEND_DIR / filename)
    return page


for _path, _filename in PAGES.items():
    app.get(_path, include_in_schema=False)(_page_factory(_filename))


@app.get("/models/{model_id}", include_in_schema=False)
def model_page(model_id: str) -> FileResponse:
    return FileResponse(config.FRONTEND_DIR / "model.html")


@app.get("/artifacts/{artifact_id}", include_in_schema=False)
def artifact_page(artifact_id: str) -> FileResponse:
    return FileResponse(config.FRONTEND_DIR / "artifact.html")


@app.get("/lineage/{artifact_id}", include_in_schema=False)
def lineage_page(artifact_id: str) -> FileResponse:
    return FileResponse(config.FRONTEND_DIR / "lineage.html")


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": config.APP_NAME, "version": config.APP_VERSION}


@app.get("/api/status", tags=["system"])
def system_status():
    """What is real vs. stubbed right now. The UI shows this so nothing is overstated."""
    enrolled_count = len([i for i in store.list_identities() if i.get("biometric_enrollment_reference")])
    return {
        "service": config.APP_NAME,
        "tagline": config.APP_TAGLINE,
        "version": config.APP_VERSION,
        "implemented_phase": config.IMPLEMENTED_PHASE,
        "storage": {"mode": "sqlite", "persistent": True, "database": "modelledger.db"},
        "blockchain": blockchain.status(),
        "signatures": {"implemented": signature.IMPLEMENTED, "configured": bool(config.SIGNATURE_PRIVATE_KEY_PEM)},
        "robust_fingerprint": {"implemented": fingerprint.IMPLEMENTED},
        "proof_of_creator": {
            "implemented": True,
            "facial_authentication": True,
            "liveness_anti_spoof": True,
            "enrolled_creators": enrolled_count,
        },
        "audit_logs": {
            "count": len(store.list_audit_logs(limit=500)),
            "tamper_evident": True,
        },
        "counts": {
            "models": len(store.models),
            "artifacts": len(store.artifacts),
            "events": len(store.events),
            "enrolled_creators": enrolled_count,
        },
    }



