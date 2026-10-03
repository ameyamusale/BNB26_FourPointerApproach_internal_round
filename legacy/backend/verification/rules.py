def check_name(extracted, trusted):
    if not extracted or not trusted:
        return False, "Name is missing."

    passed = extracted.strip().lower() == trusted.strip().lower()

    if passed:
        return True, "Name matches trusted record."

    return False, (
        f"Name mismatch: document='{extracted}', "
        f"trusted='{trusted}'."
    )


def check_roll_number(extracted, trusted):
    if not extracted or not trusted:
        return False, "Roll number is missing."

    passed = extracted.strip().upper() == trusted.strip().upper()

    if passed:
        return True, "Roll number matches trusted record."

    return False, (
        f"Roll number mismatch: document='{extracted}', "
        f"trusted='{trusted}'."
    )


def check_semester(extracted, trusted):
    if extracted is None or trusted is None:
        return False, "Semester is missing."

    passed = extracted == trusted

    if passed:
        return True, "Semester matches trusted record."

    return False, (
        f"Semester mismatch: document={extracted}, "
        f"trusted={trusted}."
    )


def check_subjects(extracted_subjects, trusted_subjects):
    extracted_codes = {
        subject.code.upper()
        for subject in extracted_subjects
    }

    trusted_codes = {
        subject.code.upper()
        for subject in trusted_subjects
    }

    if extracted_codes == trusted_codes:
        return True, "Subject list matches trusted record."

    missing = trusted_codes - extracted_codes
    extra = extracted_codes - trusted_codes

    messages = []

    if missing:
        messages.append(
            f"Missing subjects: {', '.join(sorted(missing))}"
        )

    if extra:
        messages.append(
            f"Unexpected subjects: {', '.join(sorted(extra))}"
        )

    return False, "; ".join(messages)


def check_marks(extracted_subjects, trusted_subjects):
    trusted_marks = {
        subject.code.upper(): subject.marks
        for subject in trusted_subjects
    }

    mismatches = []

    for subject in extracted_subjects:

        code = subject.code.upper()

        if code not in trusted_marks:
            continue

        extracted_marks = subject.marks
        trusted_mark = trusted_marks[code]

        if extracted_marks is None:
            mismatches.append(
                f"{code}: marks could not be extracted"
            )
            continue

        if trusted_mark is None:
            continue

        if extracted_marks != trusted_mark:
            mismatches.append(
                f"{code}: document={extracted_marks}, "
                f"trusted={trusted_mark}"
            )

    if not mismatches:
        return True, "All subject marks match trusted records."

    return False, "Mark mismatches: " + "; ".join(mismatches)


def check_total(extracted_subjects, claimed_total):
    if claimed_total is None:
        return False, "Total marks are missing."

    marks = [
        subject.marks
        for subject in extracted_subjects
        if subject.marks is not None
    ]

    if not marks:
        return False, "Subject marks are unavailable."

    calculated_total = sum(marks)

    passed = calculated_total == claimed_total

    if passed:
        return True, f"Total marks are correct: {claimed_total}."

    return False, (
        f"Total marks mismatch: calculated={calculated_total}, "
        f"document={claimed_total}."
    )


def check_cgpa(extracted, trusted):
    if extracted is None:
        return False, "CGPA is missing."

    if trusted is None:
        return False, "Trusted CGPA is unavailable."

    passed = abs(extracted - trusted) < 0.01

    if passed:
        return True, f"CGPA matches trusted record: {extracted}."

    return False, (
        f"CGPA mismatch: document={extracted}, "
        f"trusted={trusted}."
    )