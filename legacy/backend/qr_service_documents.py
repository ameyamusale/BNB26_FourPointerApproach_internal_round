import os
import qrcode
 
# backend/app/services/ -> up two levels -> backend/generated_qr
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "generated_qr")
BASE_VERIFY_URL = "https://veritrust.ai/verify"
 
 
def generate_qr(document_id: str, base_url: str = BASE_VERIFY_URL) -> str:
    """
    Generate a QR code pointing to the verification URL for a document.
    The QR never contains the PDF itself, only a link/ID to look it up.
 
    Returns the file path of the saved PNG.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
 
    url = f"{base_url}/{document_id}"
    img = qrcode.make(url)
 
    file_path = os.path.join(OUTPUT_DIR, f"{document_id}.png")
    img.save(file_path)
 
    return file_path
 
 
if __name__ == "__main__":
    path = generate_qr("VT-2026-0001")
    print(f"QR saved to: {path}")
 