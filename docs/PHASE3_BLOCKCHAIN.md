# Phase 3 — ModelLedgerRegistry blockchain layer

Phase 3 replaces the legacy `DocumentRegistry.sol` with `ModelLedgerRegistry.sol`.

## Implemented

- Model registration commitment
- Artifact registration commitment
- Parent/child provenance events
- Event history lookup
- Model revocation
- Provenance-claim revocation
- Duplicate prevention
- Unauthorized revocation checks
- Python blockchain adapter with real RPC reads/writes
- Explicit offline/dependency-missing states; no silent verification success

## On-chain privacy rule

Only compact identifiers, hashes/commitments, actions, issuer addresses, timestamps and status are stored. Images, prompts, private datasets, model binaries and biometric information remain off-chain.

## Local setup

```text
cd blockchain
npm install
npm test
npx hardhat node
npm run deploy:local -- --network localhost
```

Then configure the backend with the printed contract address and an authorized transaction private key:

```text
MODELLEDGER_RPC_URL=http://127.0.0.1:8545
MODELLEDGER_CONTRACT_ADDRESS=<deployed address>
MODELLEDGER_TX_PRIVATE_KEY=<authorized local account private key>
```

The Python adapter requires `backend/requirements-chain.txt`.
