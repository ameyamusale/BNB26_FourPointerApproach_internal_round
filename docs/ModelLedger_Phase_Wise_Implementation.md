# ModelLedger — Phase-Wise Implementation Plan

## Project context

**Hackathon Problem Statement:** Blockchain PS3 — **ModelLedger: Prove Which AI Model Produced This**

**Starting point:** Existing GitHub repository, `Dhruv` branch:
`https://github.com/ameyamusale/Blockchian-based-document-verification-system-/tree/Dhruv`

**Important:** The existing repository is a **baseline only**. The goal is to refactor it into a new project purpose-built for ModelLedger, not to rename the old document-verification application.

---

# 1. What the existing Dhruv branch already provides

The current repository gives us a useful technical foundation:

- FastAPI backend in `backend/main.py`
- Service-oriented backend pieces under `backend/app/services/`
- SHA-256 hashing in `hash_service.py`
- OCR / preprocessing / field extraction services
- Blockchain service and blockchain API routes
- Hardhat blockchain setup
- `DocumentRegistry.sol`
- Contract deployment script and tests
- Simple HTML/CSS/JavaScript frontend
- Original/tampered test-data structure

The current application is centered around **university/marksheet document verification**. The backend extracts fields such as name, roll number, university, semester and CGPA and then combines file hashing with blockchain verification.

That architecture is useful as a starting skeleton, but the core domain must change from:

> **Document verification**

to:

> **AI-generated content provenance and evidence-based verification**

---

# 2. Target product

## ModelLedger
### AI Content Provenance & Verification Network

### One-line project definition

> ModelLedger establishes, records, and verifies the provenance of AI-generated artifacts across multiple AI models and applications without exposing private prompts or source files.

### What the system should answer

When a verifier receives an AI-generated artifact, the system should help answer:

1. What is the claimed origin?
2. Which model/application created it?
3. Which version was involved?
4. What transformations happened afterward?
5. Who/what made each provenance claim?
6. What cryptographic evidence supports the claim?
7. Is the provenance **Trusted**, **Self-Asserted**, or **Unverifiable**?
8. Is there a conflict or tampering signal?
9. Can the history be verified without exposing private prompts or source data?

---

# 3. Core product philosophy

Do **not** build a generic "AI fake detector".

Do **not** put complete images, models, prompts or private datasets on-chain.

Do **not** claim that blockchain itself proves truth.

Instead use this model:

```text
AI Model / Application
        |
        | makes provenance claim
        v
Artifact + provenance evidence
        |
        | fingerprint / signature
        v
ModelLedger backend
        |
        +---- exact hash
        +---- robust/content fingerprint
        +---- signature verification
        +---- lineage / provenance graph
        +---- trust evaluation
        |
        v
Blockchain commitment / registry
        |
        v
Independent verification
```

Blockchain provides a tamper-evident shared record. Cryptography establishes integrity and authorship of claims. Off-chain services handle computation, search and private data.

---

# 4. Target system architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                         USERS                                  │
│ Creator | AI Developer | Auditor | Organization | Verifier   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               v
┌─────────────────────────────────────────────────────────────────┐
│                       MODELLEDGER UI                           │
│                                                                 │
│ Dashboard | Register Model | Register Artifact | Verify       │
│ Model Passport | Artifact Passport | Lineage | Audit | Lab   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               v
┌─────────────────────────────────────────────────────────────────┐
│                        FASTAPI API                             │
│                                                                 │
│ Identity / Auth                                                │
│ Model Registry                                                 │
│ Artifact Registry                                              │
│ Provenance Manager                                             │
│ Verification Engine                                            │
│ Trust Engine                                                   │
│ Transformation Engine                                         │
│ Conflict Detection                                             │
│ Adversarial Testing                                             │
└───────────────┬──────────────────────────────┬──────────────────┘
                │                              │
                v                              v
