# ModelLedger — blockchain workspace

Hardhat 2 + ethers v6.

## Active contract

`ModelLedgerRegistry.sol` is the Phase 3 registry. The legacy `DocumentRegistry.sol` remains only for historical baseline compatibility.

The active registry supports model commitments, artifact commitments, parent/child provenance events, event history, model revocation and claim revocation.

```bash
npm install
npm test
npm run node
# in another terminal
npm run deploy:local
```

The deploy command prints `MODELLEDGER_RPC_URL`, `MODELLEDGER_CONTRACT_ADDRESS` and the private-key configuration name expected by the backend.

Hardhat downloads Solidity compiler `0.8.27` on first use, so the first install/compile requires npm and compiler-network access.
