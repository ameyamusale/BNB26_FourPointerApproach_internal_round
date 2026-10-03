# ModelLedger progress

- [x] **Phase 0** — baseline frozen (`baseline-dhruv`, branch `modelledger-main`)
- [x] **Phase 1** — domain refactor (models / artifacts / provenance)
- [x] Phase 2 — database layer (`models`, `artifacts`, `provenance_events`, `claims`, `identities`)
- [x] Phase 3 — `ModelLedgerRegistry.sol` + tests + backend adapter
- [x] Phase 4 — signatures, robust fingerprint, evidence object
- [x] Phase 5 — provenance graph + verification UI
- [x] Phase 6 — multi-model transformation pipeline
- [x] Phase 7 — trust engine rules, conflicts, adversarial lab
- [ ] Phase 8 — Proof of Creator (stretch)
- [ ] Phase 9 — privacy / hardening pass
- [ ] Phase 10 — polished frontend + demo


## Phase 2 implementation note

Phase 2 is complete. The in-memory persistence boundary has been replaced with a persistent SQLite database at `data/modelledger.db` by default. The schema contains `models`, `artifacts`, `provenance_events`, `claims`, and `identities`, with foreign keys and indexes. Existing Phase 1 service APIs continue to use the store facade, so the domain/API layer did not need to be rewritten.


## Phase 3 implementation note

The legacy `DocumentRegistry.sol` remains only as a historical baseline. The active contract is `ModelLedgerRegistry.sol`, with model/artifact/provenance registration, lineage links, revocation and compact on-chain commitments. The Python adapter uses real RPC calls when configured and otherwise reports an explicit offline state.

## Phase 4 implementation note

Phase 4 adds a pHash-style image fingerprint, secp256k1 ECDSA provenance signatures, signature verification, transformation fingerprint checks, and a combined evidence object. The backend cannot report blockchain-backed trust unless the chain was actually queried.

## Phase 5 implementation note

Phase 5 adds the provenance graph service (`services/graph.py`), model/artifact passports (`services/passport.py`), and a multi-page UI: `/dashboard`, `/models`, `/artifacts`, `/verify`, `/audit`, `/adversarial`, `/demo`, plus `/models/{id}`, `/artifacts/{id}` and `/lineage/{id}` passport/lineage pages. The dashboard renders the whole-registry graph; passports assemble hashes, lineage, events and blockchain references.

## Phase 6 implementation note

Phase 6 adds the one-click multi-model pipeline (`POST /api/demo/pipeline`, page `/demo`): Model A generates Artifact A, Model B upscales it into Artifact B, and an editor application re-encodes it into Artifact C. Each step creates a new artifact ID, a signed provenance event and an on-chain commitment. The pipeline is re-runnable (per-run pixel marker prevents duplicate hashes; demo models are reused per seed label).

## Phase 7 implementation note

Phase 7 completes the trust engine wiring (conflicts from competing claims and origin-model mismatches), upgrades the conflict detector, and makes the Adversarial Lab executable: `POST /api/adversarial/run/{scenario}` runs tamper-artifact, forge-claim, remove-step, conflicting-claims and revoke-model against real state and returns the full evidence behind the resulting trust state. All five attacks are covered by tests.
