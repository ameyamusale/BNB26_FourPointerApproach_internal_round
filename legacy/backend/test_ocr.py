from app.services.ocr_service import extract_text

image_path = "uploads/pages/page_1.png"

result = extract_text(image_path)

print(result)