┌─────────────────────────────┐   ┌─────────────────────────────┐
│      CRYPTO / EVIDENCE      │   │       PROVENANCE GRAPH       │
│                             │   │                             │
│ SHA-256                     │   │ Model nodes                 │
│ Robust fingerprint          │   │ Artifact nodes              │
│ Digital signatures          │   │ Application nodes           │
│ Metadata commitments        │   │ Transformation edges        │
│ Signature validation        │   │ Evidence edges              │
└──────────────┬──────────────┘   └──────────────┬──────────────┘
               │                                 │
               └────────────────┬────────────────┘
                                v
┌─────────────────────────────────────────────────────────────────┐
│                    MODELLEDGER SMART CONTRACT                   │
│                                                                 │
│ Model registration | Artifact commitment | Provenance claims  │
│ Parent-child relationships | Revocation | Event history       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                 ┌─────────────┴─────────────┐
                 v                           v
        ┌──────────────────┐        ┌────────────────────┐
        │ BLOCKCHAIN       │        │ OFF-CHAIN STORAGE  │
        │ Immutable/evident│        │ MongoDB/Postgres   │
        │ commitments      │        │ IPFS/object store  │
        └──────────────────┘        │ encrypted/private │
                                    └────────────────────┘
```

---

# 5. Main modules

## A. Model Registry

Stores:

- model ID
- model name
- version
- creator identity
- model fingerprint
- model type
- registration timestamp
- current status
- optional model card metadata

### Example

```text
Model: VisionGen-X
Version: 2.1.0
Model Hash: A81F93...
Creator: Team Alpha
Wallet: 0x82A...
Status: ACTIVE
```

---

## B. Artifact Registry

Each AI-generated or transformed artifact receives an artifact ID.

For the MVP, start with **images**. Later the design can support other modalities.

Stores:

- artifact ID
- type
- exact SHA-256 hash
- robust/content fingerprint
- parent artifact
- current provenance status
- storage reference
- timestamps

---

## C. Provenance Event System

Every meaningful transformation becomes an event.

```text
GENERATED
UPSCALED
EDITED
RESIZED
CROPPED
FILTERED
RE-ENCODED
PUBLISHED
```

Example:

```text
Event #82371
Input Artifact: IMG-100
Output Artifact: IMG-101
Actor: Model B
Action: UPSCALE
Version: 2.0
Timestamp: ...
Signature: ...
```

---

## D. Provenance Graph

The UI should show lineage visually:

```text
                 Model A v1.0
                      |
                   generated
                      v
                 Artifact #001
                      |
                   upscaled
                      v
                 Model B v2.0
                      |
                    edited
                      v
                 Artifact #002
                      |
                 published by
                      v
                Application C
```

This is one of the primary product features.

---

## E. Verification Engine

Verification should combine several forms of evidence.

### Exact integrity

```text
SHA-256(current artifact)
          ==
registered exact hash?
```

### Signature validity

```text
provenance claim
       |
       v
valid digital signature?
```

### Lineage consistency

```text
parent exists?
transformation recorded?
child linked correctly?
```

### Blockchain evidence

```text
record exists?
commitment matches?
revoked?
```

---

# 6. Trust states

The final system should not reduce every case to "real/fake".

## TRUSTED

Use when the available provenance claims are supported by verifiable evidence and the lineage is internally consistent.

## SELF-ASSERTED

Use when the creator/application claims an origin, but there is not enough independent or cryptographic evidence to establish it.

## UNVERIFIABLE

Use when the available evidence is insufficient to establish the origin or history.

## CONFLICT / INCONSISTENT

This is an important alert state when different provenance claims disagree or the artifact does not match its claimed history.

---

# 7. Unique features planned for the hackathon

## Feature 1 — Model Passport

A profile for every registered model.

Shows:

- model identity
- version history
- fingerprint
- creator
- registrations
- status
- provenance events

---

## Feature 2 — Artifact Passport

A verifiable profile for every artifact.

Shows:

- artifact ID
- current fingerprint
- claimed origin
- current status
- transformation count
- provenance depth
- blockchain references

---

## Feature 3 — Multi-Model Provenance Graph

Example:

```text
Model A
  |
  v
Image 1
  |
  v
Model B
  |
  v
Image 2
  |
  v
Editor C
  |
  v
