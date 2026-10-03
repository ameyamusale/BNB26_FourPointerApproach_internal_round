"""Phase 7 API: the adversarial lab."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from services import adversarial
from services.errors import ModelLedgerError

router = APIRouter(prefix="/api/adversarial", tags=["adversarial"])


@router.get("/scenarios")
def list_scenarios():
    return adversarial.list_scenarios()


@router.post("/run/{scenario_id}")
def run_scenario(scenario_id: str):
    try:
        return adversarial.run(scenario_id)
    except ModelLedgerError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
