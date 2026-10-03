import os

os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")

try:
    from paddleocr import PaddleOCR
except Exception:
    PaddleOCR = None


ocr = None
if PaddleOCR is not None:
    try:
        ocr = PaddleOCR(
            lang="en",
            device="cpu",
            enable_mkldnn=False
        )
    except Exception:
        ocr = None


def extract_text(image_path: str):
    if ocr is None:
        return {
            "rec_texts": [],
            "rec_scores": [],
            "rec_boxes": [],
            "warning": "OCR engine is unavailable; text extraction was skipped."
        }

    result = ocr.predict(image_path)
    page = result[0]

    return {
        "rec_texts": page.get("rec_texts", []),
        "rec_scores": page.get("rec_scores", []),
        "rec_boxes": page.get("rec_boxes", [])
    }