Final Artifact
```

---

## Feature 4 — Transformation-Aware Verification

Support legitimate changes that make a byte-for-byte hash different.

Use:

- exact cryptographic hash for exact identity
- robust/content fingerprint for transformation support
- provenance event describing the transformation

The system should say something like:

```text
Exact bytes: CHANGED
Known transformation: RESIZE
Transformation claim: VERIFIED
Lineage: CONSISTENT
```

Rather than simply calling the transformed artifact fake.

---

## Feature 5 — Conflict Detector

Example:

```text
Claim A:
Model A created this artifact
Evidence: blockchain-backed

Claim B:
Model C created this artifact
Evidence: self-asserted
```

Output:

```text
PROVENANCE CONFLICT DETECTED
```

The user should be able to inspect both claims and their evidence.

---

## Feature 6 — Provenance Revocation

Allow an issuer/authorized entity to revoke a previously trusted claim or model registration without deleting its history.

Example:

```text
Model A v1
Registered: ✅

Later status:
REVOKED ⚠
Reason: compromised / withdrawn
```

---

## Feature 7 — Privacy-Preserving Verification

Do not publish:

- raw prompts
- private datasets
- private source files
- raw biometric data

Verify using commitments, hashes, signatures and references.

---

## Feature 8 — Proof of Creator (optional/high-value extra)

Use facial authentication as an **identity authorization layer**, not as the digital signature itself.

Correct model:

```text
Face + liveness
       |
       v
Human identity verified
       |
       v
Wallet / private-key authorization
       |
       v
Cryptographic signature
       |
       v
Provenance claim
       |
       v
Blockchain
```

### Important security rule

Do not store raw face images or face embeddings on a public blockchain.

For the hackathon MVP, the face feature should be framed as:

> **Proof of Creator — biometric-backed authorization of a provenance claim.**

---

## Feature 9 — Adversarial Lab

Create a dedicated page where judges can trigger attacks.

Controls:

```text
[ Tamper Artifact ]
[ Forge Provenance Claim ]
[ Create Conflicting Claim ]
[ Remove Provenance Step ]
[ Modify Model Metadata ]
[ Revoke Model ]
```

The expected result should be visible immediately.

---

# 8. End-to-end target workflow

```text
STEP 1
Register Creator / Identity
       |
       v
STEP 2
Register AI Model
       |
       v
STEP 3
Fingerprint model
       |
       v
STEP 4
Create artifact
       |
       v
STEP 5
Fingerprint artifact
       |
       v
STEP 6
Create provenance claim
       |
       v
STEP 7
Sign claim
       |
       v
STEP 8
Commit claim to blockchain
       |
       v
STEP 9
Transform artifact using Model B / App C
       |
       v
STEP 10
Create new child artifact
       |
       v
STEP 11
Create + sign transformation event
       |
       v
STEP 12
Verifier uploads final artifact
       |
       v
STEP 13
Reconstruct lineage
       |
       v
STEP 14
Check hashes + fingerprints + signatures + blockchain
       |
       v
