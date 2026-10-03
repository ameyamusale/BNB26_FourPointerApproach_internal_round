import os

os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"

from paddleocr import PaddleOCR

print("Creating OCR model...")

ocr = PaddleOCR(
    lang="en",
    device="cpu",
    enable_mkldnn=False
)

print("OCR model created!")

result = ocr.predict("uploads/pages/page_1.png")

print("OCR completed!")
print(result)