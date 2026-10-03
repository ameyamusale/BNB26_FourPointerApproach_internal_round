import json

from app.services.ocr_service import extract_text
from app.services.field_extractor import extract_fields


result = extract_text("uploads/pages/page_1.png")

rec_texts = result["rec_texts"]

data = extract_fields(rec_texts)

print("\n========== EXTRACTED JSON ==========\n")

print(json.dumps(data, indent=2))