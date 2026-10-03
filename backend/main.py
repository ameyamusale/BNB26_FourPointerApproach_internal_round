"""ModelLedger API composition / startup.

Run from the backend/ folder:  uvicorn main:app --reload
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import config
from api import adversarial, artifacts, demo, graph, models as models_api, provenance, verification
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

app.mount("/static", StaticFiles(directory=str(config.FRONTEND_DIR)), name="static")


# ---------------------------------------------------------------------------
# UI pages (Phase 5+). Plain static HTML pages served by the same FastAPI app.
# ---------------------------------------------------------------------------
PAGES = {
    "/dashboard": "dashboard.html",
    "/models": "models.html",
    "/artifacts": "artifacts.html",
    "/verify": "verify.html",
    "/audit": "audit.html",
    "/adversarial": "adversarial.html",
    "/demo": "demo.html",
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
    # Passport / lineage pages carry an :id path parameter.
    app.get(_path + "/{resource_id}", include_in_schema=False)(_page_factory(_filename))


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
    return {
        "service": config.APP_NAME,
        "tagline": config.APP_TAGLINE,
        "version": config.APP_VERSION,
        "implemented_phase": config.IMPLEMENTED_PHASE,
        "storage": {"mode": "sqlite", "persistent": True, "database": "modelledger.db"},
        "blockchain": blockchain.status(),
        "signatures": {"implemented": signature.IMPLEMENTED, "configured": bool(config.SIGNATURE_PRIVATE_KEY_PEM)},
        "robust_fingerprint": {"implemented": fingerprint.IMPLEMENTED},
        "counts": {
            "models": len(store.models),
            "artifacts": len(store.artifacts),
            "events": len(store.events),
        },
    }
