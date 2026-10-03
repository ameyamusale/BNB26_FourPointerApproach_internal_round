from .schemas import (
    MarksheetData,
    VerificationResult,
    VerificationCheck
)

from .rules import (
    check_name,
    check_roll_number,
    check_semester,
    check_subjects,
    check_marks,
    check_total,
    check_cgpa
)


def verify_document(
    extracted: MarksheetData,
    trusted: MarksheetData
) -> VerificationResult:

    checks = []

    # -----------------------------------------
    # 1. Name
    # -----------------------------------------

    passed, message = check_name(
        extracted.name,
        trusted.name
    )

    checks.append(
        VerificationCheck(
            name="name_match",
            passed=passed,
            message=message
        )
    )

    # -----------------------------------------
    # 2. Roll number
    # -----------------------------------------

    passed, message = check_roll_number(
        extracted.roll_number,
        trusted.roll_number
    )

    checks.append(
        VerificationCheck(
            name="roll_number_match",
            passed=passed,
            message=message
        )
    )

    # -----------------------------------------
    # 3. Semester
    # -----------------------------------------

    passed, message = check_semester(
        extracted.semester,
        trusted.semester
    )

    checks.append(
        VerificationCheck(
            name="semester_match",
            passed=passed,
            message=message
        )
    )

    # -----------------------------------------
    # 4. Subjects
    # -----------------------------------------

    passed, message = check_subjects(
        extracted.subjects,
        trusted.subjects
    )

    checks.append(
        VerificationCheck(
            name="subjects_match",
            passed=passed,
            message=message
        )
    )

    # -----------------------------------------
    # 5. Marks
    # -----------------------------------------

    passed, message = check_marks(
        extracted.subjects,
        trusted.subjects
    )

    checks.append(
        VerificationCheck(
            name="marks_match",
            passed=passed,
            message=message
        )
    )

    # -----------------------------------------
    # 6. Total
    # -----------------------------------------

    passed, message = check_total(
        extracted.subjects,
        extracted.total_marks
    )

    checks.append(
        VerificationCheck(
            name="total_match",
            passed=passed,
            message=message
        )
    )

    # -----------------------------------------
    # 7. CGPA
    # -----------------------------------------

    passed, message = check_cgpa(
        extracted.cgpa,
        trusted.cgpa
    )

    checks.append(
        VerificationCheck(
            name="cgpa_match",
            passed=passed,
            message=message
        )
    )

    # -----------------------------------------
    # Calculate score
    # -----------------------------------------

    passed_count = sum(
        1 for check in checks
        if check.passed
    )

    total_checks = len(checks)

    score = (passed_count / total_checks) * 100

    # -----------------------------------------
    # Determine status
    # -----------------------------------------

    if all(check.passed for check in checks):
        status = "VERIFIED"

    elif any(
        check.name == "roll_number_match"
        and not check.passed
        for check in checks
    ):
        status = "FAILED"

    else:
        status = "SUSPICIOUS"

    return VerificationResult(
        status=status,
        score=round(score, 2),
        checks=checks
    )