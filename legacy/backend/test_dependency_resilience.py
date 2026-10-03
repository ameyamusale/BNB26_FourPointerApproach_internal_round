import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_optional_dependency_modules_import_cleanly():
    import app.services.blockchain_service as blockchain_service
    import app.services.ocr_service as ocr_service

    assert callable(blockchain_service.register_document)
    assert callable(blockchain_service.verify_document)
    assert callable(ocr_service.extract_text)
