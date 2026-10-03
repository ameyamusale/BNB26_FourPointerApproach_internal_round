# Phase 4 — Cryptographic evidence layer

## Implemented

### Exact hash
SHA-256 remains the exact-byte identity check.

### Robust fingerprint
Images receive a pHash-style perceptual fingerprint after EXIF orientation normalization, grayscale conversion and resize. It is used only as supporting evidence for transformations.

### Digital signatures
Provenance events can be signed with an ECDSA secp256k1 private key supplied through `MODELLEDGER_SIGNATURE_PRIVATE_KEY_PEM`. The event stores the signature and public verification key; the private key is never stored.

### Evidence object
Verification reports now combine:

- exact artifact match
- model registration
- parent/lineage integrity
- robust transformation consistency
- signature validity
- blockchain commitment state
- revocation state

`TRUSTED` is only reachable when all required evidence is actually established. Missing blockchain/signature evidence remains `not_checked`; it is never treated as success.

## Testing

The backend suite covers stable fingerprints, valid signatures and tampered-signature rejection in addition to the original API/service tests.