STEP 15
Return:
TRUSTED / SELF-ASSERTED / UNVERIFIABLE / CONFLICT
```

---

# PHASE-WISE IMPLEMENTATION

# Phase 0 — Freeze the baseline and create the new branch

### Goal

Preserve the current `Dhruv` branch as the working reference and begin the ModelLedger refactor in a dedicated branch/repository state.

### Actions

1. Create a branch such as:

```text
modelledger-main
```

2. Tag/snapshot the current `Dhruv` state.
3. Run the existing application before modifying anything.
4. Record environment/setup commands.
5. Confirm the current Hardhat contract deploy/test flow.

### Baseline files identified

```text
backend/main.py
backend/app/services/hash_service.py
backend/app/services/blockchain_service.py
backend/app/services/blockchain_routes.py
backend/app/services/ocr_service.py
backend/app/services/field_extractor.py
backend/app/services/preprocessing.py
backend/app/services/qr_service.py
blockchain/contracts/DocumentRegistry.sol
blockchain/scripts/deploy.js
blockchain/test/DocumentRegistry.test.js
frontend/index.html
frontend/upload.html
frontend/result.html
frontend/details.html
frontend/app.js
frontend/styles.css
```

### Exit condition

The old application still works and can be restored at any time.

---

# Phase 1 — Domain refactor: Document -> Model / Artifact / Provenance

### Goal

Remove marksheet-specific assumptions from the application domain.

### Refactor

Current concepts:

```text
Document
Roll Number
University
Semester
CGPA
```

New concepts:

```text
Model
Artifact
Provenance Event
Provenance Claim
Creator
Transformation
Verification Evidence
```

### Backend work

Split `backend/main.py` into domain routes/services.

Proposed structure:

```text
backend/
├── main.py
├── api/
│   ├── models.py
│   ├── artifacts.py
│   ├── provenance.py
│   ├── verification.py
│   └── adversarial.py
├── services/
│   ├── hashing.py
│   ├── fingerprint.py
│   ├── model_registry.py
│   ├── artifact_registry.py
│   ├── provenance.py
│   ├── verification.py
│   ├── trust_engine.py
│   ├── signature.py
│   ├── transformation.py
│   ├── conflict_detector.py
│   └── blockchain.py
└── models/
    ├── model.py
    ├── artifact.py
    ├── provenance.py
    └── claims.py
```

### Reuse immediately

Keep and adapt:

- SHA-256 hashing service
- blockchain communication patterns
- FastAPI setup
- CORS/setup
- frontend styling ideas
- Hardhat configuration
- test/deployment workflow

### Remove from the main domain

- marksheet-only extraction
- CGPA validation
- university/semester logic
- hard-coded student fallbacks
- document-only verification states

### Exit condition

You can register a generic model and generic artifact conceptually, even if blockchain persistence is still stubbed.

---

# Phase 2 — New data model and off-chain database

### Goal

Create the data layer before expanding blockchain functionality.

### Collections/tables

## `models`

```text
model_id
name
version
model_type
creator_id
model_hash
metadata_hash
created_at
status
```

## `artifacts`

```text
artifact_id
artifact_type
exact_hash
robust_fingerprint
storage_uri
created_at
status
```

## `provenance_events`

```text
event_id
parent_artifact_id
child_artifact_id
model_id
application_id
action
metadata_hash
signature
created_at
blockchain_tx
```

## `claims`

```text
claim_id
artifact_id
claim_type
issuer_id
evidence_type
signature
status
created_at
```

## `identities`

```text
identity_id
name
wallet_address
role
biometric_enrollment_reference
status
```

### Exit condition

The backend can create and retrieve models, artifacts and provenance events without relying on blockchain queries.

---

# Phase 3 — Replace DocumentRegistry with ModelLedgerRegistry

### Goal

Refactor the smart contract from a document hash registry into a provenance registry.

### Proposed contract modules

Prefer one clear MVP contract or small contract set.

```text
ModelLedgerRegistry
├── registerModel()
├── registerArtifact()
├── addProvenanceEvent()
├── getModel()
├── getArtifact()
├── getArtifactEvents()
├── revokeModel()
└── revokeClaim()
```

### Important on-chain fields

Keep on-chain data compact:

```text
modelId
artifactId
parentArtifactId
modelHash / commitment
artifactHash / commitment
action
issuer / wallet
signature reference / claim hash
timestamp
status
```

### Do not store on-chain

- images
- videos
- prompts
- model binary files
- private datasets
- raw biometric information

### Tests to add

1. Model registration.
2. Artifact registration.
3. Parent-child provenance link.
4. Transformation event.
5. Duplicate prevention.
6. Revocation.
7. Unauthorized mutation rejection.
8. Retrieval of lineage/event history.

### Exit condition

A model and an artifact can be registered on-chain and linked by a provenance event.

---

# Phase 4 — Cryptographic evidence layer

### Goal

Turn ModelLedger into a genuine evidence-based verification platform.

### 4.1 Exact hash

Reuse and generalize the current SHA-256 service.

```text
file bytes
   |
   v
SHA-256
   |
   v
