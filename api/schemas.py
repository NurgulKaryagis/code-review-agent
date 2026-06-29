from typing import List
from pydantic import BaseModel, field_validator, HttpUrl


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


class FileTaskSchema(BaseModel):
    file: str
    priority: int
    focus_areas: List[str]


class SupervisorPlanSchema(BaseModel):
    tasks: List[FileTaskSchema]


class SecurityFindingSchema(BaseModel):
    category: str
    severity: str
    line: int
    description: str

    @field_validator("category")
    @classmethod
    def category_must_be_valid(cls, v: str) -> str:
        allowed = {"injection", "auth", "secrets"}
        if v.lower() not in allowed:
            raise ValueError(f"category must be one of {allowed}, got '{v}'")
        return v.lower()

    @field_validator("severity")
    @classmethod
    def severity_must_be_valid(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "critical"}
        if v.lower() not in allowed:
            raise ValueError(f"severity must be one of {allowed}, got '{v}'")
        return v.lower()


class FinalReviewSchema(BaseModel):
    file_name: str
    revised_code: str
    review_notes: str


class PRCommentSchema(BaseModel):
    file_name: str
    line: int
    body: str


class PRResultSchema(BaseModel):
    pr_description: str
    comments: List[PRCommentSchema]


class PullRequestPayload(BaseModel):
    number: int
    html_url: HttpUrl


class WebhookPayload(BaseModel):
    action: str
    pull_request: PullRequestPayload