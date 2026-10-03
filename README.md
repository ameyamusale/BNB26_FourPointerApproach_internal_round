# ModelLedger

**AI Content Provenance & Multi-Model Verification Infrastructure**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Solidity](https://img.shields.io/badge/Solidity-0.8.20-363636.svg)](https://soliditylang.org/)
[![Hardhat](https://img.shields.io/badge/Hardhat-2.22-yellow.svg)](https://hardhat.org/)
[![Database](https://img.shields.io/badge/Database-SQLite%203%20(WAL)-lightgrey.svg)](https://www.sqlite.org/)
[![Security Audit](https://img.shields.io/badge/Security%20Audit-Verified-green.svg)](docs/SECURITY_AUDIT.md)

---

## Overview

**ModelLedger** is an open, auditable provenance network and verification engine designed to prove the origin, transformation history, and human authorization of AI-generated content across models and applications.

In modern generative workflows, digital media rarely originates from a single standalone model. A single image may be synthesized by an image generator (e.g., Model A), upscaled by an enhancement model (e.g., Model B), cropped and color-graded in an editing tool (e.g., Application C), and compressed for web delivery. Existing attribution methods either collapse the answer into a binary "real vs. fake" classification or rely on watermarks that degrade upon re-encoding.

ModelLedger solves this by recording fine-grained cryptographic provenance events:
- **Never collapses to binary "real/fake":** The system returns calibrated evidence states—`TRUSTED`, `SELF_ASSERTED`, `UNVERIFIABLE`, or `CONFLICT`.
- **Zero prompt leakage:** Content creators verify that their generation prompts produced an artifact via SHA-256 commitments without disclosing private prompts or files.
- **Off-chain biometric authorization:** Human creators authenticate ownership via facial liveness without placing raw biometric data on-chain.
- **Dual-hash integrity:** Exact SHA-256 binary hashing is paired with 64-bit Discrete Cosine Transform (DCT) perceptual hashing (`pHash`) to maintain traceability across compression and re-encoding.
- **Offline-resilient consensus:** Operates fully offline with cryptographically chained audit logs, and commits state to EVM smart contracts when connected.

---

## Problem Statement

Generative AI content systems face three foundational trust failures:

1. **Model Attribution & Lineage Blindness:** Consumers and evaluators cannot determine which model weights generated an artifact once it has passed through post-processing tools.
2. **Watermark Fragility & False Classifiers:** Statistical deepfake detectors suffer from high false-positive rates on compressed media, while pixel watermarks are easily stripped by cropping, downsampling, or format conversion.
3. **Identity Impersonation & Prompt Exposure:** Anyone can claim authorship of an AI generation, while proving legitimate creation often requires exposing sensitive proprietary prompt engineering.

---

## Solution Flow

ModelLedger addresses these challenges through a verifiable cryptographic pipeline:

```text
Creator (Biometric Liveness)
   │
   ▼
Model (Weight Hash & Metadata Commitment)
   │
   ▼
Artifact (Exact SHA-256 & Perceptual pHash)
   │
   ▼
Transformations (Parent-to-Child Provenance Events)
   │
   ▼
Cryptographic Evidence (ECDSA Signatures & SHA-256 Commitments)
   │
   ▼
Verification Engine (7-Point Evidence Checklist)
   │
   ▼
Audit Ledger (Tamper-Evident Hash Chain) & Optional Blockchain Anchor
```

---

## Key Features

- **Proof of Creator:** In-browser camera capture with 4-stage anti-spoof liveness detection (Laplacian blur variance, FFT moiré screening, aspect ratio, and eye-pair confirmation). Issues HMAC-SHA256 session tokens to bind human identity to model registrations.
- **Model Registry:** Immutable registration of AI generators with model architecture, weights SHA-256 fingerprint, and creator identity binding.
- **Artifact Registry & Transformation Tracking:** Captures parent-child relationships across transformation actions (`GENERATED`, `UPSCALED`, `RE_ENCODED`, `CROPPED`, `COMPRESSED`).
- **Cryptographic Signatures (SECP256k1):** Canonical JSON serialization signed with ECDSA keys, matching Ethereum standard curves.
- **Privacy-Preserving Zero-Prompt Verification:** Cryptographic SHA-256 prompt commitment allows creators to prove generation intent without publishing proprietary prompt text.
- **7-Point Verification Engine:** Reconstructs the entire directed acyclic graph (DAG) to determine whether artifacts originate from an active model and unbroken lineage.
- **Adversarial Security Lab:** Built-in interactive test suite executing 7 real-time simulated attack vectors with live cryptographic verification of failure states.
- **Tamper-Evident Audit Hash Chain:** Append-only ledger where each event is cryptographically linked (`log_hash = SHA256(prev_hash + data)`). Provides 1-click verification from the genesis block.
- **Dual-Mode Blockchain Layer:** Full EVM smart contract (`ModelLedgerRegistry.sol`) ready for Hardhat or public testnets, with graceful offline demonstration fallback.

---

## System Architecture

![ModelLedger System Architecture](docs/architecture.png)

The application is structured into four cohesive tiers:

1. **Presentation Layer:** Vanilla JavaScript and CSS design system served directly by FastAPI. Zero build step, zero client bloat, and full native DOM performance.
2. **Application & API Layer:** FastAPI framework routing requests, managing multipart uploads, and providing OpenAPI/Swagger documentation.
3. **Logic & Security Engines:** Modular Python services executing computer vision heuristics, cryptographic math, lineage tree traversal, and threat simulation.
4. **Persistence & Consensus:** SQLite 3 in WAL mode with strict foreign key constraints, coupled with an EVM smart contract registry on Ethereum/Hardhat.

---

## Core Modules

### 1. Proof of Creator
Located in `backend/services/creator_auth.py` and `backend/api/creator.py`.
- Evaluates human presence using OpenCV Haar Cascades and Fast Fourier Transform (FFT) analysis.
- Computes a normalized 128-byte facial vector and hashes it to a 32-byte SHA-256 commitment (`0x...`).
- **Privacy Guarantee:** Raw facial images and feature vectors are discarded immediately after memory processing. Only the commitment hash is stored. Zero biometric data is placed on-chain.

### 2. Model Registry
Located in `backend/services/model_registry.py` and `backend/api/models.py`.
- Stores model metadata, creator identifiers, and model weight fingerprints.
- Links models directly to verified creator profiles via cryptographic authorization tokens.
- Supports model lifecycle revocation.

### 3. Artifact Registry & Fingerprinting
Located in `backend/services/artifact_registry.py` and `backend/services/fingerprint.py`.
- Computes binary SHA-256 hash for byte-level tamper detection.
- Computes 64-bit DCT perceptual hash (`pHash`) to identify transformations that preserve visual structure (e.g., resizing, minor color adjustments).

### 4. Provenance Engine & Lineage DAG
Located in `backend/services/provenance.py` and `backend/services/graph.py`.
- Records atomic provenance events connecting parent artifacts to child artifacts.
- Reconstructs end-to-end directed acyclic graphs (DAGs), validating that every step connects back to an active root model.

### 5. Verification & Trust Engine
Located in `backend/services/verification.py` and `backend/services/trust_engine.py`.
- Evaluates candidate files against 7 verification criteria.
- Assigns one of four mutually exclusive trust statuses:
  - `TRUSTED`: Exact hash match, valid ECDSA signature, unbroken lineage, and verified on-chain commitment.
  - `SELF_ASSERTED`: Exact or perceptual hash match with recorded provenance, but without complete cryptographic signatures or on-chain confirmation.
  - `UNVERIFIABLE`: Artifact hash is not found in the registry or parent references are missing.
  - `CONFLICT`: Competing claims, forged signatures, or a revoked upstream model detected.

### 6. Adversarial Testing Lab
Located in `backend/services/adversarial.py` and `backend/api/adversarial.py`.
- Provides an automated testbed for 7 live attack scenarios:
  1. *Artifact Tampering* (single byte alteration results in `UNVERIFIABLE`).
  2. *Forged Provenance Claim* (invalid signature results in `CONFLICT`).
  3. *Removed Provenance Step* (broken lineage results in `CONFLICT`).
  4. *Conflicting Origin Claims* (competing models claim same artifact).
  5. *Revoked Model Usage* (flagged as `SELF_ASSERTED` with lifecycle warning).
  6. *Biometric Spoofing* (simulated 2D photograph rejected by liveness filters).
  7. *Unauthorized Blockchain Mutation* (reverted on smart contract level).

### 7. Tamper-Evident Audit Ledger
Located in `backend/services/store.py` and `backend/api/audit.py`.
- Formulates a SHA-256 cryptographic blockchain-style hash chain over administrative events:
  $$\text{log\_hash}_i = \text{SHA-256}(\text{prev\_hash}_{i-1} \parallel \text{log\_id}_i \parallel \text{action}_i \parallel \text{resource\_id}_i \parallel \text{details}_i)$$
- Verifiable via `GET /api/audit/verify-chain`.

### 8. Blockchain Consensus Layer
Located in `blockchain/contracts/ModelLedgerRegistry.sol` and `backend/services/blockchain.py`.
- Implemented as an EVM smart contract tracking model registrations, artifact commitments, and provenance links.
- **Current Operational Status:** Configured for offline/local demonstration. When `MODELLEDGER_RPC_URL` is omitted, the system explicitly reports status `offline` and marks blockchain checks as `not checked` rather than falsely asserting security.

---

## Visual Walkthrough & Screenshots

All screenshots below represent the verified, working application interfaces captured directly from the running local instance.

### 1. Dashboard (`/dashboard`)
Displays high-level registry metrics, verified creator counts, recent activity, and the full interactive provenance DAG.
![Dashboard](docs/screenshots/01-dashboard.png)

### 2. Proof of Creator (`/proof-of-creator`)
In-browser capture studio with webcam feed, 5-stage anti-spoof liveness check, HMAC token generation, and the enrolled creator directory.
![Proof of Creator](docs/screenshots/02-proof-of-creator.png)

### 3. Model Registry (`/models`)
Model registration interface with weights SHA-256 input, 1-click biometric token autofill, and the active model directory.
![Model Registry](docs/screenshots/03-model-registry.png)

### 4. Artifact Registry (`/artifacts`)
Registers newly generated artifacts or transformation steps (`UPSCALED`, `RE_ENCODED`, `CROPPED`) with in-memory hashing and perceptual fingerprinting.
![Artifact Registry](docs/screenshots/04-artifact-registry.png)

### 5. Verification Portal (`/verify`)
Drag-and-drop artifact verifier displaying the 7-point evidence checklist, trust state badge, and zero-prompt commitment test.
![Verification Portal](docs/screenshots/05-verify.png)

### 6. Lineage Graph (`/lineage/{id}`)
Deep provenance inspector demonstrating root reachability, transformation depth, and parent-child event edges.
![Lineage Graph](docs/screenshots/06-lineage.png)

### 7. Adversarial Lab (`/adversarial-lab`)
Security evaluation suite running 7 live attack vectors with expected vs. actual evidence reports.
![Adversarial Lab](docs/screenshots/07-adversarial-lab.png)

### 8. Tamper-Evident Audit Log (`/audit`)
Cryptographically chained event ledger with 1-click SHA-256 hash chain verification.
![Audit Log](docs/screenshots/08-audit-log.png)

---

## Technology Stack

| Layer | Component | Description |
|---|---|---|
| **Frontend** | HTML5, Vanilla JavaScript, CSS3 | Custom responsive dark glassmorphism design system; no build step required. |
| **Backend** | Python 3.10+, FastAPI, Uvicorn | High-performance asynchronous API framework with automated OpenAPI docs. |
| **Database** | SQLite 3 (WAL Mode) | Persistent, thread-safe relational store with foreign-key referential integrity. |
| **Computer Vision** | OpenCV (`cv2`), Pillow (`PIL`), NumPy | Haar cascades for face/eye detection; FFT spectrum analysis for anti-spoofing. |
| **Cryptography** | `cryptography` (hazmat), `hashlib`, `hmac` | SHA-256 exact hashing, SECP256k1 ECDSA signatures, HMAC session authorization. |
| **Blockchain** | Solidity 0.8.20, Hardhat, Web3.py | Smart contract registry deployed locally or on Ethereum testnets; offline fallback. |
| **Testing** | `pytest`, Hardhat Test (Mocha/Chai) | Comprehensive backend unit and integration tests; EVM smart contract test suite. |

---

## Repository Structure

```text
ModelLedger/
├── backend/
│   ├── api/                    # REST API routers (creator, models, artifacts, verify, etc.)
│   ├── models/                 # Pydantic data schemas and enums
│   ├── services/               # Core engines (verification, creator_auth, blockchain, store)
│   ├── tests/                  # Pytest test suite (unit, integration, adversarial, e2e)
│   ├── config.py               # Central environment configuration
│   ├── main.py                 # FastAPI application composition and route registration
│   └── requirements.txt        # Backend dependencies
├── blockchain/
│   ├── contracts/              # Solidity contracts (ModelLedgerRegistry.sol)
│   ├── scripts/                # Hardhat deployment scripts
│   ├── test/                   # Mocha/Chai contract unit tests
│   ├── hardhat.config.js       # Hardhat network configuration
│   └── package.json            # Node dependencies
├── data/
│   └── modelledger.db          # Persistent SQLite database file
├── docs/
│   ├── screenshots/            # Verified application interface captures
│   ├── architecture.png        # System architecture diagram
│   ├── API.md                  # Detailed REST API documentation
│   └── SECURITY_AUDIT.md       # Comprehensive security audit report
├── frontend/
│   ├── common.js               # Shared DOM helpers, navigation, and API utilities
│   ├── graph-ui.js             # SVG flow graphs and lineage renderers
│   ├── styles.css              # Unified design system
│   ├── dashboard.html          # Dashboard interface
│   ├── creator.html            # Proof of Creator studio
│   ├── models.html             # Model registry interface
│   ├── model.html              # Model passport detail view
│   ├── artifacts.html          # Artifact registry interface
│   ├── artifact.html           # Artifact passport detail view
│   ├── verify.html             # Verification portal
│   ├── lineage.html            # Lineage DAG visualization
│   ├── adversarial.html        # Adversarial lab testbed
│   └── audit.html              # Audit log and hash chain viewer
├── .env.example                # Environment variables template
└── README.md                   # Project documentation
```

---

## Getting Started

### Prerequisites
- **Python:** 3.10 or higher
- **Node.js:** 18 or higher (optional, for local blockchain compilation)

### 1. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment (optional)
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the application
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open your browser to:
- **Web Application:** `http://127.0.0.1:8000/dashboard`
- **Interactive API Documentation:** `http://127.0.0.1:8000/docs`

### 2. Running Automated Tests

#### Backend Test Suite (Pytest)
```bash
cd backend
python -m pytest -v
```
*Current verified status: 75 unit/integration tests passing in offline demonstration mode.*

#### Blockchain Smart Contract Tests (Hardhat)
```bash
cd blockchain
npm install
npm test
```
*Current verified status: 16 smart contract test cases passing (5s).*

### 3. Optional: Enabling On-Chain Blockchain Mode

To run a live local blockchain node and commit transactions on-chain:

```bash
# Terminal 1: Start local Hardhat node
cd blockchain
npx hardhat node

# Terminal 2: Deploy ModelLedgerRegistry contract
cd blockchain
npx hardhat run scripts/deploy.js --network localhost
```

Copy the deployed contract address and set the corresponding environment variables in `.env`:
```text
MODELLEDGER_RPC_URL=http://127.0.0.1:8545
MODELLEDGER_CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
MODELLEDGER_TX_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
```
Restart the backend to automatically transition from offline mode to live on-chain synchronization.

---

## Verification Trust Matrix

ModelLedger never gives false binary certainties. Trust decisions are evaluated according to the following mathematical rules:

| Trust State | Conditions Required | Meaning |
|---|---|---|
| `TRUSTED` | Exact SHA-256 match + valid SECP256k1 signature + verified on-chain commitment + root model active. | Cryptographically verified origin with tamper-evident blockchain consensus. |
| `SELF_ASSERTED` | Registered provenance and hash match, but signatures unconfigured or blockchain running in offline mode. | Claim is recorded in local registry; origin asserted without cryptographic consensus. |
| `UNVERIFIABLE` | Artifact hash not found in registry, or parent references cannot be located. | No matching provenance record exists in the system. |
| `CONFLICT` | Signature invalid, competing origin claims detected, broken lineage step, or upstream model revoked. | Evidence contradicts recorded claim; potential tampering or impersonation. |

---

## Security & Privacy Highlights

- **Zero Raw Biometrics On-Chain:** Face embeddings are hashed to 32-byte commitments off-chain; raw photos and vectors are never stored in the database or written to blockchain storage.
- **Zero Prompt Leakage:** Prompt commitments use standard SHA-256 hashing ($H(\text{prompt})$). Verification is performed strictly off-chain by evaluating $H(\text{candidate}) \stackrel{?}{=} \text{commitment}$.
- **Complete Audit Review:** For a detailed threat analysis, vulnerability mitigations, and implementation boundary reviews, inspect [**docs/SECURITY_AUDIT.md**](docs/SECURITY_AUDIT.md).
- **REST API Reference:** Complete endpoint schemas and curl examples are documented in [**docs/API.md**](docs/API.md).
