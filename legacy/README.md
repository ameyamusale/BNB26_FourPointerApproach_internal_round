# legacy/

The original **VeriTrust AI** marksheet-verification code from the `Dhruv` branch, archived for reference only.
Nothing here is imported by ModelLedger. The full original also lives in git: `git show baseline-dhruv`.

| Path | What it was | Fate in ModelLedger |
|------|-------------|---------------------|
| `backend/main_documents.py` | marksheet upload + regex field extraction + `VERIFIED/SUSPICIOUS/FAILED` | replaced by `backend/main.py` + `api/` + `services/` |
| `backend/verification/` | CGPA / semester rules engine | removed (domain-specific) |
| `backend/field_extractor.py`, `ocr_service.py`, `preprocessing.py` | OCR + field parsing | optional, metadata extraction only if ever needed |
| `backend/hash_service_documents.py` | SHA-256 | generalised into `services/hashing.py` |
| `backend/blockchain_*_documents.py` | document hash registry client/routes | replaced by `services/blockchain.py` (Phase 3 wires it up) |
| `backend/qr_service_documents.py` | QR for a verify URL | reusable for public verification links (stretch) |
| `dataset/` | original / tampered marksheet PDFs | concept reused as adversarial fixtures in Phase 7 |
| `frontend/` | VeriTrust UI | replaced by the ModelLedger console |
