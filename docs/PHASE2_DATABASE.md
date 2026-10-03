# Phase 2 — Off-chain database layer ✅

## Goal

Replace Phase 1 in-memory persistence with a real persistent database while keeping the existing ModelLedger domain/API contracts stable.

## Implementation

The MVP uses **SQLite** as its default off-chain database. SQLite is part of Python, so the project can be cloned and run locally without installing a separate database server. The database path is configurable with `MODELLEDGER_DB_PATH`; the default is `data/modelledger.db`.

The database is initialized automatically when the FastAPI application imports the persistence layer. No manual migration command is required for a fresh checkout.

## Schema

### `models`
Stores the registered AI model identity, version, type, creator, model commitment, metadata commitment, status and timestamp.

### `artifacts`
Stores artifact ID, modality, exact SHA-256, optional robust fingerprint, size, optional storage reference, claimed model, status and timestamp. Exact hashes are unique.

### `provenance_events`
Stores parent/child artifact relationships, model/application actor, transformation action, private-metadata commitment, signature placeholder, blockchain transaction placeholder and timestamp. Each artifact has at most one creating event in the current Phase 1/2 domain rules.

### `claims`
Provides the Phase 2 persistence table for provenance/verification claims, including issuer, evidence type, signature, status and structured evidence JSON. Claim-writing helpers are ready for the Phase 3/4 evidence flow.

### `identities`
Stores creator/application identity references, wallet reference, role, optional biometric enrollment reference, status and creation time. Raw biometric data is not stored.

## Persistence boundary

The existing service layer still calls `services.store.store`, but that object is now a `SQLiteStore`. This keeps Phase 1 APIs stable while replacing the storage implementation underneath them.

```text
FastAPI routes
      ↓
Domain services
      ↓
SQLiteStore repository facade
      ↓
SQLite database

models / artifacts / provenance_events / claims / identities
```

## Integrity controls

- Foreign keys are enabled.
- Exact artifact hashes are unique.
- Model metadata commitments are unique.
- Parent/child provenance references use foreign keys.
- Provenance events are indexed by parent and child artifact.
- Model/artifact/event reads reconstruct the existing Pydantic domain objects.
- Model registration creates/updates its creator identity in the same database transaction.
- The database survives backend restarts.

## Verification

The backend test suite now includes a persistence test that opens a second `SQLiteStore` against the same database and retrieves a model created by the first store instance.

Current validation: **17 tests passing**.

## Phase 2 exit condition

> The backend can create and retrieve models, artifacts and provenance events without relying on blockchain queries, and the records remain available after the process restarts.
