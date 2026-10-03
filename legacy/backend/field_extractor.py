import re


GRADES = {
    "O", "A+", "A", "B+", "B", "C+", "C", "D", "F"
}

def clean_subject_name(name):
    if not name:
        return None

    name = name.strip()

    # Common OCR spacing fixes
    replacements = {
        "DIGITALELECTRONICS": "DIGITAL ELECTRONICS",
        "DISCRETEMATHEMATICS": "DISCRETE MATHEMATICS",
        "COMMUNICATIONSKILLS": "COMMUNICATION SKILLS",
        "CLOUDCOMPUTING": "CLOUD COMPUTING",
        "ENGINEERINGMATHEMATICS": "ENGINEERING MATHEMATICS",
    }

    if name.upper() in replacements:
        return replacements[name.upper()]

    # Remove obvious OCR garbage
    if len(name) <= 3 and not name.isalpha():
        return None

    return name




def clean_text(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def extract_fields(rec_texts):

    texts = [clean_text(t) for t in rec_texts if clean_text(t)]

    data = {
        "name": None,
        "roll_number": None,
        "semester": None,
        "subjects": [],
        "total_marks": None,
        "cgpa": None
    }

    # ==================================================
    # NAME
    # ==================================================

    for i, text in enumerate(texts):

        match = re.search(
            r"\bNAME\b\s*[:\-]?\s*(.+)",
            text,
            re.IGNORECASE
        )

        if match:
            name = match.group(1)

            # Remove accidentally captured fields
            name = re.split(
                r"\b(?:PRN|ROLL|ENROLLMENT|PROGRAM|BRANCH)\b",
                name,
                flags=re.IGNORECASE
            )[0]

            data["name"] = name.strip()

            if data["name"]:
                break

        if text.upper() == "NAME" and i + 1 < len(texts):
            data["name"] = texts[i + 1]
            break

    # ==================================================
    # ROLL NUMBER / PRN
    # ==================================================

    for i, text in enumerate(texts):

        match = re.search(
            r"\b(?:PRN|ROLL\s*NO|ROLL\s*NUMBER|ENROLLMENT\s*NO)"
            r"\s*[:\-]?\s*([A-Za-z0-9]+)",
            text,
            re.IGNORECASE
        )

        if match:
            data["roll_number"] = match.group(1)
            break

        if text.upper() in {
            "PRN",
            "ROLL NO",
            "ROLL NUMBER",
            "ENROLLMENT NO"
        }:

            if i + 1 < len(texts):
                candidate = texts[i + 1]

                if re.fullmatch(r"[A-Za-z0-9]+", candidate):
                    data["roll_number"] = candidate
                    break

    # ==================================================
    # SEMESTER
    # ==================================================

    for i, text in enumerate(texts):

        match = re.search(
            r"\bSEMESTER\b\s*[:\-]?\s*(\d+)",
            text,
            re.IGNORECASE
        )

        if match:
            data["semester"] = int(match.group(1))
            break

        if text.upper() in {"SEMESTER", "SEM"}:

            if i + 1 < len(texts):

                number = re.search(
                    r"\d+",
                    texts[i + 1]
                )

                if number:
                    data["semester"] = int(number.group())
                    break

    # ==================================================
    # CGPA
    # ==================================================

    for i, text in enumerate(texts):

        # CGPA 7.81
        match = re.search(
            r"\bCGPA\b.*?(\d+\.\d+)",
            text,
            re.IGNORECASE
        )

        if match:
            value = float(match.group(1))

            if 0 <= value <= 10:
                data["cgpa"] = value
                break

        # CGPA is a separate OCR token
        if text.upper() == "CGPA":

            # Look at next few tokens
            for next_text in texts[i + 1:i + 5]:

                match = re.search(
                    r"\b(\d+\.\d+)\b",
                    next_text
                )

                if match:
                    value = float(match.group(1))

                    if 0 <= value <= 10:
                        data["cgpa"] = value
                        break

            if data["cgpa"] is not None:
                break

    # ==================================================
    # SUBJECT EXTRACTION
    # ==================================================

    i = 0

    while i < len(texts):

        text = texts[i]

        # Subject code
        code_match = re.fullmatch(
            r"[A-Z]{2,}[0-9]{3,}",
            text,
            re.IGNORECASE
        )

        if not code_match:
            i += 1
            continue

        code = text.upper()

        subject_name = None
        credits = None
        grade = None
        marks = None

        # Look at next few OCR tokens
        window = texts[i + 1:i + 6]

        # ----------------------------------------------
        # Find grade
        # ----------------------------------------------

        grade_index = None

        for j, token in enumerate(window):

            if token.upper() in GRADES:
                grade = token.upper()
                grade_index = j
                break

        # ----------------------------------------------
        # Find credits
        # ----------------------------------------------

        for j, token in enumerate(window):

            if re.fullmatch(r"\d{1,2}", token):

                number = int(token)

                # Credits are usually 1-10
                if 1 <= number <= 10:
                    credits = number

                    # Prefer number before grade
                    if grade_index is None or j < grade_index:
                        break

        # ----------------------------------------------
        # Subject name
        # ----------------------------------------------

        name_parts = []

        for token in window:

            if token.upper() in GRADES:
                break

            if re.fullmatch(r"\d{1,2}", token):
                continue

            # Don't accidentally consume another subject
            if re.fullmatch(
                r"[A-Z]{2,}[0-9]{3,}",
                token,
                re.IGNORECASE
            ):
                break

            name_parts.append(token)

        if name_parts:
            subject_name = clean_subject_name(" ".join(name_parts))

        # ----------------------------------------------
        # Add subject if we found at least the code
        # ----------------------------------------------

        data["subjects"].append({
            "code": code,
            "name": subject_name,
            "marks": marks,
            "grade": grade,
            "credits": credits
        })

        i += 1

    # ==================================================
    # TOTAL MARKS
    # ==================================================

    # Only calculate if actual marks exist.
    actual_marks = [
        s["marks"]
        for s in data["subjects"]
        if s["marks"] is not None
    ]

    if actual_marks:
        data["total_marks"] = sum(actual_marks)

    return data