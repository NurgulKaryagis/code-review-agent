from typing import List
from pydantic import BaseModel, field_validator


class AnalysisResultSchema(BaseModel):
    file_name: str
    issues: List[str]
    severity: str
    function_count: int

    @field_validator("severity")
    @classmethod
    def severity_must_be_valid(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "critical"}
        if v.lower() not in allowed:
            raise ValueError(f"severity must be one of {allowed}, got '{v}'")
        return v.lower()


class SuggestedCodeSchema(BaseModel):
    suggestion_id: int
    file_name: str
    suggested_code: str
