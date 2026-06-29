from typing import Annotated, Optional
from operator import add
from typing_extensions import TypedDict


class CodeItem(TypedDict):
    file_name: str
    code: str


class AnalysisResult(TypedDict):
    file_name: str
    severity: str
    function_count: int


class JudgeScore(TypedDict):
    file_name: str
    score: float
    reasoning: str


class FileTask(TypedDict):
    file: str
    priority: int
    focus_areas: list[str]


class RepoContext(TypedDict):
    dependencies: dict[str, list[str]]
    patterns: list[str]
    architecture: list[str]


class SuggestedCode(TypedDict):
    suggestion_id: int
    file_name: str
    suggested_code: str


class SecurityFinding(TypedDict):
    category: str
    severity: str
    line: int
    description: str


class TestCode(TypedDict):
    file_name: str
    test_code: str


class BrokenScenario(TypedDict):
    file_name: str
    scenario: str


class FinalReview(TypedDict):
    file_name: str
    revised_code: str
    review_notes: str


class PRComment(TypedDict):
    file_name: str
    line: int
    body: str


class PRResult(TypedDict):
    patch_status: str
    pr_description: str
    comments: list[PRComment]


class PRReviewState(TypedDict):
    pr_id: int
    pr_url: str
    thread_id: Optional[str]
    analyzed_codes: Optional[list[CodeItem]]
    analysis_results: Optional[list[AnalysisResult]]
    judge_scores: Optional[list[JudgeScore]]
    judge_status: Optional[str]
    human_approved: Optional[bool]
    pr_review_steps: Annotated[list[str], add]

    supervisor_plan: Optional[list[FileTask]]
    repo_context: Optional[RepoContext]
    implementation_result: Optional[list[SuggestedCode]]
    test_code: Optional[list[TestCode]]
    broken_scenarios: Optional[list[BrokenScenario]]
    security_findings: Optional[list[SecurityFinding]]
    final_review: Optional[list[FinalReview]]
    pr_result: Optional[PRResult]