exact_hash
```

### 4.2 Robust fingerprint

Add a modality-aware fingerprint for the MVP image workflow.

Purpose:

> Detect/associate legitimate transformations even when the exact bytes change.

Do not treat this as absolute proof. It is supporting evidence.

### 4.3 Digital signatures

Implement a signed provenance claim flow:

```text
claim payload
    |
    v
wallet/private key
    |
    v
digital signature
```

### 4.4 Evidence object

Every verification should produce structured evidence:

```json
{
  "artifact_match": true,
  "model_registered": true,
  "signature_valid": true,
  "parent_exists": true,
  "transformation_valid": true,
  "blockchain_record": true,
  "revoked": false
}
```

### Exit condition

The backend can independently verify a provenance claim using cryptographic evidence.

---

# Phase 5 — Provenance Graph + verification engine

### Goal

Make the provenance understandable to a human.

### Build graph representation

```text
nodes:
- MODEL
- ARTIFACT
- APPLICATION
- CREATOR

edges:
- GENERATED
- TRANSFORMED
- EDITED
- PUBLISHED
```

### Verification engine flow

```text
Artifact upload
     |
     v
Exact hash
     |
     v
Robust fingerprint
     |
     v
Locate provenance claims
     |
     v
Validate signatures
     |
     v
Reconstruct lineage
     |
     v
Check blockchain
     |
     v
Check revocation
     |
     v
Trust engine
```

### Output

```text
TRUSTED
SELF-ASSERTED
UNVERIFIABLE
CONFLICT / INCONSISTENT
```

### UI pages

```text
/dashboard
/models
/models/:id
/artifacts
/artifacts/:id
/verify
/lineage/:id
/audit
/adversarial
```

### Exit condition

A judge can upload an artifact and visually understand its provenance graph and evidence.

---

# Phase 6 — Multi-model transformation pipeline

### Goal

Demonstrate the exact scenario described by the problem statement.

### Build a controlled demo pipeline

```text
Model A
  |
  | generate
  v
Artifact A
  |
  | Model B upscale
  v
Artifact B
  |
  | Editor resize/re-encode
  v
Artifact C
```

### Each step creates

- new artifact ID
- parent artifact ID
- action
- model/application identity
- output fingerprint
- signed provenance claim
- blockchain event

### Exit condition

The system can reconstruct a multi-step lineage across more than one model/application.

---

# Phase 7 — Trust engine + conflict + adversarial lab

### Goal

Turn the project into an investigation platform.

## Trust engine rules

### Trusted

Require a defined minimum evidence set, for example:

```text
registered origin
+
valid signature
+
consistent artifact fingerprint
+
valid lineage
+
blockchain evidence
+
not revoked
```

### Self-asserted

```text
claim exists
but evidence is insufficient
```

### Unverifiable

```text
not enough information to establish origin
```

### Conflict

```text
multiple incompatible provenance claims
```

## Adversarial scenarios

### Attack A — Tampered artifact

Modify the file after registration.

Expected:

```text
EXACT HASH MISMATCH
PROVENANCE INCONSISTENCY
```

### Attack B — Forged claim

Create a false claim for another model.

Expected:

```text
SIGNATURE INVALID / CLAIM NOT SUPPORTED
```

### Attack C — Missing provenance step

Delete one event from the claimed history.

Expected:

```text
BROKEN LINEAGE
```

### Attack D — Conflicting claims

Create two origin claims.

Expected:

```text
PROVENANCE CONFLICT DETECTED
```

### Attack E — Revoked model

Register model, later revoke it.

Expected:

```text
PROVENANCE AVAILABLE
BUT MODEL/CLAIM REVOKED
```

### Exit condition

The adversarial page can demonstrate at least 3 attacks live and show the evidence behind each result.

---

# Phase 8 — Proof of Creator (facial authentication)

### Goal

Add the unique biometric-backed authorization layer after the cryptographic core is stable.

### Principle

**Face is authentication/identity evidence. Private-key signature is the actual cryptographic signature.**

### Flow

```text
Creator
   |
   v
Face capture
   |
   v
Liveness / anti-spoof check
   |
   v
Identity match
   |
   v
