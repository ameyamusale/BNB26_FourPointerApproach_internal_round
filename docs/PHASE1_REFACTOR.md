# Phase 1 — Domain refactor: Document → Model / Artifact / Provenance ✅

## New structure (matches the plan)
```
backend/
├── main.py                  composition, CORS, /health, /api/status
├── config.py                env-driven settings (no hard-coded addresses)
├── api/        models · artifacts · provenance · verification · adversarial · deps
├── services/   hashing · fingerprint* · model_registry · artifact_registry · provenance
│               verification · trust_engine · signature* · transformation* · conflict_detector*
│               blockchain* · store (in-memory) · errors
├── models/     model · artifact · provenance · claims      (pydantic schemas)
└── tests/      test_services.py · test_api.py              (16 tests)
frontend/       index.html · app.js · styles.css            (ModelLedger console)
blockchain/     legacy DocumentRegistry until Phase 3
legacy/         archived marksheet code (see legacy/README.md)
```
`*` = interface + honest stub, filled in by a later phase.

## What works now
* Register a **model** (metadata hash; optional client-computed weights hash; duplicate prevention).
* Register an **artifact** (SHA-256 of the upload, duplicate-bytes prevention, file not stored).
* Record **provenance events** (GENERATED, UPSCALED, EDITED, RESIZED, CROPPED, FILTERED, RE_ENCODED, PUBLISHED). Private metadata is hashed, never stored.
* Reconstruct **lineage** across several models/applications.
* **Verify** an upload → structured evidence + trust state (`TRUSTED / SELF_ASSERTED / UNVERIFIABLE / CONFLICT`).
* Adversarial scenario **catalogue** (attacks themselves are Phase 7).

## What is deliberately stubbed (and shown as "not checked", never as passed)
| Capability | Phase |
|---|---|
| Database persistence (currently in-memory) | 2 |
| On-chain registry (`ModelLedgerRegistry`) | 3 |
| Signatures, robust fingerprint | 4 |
| Graph UI, conflict detection, transformation checks | 5–7 |

Because signature and blockchain evidence are `None`, **no artifact can reach TRUSTED in Phase 1**. The best an honest registry-only result can be is `SELF_ASSERTED`. The trust-engine rules for TRUSTED are already final and tested.

## Design decisions to know about
* **Tri-state evidence** (`true` / `false` / `null = not checked`) is the mechanism that enforces "no silent success".
* One creating event per artifact for now (409 otherwise). Phase 7 relaxes this so competing claims can exist and be flagged as `CONFLICT`.
* Revoked model → status `SELF_ASSERTED` with flag `REVOKED` (history kept, trust withdrawn). Revisit in Phase 7 if you want a dedicated state.
* Uploads are image-only for the MVP (png/jpg/jpeg/webp/gif/bmp, ≤10 MB), validated by extension and size.

## Old → new map
| Baseline | Now |
|---|---|
| `backend/main.py` | `backend/main.py` (composition only) + `api/*` |
| `hash_service.py` | `services/hashing.py` |
| `blockchain_service.py` / `blockchain_routes.py` | `services/blockchain.py` (stub, honest) |
| `verification/` (CGPA rules) | `services/verification.py` + `services/trust_engine.py` |
| OCR / extractor / preprocessing | `legacy/` |
| `frontend/*` | new `frontend/*` |
| `dataset/` | `legacy/dataset/` (adversarial fixtures later) |

## Exit condition
A generic model and artifact can be registered, linked by provenance events, and verified (blockchain persistence stubbed). ✔
