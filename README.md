# ModelLedger — AI Content Provenance & Verification Network

Hackathon problem: **Blockchain PS3 — prove which AI model produced this.**

Status: **Phase 0 + Phase 1 + Phase 2 + Phase 3 + Phase 4 complete** (see `docs/PROGRESS.md`).

ModelLedger records and verifies the origin and transformation history of AI-generated artifacts across multiple models/applications, using hashes, provenance evidence and a blockchain registry, without exposing private prompts or files. It never reduces the answer to "real/fake": results are `TRUSTED`, `SELF_ASSERTED`, `UNVERIFIABLE` or `CONFLICT`, each with evidence.

## Run it (backend + UI)

Requirements: Python 3.10+.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn main:app --reload
```

Open **http://127.0.0.1:8000** (UI) and **http://127.0.0.1:8000/docs** (interactive API).

### Phase 2 database

The backend now uses a persistent **SQLite** database. It is created automatically at:

```text
data/modelledger.db
```

You can override the location with `MODELLEDGER_DB_PATH`. The schema contains:

- `models`
- `artifacts`
- `provenance_events`
- `claims`
- `identities`

No separate database server is required for the local MVP.

## Run the tests

```bash
cd backend && python -m pytest -q
```

The current backend suite contains **17 tests**, including a persistence test that verifies records survive a new database-store instance.

Legacy blockchain tests remain available:

```bash
cd blockchain && npm install && npm test
```

## Try the current flow in the UI

1. Register model **ModelA v1.0** and **ModelB v2.0**.
2. Register an image with ModelA and no parent → recorded as `GENERATED`.
3. Register a second image with ModelB, parent = the first artifact, action = `UPSCALED`.
4. Verify the second image → lineage is reconstructed from the database and the current evidence produces `SELF_ASSERTED` because signatures and blockchain persistence are later-phase work.
5. Restart the backend and verify that the registered models, artifacts and provenance events are still present.

## Phase 3 + 4 blockchain and cryptographic setup

Install blockchain dependencies and deploy the registry:

```bash
cd blockchain
npm install
npm test
npx hardhat node
npm run deploy:local -- --network localhost
```

Configure `MODELLEDGER_RPC_URL`, `MODELLEDGER_CONTRACT_ADDRESS`, and `MODELLEDGER_TX_PRIVATE_KEY` in the backend environment. For signed provenance claims, configure `MODELLEDGER_SIGNATURE_PRIVATE_KEY_PEM` with a secp256k1 PEM private key.

The backend remains usable offline. In that mode, blockchain checks are explicitly `not_checked` and cannot produce `TRUSTED`.

## Repository layout

See `docs/PHASE1_REFACTOR.md` and `docs/PHASE2_DATABASE.md`. The baseline audit is in `docs/PHASE0_BASELINE.md`. The original marksheet application is preserved under `legacy/` and the baseline git state is tagged `baseline-dhruv`.

## Configuration

Environment variables are used for runtime configuration (see `.env.example`). No secrets or contract addresses are hard-coded.
