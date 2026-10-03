from fastapi import APIRouter
from pydantic import BaseModel
 
from app.services.blockchain_service import register_document, verify_document, get_document
from app.services.qr_service import generate_qr
 
router = APIRouter(prefix="/blockchain", tags=["blockchain"])
 
 
class DocPayload(BaseModel):
    document_id: str
    document_hash: str
 
 
@router.post("/register")
def register(payload: DocPayload):
    """
    Register a document's hash on-chain and generate its verification QR code.
    """
    result = register_document(payload.document_id, payload.document_hash)
    if result.get("success"):
        qr_path = generate_qr(payload.document_id)
        result["qr_code_path"] = qr_path
    return result
 
 
@router.post("/verify")
def verify(payload: DocPayload):
    """
    Compare an uploaded document's hash against what's stored on-chain.
    """
    return verify_document(payload.document_id, payload.document_hash)
 
 
@router.get("/document/{document_id}")
def get_doc(document_id: str):
    """
    Look up the stored hash/issuer/timestamp for a document_id.
    """
    return get_document(document_id)