Wallet/private-key authorization
   |
   v
Signed provenance claim
   |
   v
Blockchain
```

### UI

```text
PROOF OF CREATOR

Face detected            ✅
Liveness                  ✅
Identity match            ✅
Wallet authorization      ✅
Claim signature            ✅
Blockchain registration   ✅
```

### Privacy

Keep raw biometric information off-chain. Store only the minimum secure reference/commitment needed by the architecture.

### Exit condition

A creator can authorize a model or provenance claim through biometric-backed identity verification followed by cryptographic signing.

---

# Phase 9 — Privacy and production-hardening pass

### Goal

Make the architecture defensible under judge questions.

### Required controls

- never expose private prompts in normal verification
- never place large files on-chain
- keep secrets in environment variables
- avoid hard-coded blockchain account addresses
- validate uploads
- validate signature payloads
- enforce role/permission checks
- log verification decisions
- separate private data from public provenance metadata
- handle blockchain/network failure explicitly

### Important correction from the baseline

The current blockchain service contains a placeholder contract address and fallback behavior when blockchain integration is unavailable. The ModelLedger implementation must not silently present a positive verification result when blockchain verification is not actually available.

### Exit condition

Every displayed trust result can be explained by real evidence and real system state.

---

# Phase 10 — Complete frontend and judge experience

### Goal

Turn the technical system into a polished demo.

## Main dashboard

Show:

```text
Models              24
Artifacts        1,482
Verified          892
Conflicts           12
Revoked              3
Unverifiable        47
```

## Model Passport

```text
VisionGen-X v2.1
Creator: Team Alpha
Model Hash: A81F...
Status: ACTIVE
Provenance Events: 123
```

## Artifact Passport

```text
Artifact #1024
Origin: VisionGen-X v2.1
Status: TRUSTED
Transformations: 3
```

## Lineage page

Interactive graph:

```text
Model A -> Artifact 1 -> Model B -> Artifact 2 -> Editor -> Final
```

## Verification page

Show evidence checklist.

## Adversarial Lab

Show attack controls and resulting evidence.

---

# 11. Final 3-minute demo flow

This should be the demo the team rehearses first.

## 0:00–0:25 — Register model

```text
Model A v1.0
Creator verified
Fingerprint generated
Blockchain registration ✅
```

## 0:25–0:50 — Generate artifact

```text
Model A
   ↓
Artifact #001
```

Create provenance claim.

## 0:50–1:15 — Transform through another system

```text
Artifact #001
   ↓
Model B
   ↓
Artifact #002
```

Show the signed transformation event.

## 1:15–1:35 — Show lineage

```text
Model A
   ↓
Artifact #001
   ↓
Model B
   ↓
Artifact #002
```

## 1:35–1:55 — Verify

```text
Origin                ✅
Model registration    ✅
Signature             ✅
Transformation        ✅
Blockchain evidence   ✅
Revocation            ✅

STATUS: TRUSTED
```

## 1:55–2:20 — Attack

Forge a provenance claim or tamper with the artifact.

```text
🚨 PROVENANCE INCONSISTENCY
```

## 2:20–2:45 — Conflict case

```text
Claim A: Model A
Evidence: strong ✅

Claim B: Model C
Evidence: self-asserted ⚠

