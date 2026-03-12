import logging
import time
from json import JSONDecodeError

from langgraph.types import interrupt
from litellm import completion
from pydantic import ValidationError

from agent.state import PRReviewState
from agent.tools.git_patch import get_pr_files, apply_patch
from agent.tools.ast_parser import analyze_code
from agent.tools.utils import parse_llm_json
from config.prompts import get_analysis_prompts, get_suggestion_prompts
from api.schemas import AnalysisResultSchema, SuggestedCodeSchema
from eval.judge import judge_code_refactory

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_LLM_TIMEOUT = 30


def _call_llm_with_retry(messages: list, schema_cls, parse_fn=parse_llm_json):
    """LLM call with exponential backoff and stricter-prompt retry on parse/schema failure."""
    last_exc = None
    strict = False
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            effective_messages = messages
            if strict:
                effective_messages = [
                    {**messages[0], "content": messages[0]["content"] + "\nIMPORTANT: Respond with valid JSON only, no extra text."},
                    *messages[1:],
                ]
            response = completion(
                model="gpt-4o-mini",
                messages=effective_messages,
                timeout=_LLM_TIMEOUT,
            )
            content = response.choices[0].message.content
            return schema_cls(**parse_fn(content))
        except (JSONDecodeError, ValidationError) as e:
            last_exc = e
            logger.warning(
                "attempt %d/%d: parse/schema error: %s — retrying with stricter prompt",
                attempt, _MAX_RETRIES, e,
            )
            strict = True
        except Exception as e:
            last_exc = e
            if attempt < _MAX_RETRIES:
                wait = 2 ** attempt
                logger.warning(
                    "attempt %d/%d: LLM error: %s — retrying in %ds",
                    attempt, _MAX_RETRIES, e, wait,
                )
                time.sleep(wait)
                strict = True
            else:
                logger.error("LLM call failed after %d attempts: %s", _MAX_RETRIES, e)
    raise RuntimeError(f"LLM call failed after {_MAX_RETRIES} attempts") from last_exc


def analysis_node(state: PRReviewState) -> dict:
    pr_files = get_pr_files(pr_url=state["pr_url"])

    analyzed_codes = []
    analysis_results = []

    for file in pr_files:
        file_name = file["file_name"]
        code_diff = file["code"]

        ast_result = analyze_code(code_diff, file_name)
        prompts = get_analysis_prompts(
            file_name=file_name,
            severity=ast_result["severity"],
            issues=ast_result["issues"],
            function_count=ast_result["function_count"],
            code_diff=code_diff,
        )

        messages = [
            {"role": "system", "content": prompts["system_prompt"]},
            {"role": "user", "content": prompts["user_prompt"]},
        ]
        llm_result = _call_llm_with_retry(messages, AnalysisResultSchema)

        analyzed_codes.append({"file_name": file_name, "code": code_diff})
        analysis_results.append(llm_result.model_dump())

    return {
        "analyzed_codes": analyzed_codes,
        "analysis_results": analysis_results,
        "analysis_status": "analyzed",
        "pr_review_steps": ["Analysis is completed."],
    }


def suggestion_node(state: PRReviewState) -> dict:
    analyzed_codes = state["analyzed_codes"]
    analysis_results = state["analysis_results"]

    suggested_codes = []
    for idx, (file_info, analysis) in enumerate(zip(analyzed_codes, analysis_results)):
        file_name = file_info["file_name"]
        code = file_info["code"]
        issues = analysis.get("issues", [])

        prompts = get_suggestion_prompts(file_name=file_name, code=code, issues=issues)
        messages = [
            {"role": "system", "content": prompts["system_prompt"]},
            {"role": "user", "content": prompts["user_prompt"]},
        ]

        suggestion_id = idx + 1
        result = _call_llm_with_retry(
            messages,
            SuggestedCodeSchema,
            parse_fn=lambda c, _id=suggestion_id: {**parse_llm_json(c), "suggestion_id": _id},
        )
        suggested_codes.append(result.model_dump())

    return {
        "suggested_codes": suggested_codes,
        "suggestion_status": "suggested",
        "pr_review_steps": ["Suggestions completed."],
    }


def judge_node(state: PRReviewState) -> dict:
    suggested_codes = state["suggested_codes"]
    analyzed_codes = state["analyzed_codes"]
    analysis_results = state["analysis_results"]

    scores = []
    judge_status = "passed"
    for suggested, original, analysis in zip(suggested_codes, analyzed_codes, analysis_results):
        score = judge_code_refactory(
            original_code=original["code"],
            suggested_code=suggested["suggested_code"],
            issues=analysis.get("issues", []),
        )
        if score["score"] < 0.5:
            judge_status = "warning"
        scores.append(score)

    return {
        "judge_scores": scores,
        "judge_status": judge_status,
        "pr_review_steps": ["Judged."],
    }


def human_review_node(state: PRReviewState) -> dict:
    suggested_codes = state["suggested_codes"]
    decision = interrupt(f"Do you confirm the changes?: {suggested_codes}")
    return {"human_approved": decision}


def patch_node(state: PRReviewState) -> dict:
    suggested_codes = state["suggested_codes"]
    pr_url = state["pr_url"]

    for suggested in suggested_codes:
        apply_patch(
            pr_url=pr_url,
            file_name=suggested["file_name"],
            suggested_code=suggested["suggested_code"],
        )

    return {
        "patch_status": "patched",
        "pr_review_steps": ["Codes are patched."],
    }
