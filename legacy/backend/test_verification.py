from app.services.verification.schemas import (
    MarksheetData,
    Subject
)

from app.services.verification.engine import verify_document


trusted_data = MarksheetData(
    name="Rahul Sharma",
    roll_number="CS21B1045",
    semester=5,
    subjects=[
        Subject(
            code="CS501",
            name="Database Management Systems",
            marks=85,
            grade="A",
            credits=4
        ),
        Subject(
            code="CS502",
            name="Operating Systems",
            marks=78,
            grade="B+",
            credits=4
        ),
        Subject(
            code="CS503",
            name="Computer Networks",
            marks=91,
            grade="A+",
            credits=4
        )
    ],
    total_marks=254,
    cgpa=8.4
)


extracted_data = MarksheetData(
    name="Rahul Sharma",
    roll_number="CS21B1045",
    semester=5,
    subjects=[
        Subject(
            code="CS501",
            name="Database Management Systems",
            marks=95,
            grade="A",
            credits=4
        ),
        Subject(
            code="CS502",
            name="Operating Systems",
            marks=78,
            grade="B+",
            credits=4
        ),
        Subject(
            code="CS503",
            name="Computer Networks",
            marks=91,
            grade="A+",
            credits=4
        )
    ],
    total_marks=254,
    cgpa=8.4
)


result = verify_document(
    extracted_data,
    trusted_data
)

print(result.model_dump_json(indent=2))