from pathlib import Path

from fastapi.testclient import TestClient

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app


client = TestClient(app)


def test_upload_and_verify_document_extracts_real_fields():
    text = b"""NAME: Rahul Sharma
ENROLLMENT: ABC2024001
UNIVERSITY: ABC University
SEMESTER: VI
CGPA: 8.7
"""

    response = client.post(
        "/api/upload",
        files={"file": ("marksheet.txt", text, "text/plain")},
    )

    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["status"] == "VERIFIED" or payload["status"] == "SUSPICIOUS"
    assert payload["document"]["name"] == "Rahul Sharma"
    assert payload["document"]["roll_number"] == "ABC2024001"
    assert payload["document"]["university"] == "ABC University"
    assert payload["document"]["semester"] == "VI"
    assert payload["document"]["cgpa"] == 8.7
    assert payload["document"]["hash"]


def test_extracts_vishwakarma_institute_of_technology_name():
    from main import extract_document_details

    text = """Student Name: Maslekar Dhruv Tushar
Enrollment No: 12414546
Vishwakarma Institute of Technology
Semester: 2
CGPA: 0
"""

    data = extract_document_details(text)

    assert data["name"] == "Maslekar Dhruv Tushar"
    assert data["roll_number"] == "12414546"
    assert data["university"] == "Vishwakarma Institute of Technology"
    assert data["semester"] == "2"
    assert data["cgpa"] == 0.0