⚠ CONFLICT DETECTED
```

## 2:45–3:00 — Proof of Creator

Show:

```text
Face + liveness ✅
Wallet authorization ✅
Signed provenance ✅
```

Final line:

> **“ModelLedger does not ask you to trust an AI-generated artifact. It lets you inspect and verify the evidence behind its provenance.”**

---

# 12. Recommended implementation order inside the team

## Member 1 — Blockchain / smart contracts

Own:

- ModelLedgerRegistry.sol
- contract tests
- deployment
- blockchain event schema
- wallet/signature verification

## Member 2 — Backend / verification engine

Own:

- FastAPI route refactor
- database models
- provenance graph data
- verification engine
- trust engine
- conflict detection

## Member 3 — AI / fingerprints / biometric layer

Own:

- robust artifact fingerprinting
- content transformation checks
- Proof of Creator prototype
- liveness/face integration
- adversarial test generation

## Member 4 (if available) — Frontend / demo

Own:

- dashboard
- model passport
- artifact passport
- lineage visualization
- verification evidence panel
- adversarial lab
- demo polish

If there are only 3 people, combine Member 4 with backend or split frontend ownership between Members 1 and 2.

---

# 13. MVP vs stretch features

## MUST HAVE

```text
✅ Model Registry
✅ Artifact Registry
✅ Exact hashing
✅ Provenance events
✅ Blockchain registry
✅ Digital signatures
✅ Verification engine
✅ Trusted / Self-Asserted / Unverifiable states
✅ Provenance graph
✅ At least 2-model pipeline
✅ At least 3 adversarial scenarios
```

## SHOULD HAVE

```text
✅ Robust/content fingerprint
✅ Transformation-aware verification
✅ Conflict detector
✅ Revocation
✅ Privacy-preserving metadata design
✅ Model/Artifact Passports
```

## STRETCH

```text
⭐ Proof of Creator
⭐ Liveness detection
⭐ Application identity
⭐ Public verification link
⭐ QR verification
⭐ IPFS provenance manifests
⭐ Advanced analytics
```

Do not sacrifice the core provenance system just to add the biometric feature.

---

# 14. Refactor map from the current Dhruv branch

| Current component | Action | New role |
|---|---|---|
| `backend/main.py` | Major refactor | API composition / startup |
| `hash_service.py` | Keep + generalize | Artifact fingerprinting |
| `blockchain_service.py` | Rewrite | ModelLedger blockchain adapter |
| `blockchain_routes.py` | Rewrite | Model/artifact/provenance API |
| `DocumentRegistry.sol` | Replace | `ModelLedgerRegistry.sol` |
| `deploy.js` | Modify | Deploy new registry |
| `DocumentRegistry.test.js` | Replace/expand | ModelLedger contract tests |
| `ocr_service.py` | Optional | Metadata extraction only, if needed |
| `field_extractor.py` | De-emphasize/remove | Replace with artifact metadata services |
| `preprocessing.py` | Reuse selectively | Artifact preprocessing |
| `qr_service.py` | Optional | Public verification link / QR |
| `frontend/index.html` | Replace | ModelLedger dashboard |
| `upload.html` | Replace | Register/verify artifact |
| `result.html` | Replace | Verification evidence |
| `details.html` | Replace | Artifact/model passport |
| `app.js` | Rewrite | ModelLedger client logic |
| `styles.css` | Reuse ideas / redesign | New product UI |
| original/tampered datasets | Keep concept | Adversarial test fixtures |

---

# 15. Critical technical rules

## Rule 1 — Blockchain is not the source of truth for the real world

A blockchain proves what was registered/committed and whether the record was altered. It does not independently prove that an initial provenance claim was true.

Therefore distinguish:

```text
Registered claim
vs.
Verified evidence
vs.
Truth in the physical world
```

## Rule 2 — Exact hash and robust fingerprint are different

Exact hash:

> “Are these exact bytes identical?”

Robust fingerprint:

> “Does this appear to be the same content after an allowed transformation?”

## Rule 3 — Face is not the digital signature

Use:

```text
Face/liveness -> identity authorization
Private key  -> cryptographic signature
Blockchain   -> tamper-evident record
```

## Rule 4 — On-chain data must be minimal

Store commitments and provenance metadata, not private content.

## Rule 5 — No silent success

If blockchain is offline, the UI must not say `VERIFIED` as if blockchain evidence was checked.

---

# 16. Evaluation checklist before submission

## Functional

- [ ] Register a model
- [ ] Register artifact
- [ ] Create provenance claim
- [ ] Sign claim
- [ ] Store claim on blockchain
- [ ] Transform artifact
- [ ] Verify final artifact
- [ ] Display lineage
- [ ] Detect tampering
- [ ] Detect conflict
- [ ] Distinguish trust states
- [ ] Handle a revoked model/claim

## Security/privacy

- [ ] No private prompts on-chain
- [ ] No raw biometric data on-chain
- [ ] No model binary on-chain
- [ ] Signature verification works
- [ ] Permissions are enforced
- [ ] Secrets use environment variables
- [ ] Blockchain failure is explicit

## Demo

- [ ] One clean artifact flow
- [ ] One legitimate transformation
- [ ] One tampering attack
- [ ] One conflicting claim
- [ ] One provenance graph
- [ ] One visible blockchain transaction/evidence reference
- [ ] Optional Proof of Creator demonstration

---

# 17. Definition of done

ModelLedger is ready when a judge can perform the following sequence without needing a verbal explanation from the team:

```text
1. See a model registered
2. See an AI artifact produced
3. See the artifact's provenance chain
4. See another model/application transform it
5. Verify the final artifact
6. Inspect the evidence
7. See TRUSTED status
8. Trigger a tamper/conflict case
9. See the status change and understand why
10. Inspect the immutable blockchain record
```

The project should feel like an **AI provenance investigation platform**, not an upgraded university document verifier.

---

# 18. Immediate next actions

### Day 1 — Baseline and refactor setup

```text
1. Clone Dhruv branch
2. Create modelledger-main branch
3. Run current system
4. Preserve baseline
5. Replace project terminology
6. Create new domain models
```

### Day 2 — Data model + contract

```text
1. Design MongoDB/Postgres schema
2. Write ModelLedgerRegistry.sol
3. Write tests
4. Deploy locally
5. Connect FastAPI
```

### Day 3 — Provenance engine

```text
1. Model registry
2. Artifact registry
3. Provenance events
4. Digital signatures
5. Verification engine
```

### Day 4 — Graph + transformations

```text
1. Multi-model pipeline
2. Parent-child artifacts
3. Robust fingerprinting
4. Lineage graph
5. Evidence panel
```

### Day 5 — Adversarial + biometric stretch

```text
1. Tamper attack
2. Fake claim attack
3. Conflict attack
4. Revocation
5. Proof of Creator prototype
```

### Day 6 — UI + integration

```text
1. Dashboard
2. Model Passport
3. Artifact Passport
4. Verification page
5. Adversarial Lab
6. Blockchain explorer links/references
```

### Day 7 — Demo hardening

```text
1. Remove dead features
2. Fix failure states
3. Prepare demo artifacts
4. Rehearse 3-minute pitch
5. Test offline/online blockchain behavior
6. Prepare judge Q&A
```

---

# 19. Final target architecture in one picture

```text
                         MODELLEDGER
                             |
          ┌──────────────────┼──────────────────┐
          |                  |                  |
       MODELS            ARTIFACTS          CREATORS
          |                  |                  |
          └──────────────────┼──────────────────┘
                             |
                    PROVENANCE CLAIM
                             |
              ┌──────────────┼──────────────┐
              |              |              |
           SHA-256        ROBUST FP      SIGNATURE
              |              |              |
              └──────────────┼──────────────┘
                             |
                     VERIFICATION ENGINE
                             |
       ┌─────────────────────┼─────────────────────┐
       |                     |                     |
   LINEAGE CHECK        TRUST ENGINE         CONFLICT CHECK
       |                     |                     |
       └─────────────────────┼─────────────────────┘
                             |
                   MODELLEDGER REGISTRY
                             |
                        BLOCKCHAIN
                             |
              ┌──────────────┼──────────────┐
              |              |              |
           AUDIT         VERIFICATION     REVOCATION
              |              |              |
              └──────────────┼──────────────┘
                             |
                     JUDGE / VERIFIER

                     + OPTIONAL LAYER
                             |
                    Proof of Creator
                  Face + Liveness + Wallet
```

---

## Final project positioning

> **ModelLedger is a blockchain-backed AI provenance platform that lets anyone inspect and verify the claimed origin, transformation history, and supporting evidence of AI-generated content — including content that has passed through multiple models and applications — while keeping sensitive generation data private.**

The strongest version of the hackathon project is therefore:

**Provenance Graph + Cryptographic Evidence + Blockchain Registry + Trust Classification + Adversarial Verification**, with **Proof of Creator** as the standout optional feature.
