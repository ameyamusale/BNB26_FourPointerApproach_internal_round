# ModelLedger progress

- [x] **Phase 0** — baseline frozen (`baseline-dhruv`, branch `modelledger-main`)
- [x] **Phase 1** — domain refactor (models / artifacts / provenance)
- [x] Phase 2 — database layer (`models`, `artifacts`, `provenance_events`, `claims`, `identities`)
- [x] Phase 3 — `ModelLedgerRegistry.sol` + tests + backend adapter
- [x] Phase 4 — signatures, robust fingerprint, evidence object
- [ ] Phase 5 — provenance graph + verification UI
- [ ] Phase 6 — multi-model transformation pipeline
- [ ] Phase 7 — trust engine rules, conflicts, adversarial lab
- [ ] Phase 8 — Proof of Creator (stretch)
- [ ] Phase 9 — privacy / hardening pass
- [ ] Phase 10 — polished frontend + demo


## Phase 2 implementation note

Phase 2 is complete. The in-memory persistence boundary has been replaced with a persistent SQLite database at `data/modelledger.db` by default. The schema contains `models`, `artifacts`, `provenance_events`, `claims`, and `identities`, with foreign keys and indexes. Existing Phase 1 service APIs continue to use the store facade, so the domain/API layer did not need to be rewritten.


## Phase 3 implementation note

The legacy `DocumentRegistry.sol` remains only as a historical baseline. The active contract is `ModelLedgerRegistry.sol`, with model/artifact/provenance registration, lineage links, revocation and compact on-chain commitments. The Python adapter uses real RPC calls when configured and otherwise reports an explicit offline state.

## Phase 4 implementation note

Phase 4 adds a pHash-style image fingerprint, secp256k1 ECDSA provenance signatures, signature verification, transformation fingerprint checks, and a combined evidence object. The backend cannot report blockchain-backed trust unless the chain was actually queried.
