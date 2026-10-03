# Phase 0 — Freeze the baseline ✅

## What was done
| Plan action | Result |
|---|---|
| Snapshot the current `Dhruv` state | git tag **`baseline-dhruv`** (commit `652794e`). `git checkout baseline-dhruv` restores the old app at any time. |
| Create a dedicated branch | **`modelledger-main`** (all ModelLedger work lives here) |
| Run the existing application | Backend tests run (see below). Hardhat tests run (see below). |
| Record environment/setup commands | Below |
| Confirm Hardhat deploy/test flow | Works **after** fixing a broken contract file (finding #1) |

## Baseline setup commands (old app)
```bash
git checkout baseline-dhruv
# backend (no requirements.txt existed; this is what was needed)
pip install fastapi "uvicorn[standard]" python-multipart pypdf pytest httpx
cd backend && python -m pytest tests -q
# blockchain
cd ../blockchain && npm install && npx hardhat test
```

## Baseline results
* **Backend:** `2 failed, 1 passed`. Both failures are in `tests/test_api_flow.py` (`roll_number` is extracted as `None`).
* **Hardhat:** could not compile as shipped (finding #1). With a valid contract the 4 tests pass and `deploy.js` deploys.

## Findings in the baseline (all addressed in Phase 1 unless noted)
1. **`DocumentRegistry.sol` was not Solidity.** Its content was a copy of the JS test file, so nothing could compile or deploy. → Contract reconstructed from the test (kept as legacy until Phase 3).
2. **Silent blockchain success.** `main.py` and `blockchain_service.py` returned `{"verified": true}` when the chain was missing. This is exactly what the plan's Rule 5 forbids. → `services/blockchain.py` reports `mode: stub`, `connected: false` and `None` for unchecked evidence.
3. **Placeholder contract address** `0xYourDeployedAddressHere` and a dead branch `_load_contract() if False else None`. → address/RPC come from environment variables.
4. **Hard-coded student fallbacks** ("Rahul Sharma", "ABC University"). → removed with the marksheet domain.
5. **CORS** `*` together with `allow_credentials=True`. → explicit local origins, no credentials.
6. **Version mismatch:** root `package.json` had Hardhat 3, `blockchain/` had Hardhat 2; `ignition/modules/Lock.js` referenced a contract that doesn't exist. → root package is now just helper scripts; Lock module removed.
7. `preprocessing.py` hard-coded a Windows Poppler path (`D:\codes\...`). → archived in `legacy/`.
8. No `requirements.txt`. → `backend/requirements*.txt` added.
9. Every file used CRLF line endings, which produced whole-file diffs. → `.gitattributes` normalises to LF.
10. Latent: `.gitignore` contained `models/`, which would have silently ignored the new `backend/models/` package. → anchored to `/models/`.

## Exit condition
The old application is preserved (`baseline-dhruv`) and restorable. ✔

> Not verified in this environment: the old OCR stack (PaddleOCR/Tesseract/Poppler) and a live `hardhat node` + FastAPI integration, because the baseline never had a working contract or configured address.
