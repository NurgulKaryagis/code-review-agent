from typing import Annotated, TypedDict, Optional, List
from operator import add

class CodeItem(TypedDict):
    file_name :str
    code: str        

class SuggestedCode(TypedDict):
    suggestion_id: int
    suggested_code:str
    file_name :str
    
class AnalysisResult(TypedDict):
    file_name: str
    severity: str
    function_count: int
    
class JudgeScore(TypedDict):
    file_name: str
    score: float
    reasoning: str
    
class PRReviewState(TypedDict):
    #input
    pr_id: int 
    pr_url: str
    
    analyzed_codes: Optional[List[CodeItem]]
    analysis_results: Optional[List[AnalysisResult]]
    analysis_status: Optional[str]
    
    suggested_codes: Optional[List[SuggestedCode]]
    suggestion_status: Optional[str]
    human_approved: Optional[bool]
    judge_status: Optional[str]
    judge_scores: Optional[List[JudgeScore]]
    patch_status: Optional[str] 
    thread_id: Optional[str]

    pr_review_steps: Annotated[list[str], add]
    
    

