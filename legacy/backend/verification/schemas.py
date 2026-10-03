from typing import List, Optional
from pydantic import BaseModel


class Subject(BaseModel):
    code: str
    name: Optional[str] = None
    marks: Optional[float] = None
    grade: Optional[str] = None
    credits: Optional[float] = None


class MarksheetData(BaseModel):
    name: Optional[str] = None
    roll_number: Optional[str] = None
    semester: Optional[int] = None
    subjects: List[Subject] = []
    total_marks: Optional[float] = None
    cgpa: Optional[float] = None


class VerificationCheck(BaseModel):
    name: str
    passed: bool
    message: str


class VerificationResult(BaseModel):
    status: str
    score: float
    checks: List[VerificationCheck]