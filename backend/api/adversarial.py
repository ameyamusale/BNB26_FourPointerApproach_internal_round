"""Adversarial Lab API. Phase 1 publishes the scenario catalogue only (attacks run in Phase 7)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/adversarial", tags=["adversarial"])


class Scenario(BaseModel):
    id: str
    title: str
    expected: str
    implemented: bool = False


SCENARIOS: List[Scenario] = [
    Scenario(id="tamper-artifact", title="Tamper with a registered artifact", expected="EXACT HASH MISMATCH / PROVENANCE INCONSISTENCY"),
    Scenario(id="forge-claim", title="Forge a provenance claim for another model", expected="SIGNATURE INVALID / CLAIM NOT SUPPORTED"),
    Scenario(id="remove-step", title="Remove a provenance step", expected="BROKEN LINEAGE"),
    Scenario(id="conflicting-claims", title="Create two conflicting origin claims", expected="PROVENANCE CONFLICT DETECTED"),
    Scenario(id="revoke-model", title="Revoke a model after registration", expected="PROVENANCE AVAILABLE BUT MODEL REVOKED"),
]


@router.get("/scenarios", response_model=List[Scenario])
def list_scenarios():
    return SCENARIOS


@router.post("/run/{scenario_id}", status_code=501)
def run_scenario(scenario_id: str):
    if scenario_id not in {s.id for s in SCENARIOS}:
        raise HTTPException(status_code=404, detail="Unknown scenario")
    raise HTTPException(status_code=501, detail="Adversarial attacks are implemented in Phase 7")
