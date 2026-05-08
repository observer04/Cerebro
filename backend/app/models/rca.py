from pydantic import BaseModel, EmailStr, Field


class RCAIn(BaseModel):
    root_cause: str = Field(..., min_length=20)
    mitigation: str = Field(..., min_length=1)
    prevention: str = Field(..., min_length=1)
    submitted_by: EmailStr
