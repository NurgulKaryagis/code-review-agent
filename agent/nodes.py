import asyncio
import logging

from langgraph.types import interrupt

from agent.state import PRReviewState
from agent.tools.ast_parser import analyze_code
from agent.tools.git_patch import apply_patch, create_pr_comment, get_pr_files
from agent.tools.security import detect_prompt_injection, validate_llm_output
from agent.tools.utils import call_llm_with_retry, parse_llm_json
from api.schemas import (
    FinalReviewSchema,
    PRResultSchema,
    SecurityFindingSchema,
    SuggestedCodeSchema,
    SupervisorPlanSchema,
)
from config.prompts import (
    get_code_analyst_prompts,
    get_implementation_prompts,
    get_pr_agent_prompts,
    get_review_prompts,
    get_security_agent_prompts,
    get_supervisor_prompts,
    get_test_agent_prompts,
)
from eval.judge import judge_code_refactory

logger = logging.getLogger(__name__)


async def supervisor_node(state: PRReviewState) -> dict:
    pr_files = await asyncio.to_thread(get_pr_files, state["pr_url"])
    file_names = [f["file_name"] for f in pr_files]

    prompts = get_supervisor_prompts(file_names=file_names, pr_url=state["pr_url"])
    messages = [
        {"role": "system", "content": prompts["system_prompt"]},
        {"role": "user", "content": prompts["user_prompt"]},
    ]

    def parse_supervisor(content: str) -> list:
        data = SupervisorPlanSchema(**parse_llm_json(content))
        return [t.model_dump() for t in data.tasks]

    supervisor_plan = await call_llm_with_retry(messages, parse_supervisor)

    analyzed_codes = []
    for f in pr_files:
        injections = detect_prompt_injection(f.get("code", ""))
        if injections:
            logger.warning("Skipping %s — injection patterns found: %s", f["file_name"], injections)
            continue
        analyzed_codes.append({"file_name": f["file_name"], "code": f["code"]})

    return {
        "supervisor_plan": supervisor_plan,
        "analyzed_codes": analyzed_codes,
        "pr_review_steps": ["Supervisor: task plan created."],
    }


async def code_analyst_node(state: PRReviewState) -> dict:
    analyzed_codes = state["analyzed_codes"]
    supervisor_plan = state["supervisor_plan"]

    priority_map = {task["file"]: task["priority"] for task in supervisor_plan}
    focus_map = {task["file"]: task["focus_areas"] for task in supervisor_plan}
    sorted_codes = sorted(analyzed_codes, key=lambda x: priority_map.get(x["file_name"], 99))

    analysis_results = []
    all_dependencies: dict[str, list] = {}
    all_patterns: set[str] = set()
    all_architecture: set[str] = set()

    for file_info in sorted_codes:
        file_name = file_info["file_name"]
        code = file_info["code"]
        focus_areas = focus_map.get(file_name, [])

        ast_result = await asyncio.to_thread(analyze_code, code, file_name)

        prompts = get_code_analyst_prompts(
            file_name=file_name,
            code=code,
            ast_result=ast_result,
            focus_areas=focus_areas,
        )
        messages = [
            {"role": "system", "content": prompts["system_prompt"]},
            {"role": "user", "content": prompts["user_prompt"]},
        ]

        result = await call_llm_with_retry(messages, parse_llm_json)

        conflicts = validate_llm_output(ast_result, result)
        if conflicts:
            logger.warning("AST/LLM conflicts in %s: %s — using AST values", file_name, conflicts)
            result["severity"] = ast_result["severity"]
            result["function_count"] = ast_result["function_count"]

        analysis_results.append({
            "file_name": file_name,
            "severity": result.get("severity", ast_result["severity"]),
            "function_count": ast_result["function_count"],
            "issues": result.get("issues", ast_result.get("issues", [])),
        })
        all_dependencies[file_name] = result.get("dependencies", [])
        all_patterns.update(result.get("patterns", []))
        all_architecture.update(result.get("architecture", []))

    repo_context = {
        "dependencies": all_dependencies,
        "patterns": list(all_patterns),
        "architecture": list(all_architecture),
    }

    return {
        "analysis_results": analysis_results,
        "repo_context": repo_context,
        "pr_review_steps": ["Code analyst: AST analysis and repo context extracted."],
    }


async def implementation_node(state: PRReviewState) -> dict:
    analyzed_codes = state["analyzed_codes"]
    analysis_results = state["analysis_results"]
    repo_context = state["repo_context"]

    implementation_result = []
    for idx, (file_info, analysis) in enumerate(zip(analyzed_codes, analysis_results)):
        file_name = file_info["file_name"]
        code = file_info["code"]
        issues = analysis.get("issues", [])

        prompts = get_implementation_prompts(
            file_name=file_name,
            code=code,
            issues=issues,
            repo_context=repo_context,
        )
        messages = [
            {"role": "system", "content": prompts["system_prompt"]},
            {"role": "user", "content": prompts["user_prompt"]},
        ]

        suggestion_id = idx + 1

        def parse_impl(content: str, _id: int = suggestion_id) -> dict:
            data = parse_llm_json(content)
            return SuggestedCodeSchema(**{**data, "suggestion_id": _id}).model_dump()

        result = await call_llm_with_retry(messages, parse_impl)
        implementation_result.append(result)

    return {
        "implementation_result": implementation_result,
        "pr_review_steps": ["Implementation: refactoring suggestions created."],
    }


async def test_agent_node(state: PRReviewState) -> dict:
    analyzed_codes = state["analyzed_codes"]
    implementation_result = state["implementation_result"]

    test_code = []
    broken_scenarios = []

    for file_info, impl in zip(analyzed_codes, implementation_result):
        file_name = file_info["file_name"]

        prompts = get_test_agent_prompts(
            file_name=file_name,
            original_code=file_info["code"],
            suggested_code=impl["suggested_code"],
        )
        messages = [
            {"role": "system", "content": prompts["system_prompt"]},
            {"role": "user", "content": prompts["user_prompt"]},
        ]

        result = await call_llm_with_retry(messages, parse_llm_json)

        test_code.append({"file_name": file_name, "test_code": result.get("test_code", "")})
        broken_scenarios.append({"file_name": file_name, "scenario": result.get("broken_scenario", "")})

    return {
        "test_code": test_code,
        "broken_scenarios": broken_scenarios,
        "pr_review_steps": ["Test agent: unit tests and integration scenarios generated."],
    }


async def security_agent_node(state: PRReviewState) -> dict:
    analyzed_codes = state["analyzed_codes"]

    security_findings = []

    for file_info in analyzed_codes:
        file_name = file_info["file_name"]
        code_diff = file_info["code"]

        prompts = get_security_agent_prompts(file_name=file_name, code_diff=code_diff)
        messages = [
            {"role": "system", "content": prompts["system_prompt"]},
            {"role": "user", "content": prompts["user_prompt"]},
        ]

        def parse_security(content: str) -> list:
            data = parse_llm_json(content)
            return [SecurityFindingSchema(**f).model_dump() for f in data.get("findings", [])]

        findings = await call_llm_with_retry(messages, parse_security)
        security_findings.extend(findings)

    return {
        "security_findings": security_findings,
        "pr_review_steps": ["Security agent: injection, auth, and secrets scan completed."],
    }


async def review_node(state: PRReviewState) -> dict:
    analyzed_codes = state["analyzed_codes"]
    implementation_result = state["implementation_result"]
    test_code = state["test_code"]
    broken_scenarios = state["broken_scenarios"]
    security_findings = state["security_findings"]

    final_review = []

    for file_info, impl, tests, broken in zip(
        analyzed_codes, implementation_result, test_code, broken_scenarios
    ):
        file_name = file_info["file_name"]

        prompts = get_review_prompts(
            file_name=file_name,
            implementation=impl,
            tests=tests,
            broken_scenario=broken,
            security_findings=security_findings,
        )
        messages = [
            {"role": "system", "content": prompts["system_prompt"]},
            {"role": "user", "content": prompts["user_prompt"]},
        ]

        def parse_review(content: str) -> dict:
            return FinalReviewSchema(**parse_llm_json(content)).model_dump()

        result = await call_llm_with_retry(messages, parse_review)
        final_review.append(result)

    return {
        "final_review": final_review,
        "pr_review_steps": ["Review: implementation revised with test and security findings."],
    }


async def judge_node(state: PRReviewState) -> dict:
    final_review = state["final_review"]
    analyzed_codes = state["analyzed_codes"]
    analysis_results = state["analysis_results"]

    scores = []
    judge_status = "passed"

    for reviewed, original, analysis in zip(final_review, analyzed_codes, analysis_results):
        score = await judge_code_refactory(
            original_code=original["code"],
            suggested_code=reviewed["revised_code"],
            issues=analysis.get("issues", []),
        )
        if score["score"] < 0.5:
            judge_status = "warning"
        scores.append({**score, "file_name": reviewed["file_name"]})

    return {
        "judge_scores": scores,
        "judge_status": judge_status,
        "pr_review_steps": ["Judge: quality evaluation completed."],
    }


async def human_review_node(state: PRReviewState) -> dict:
    final_review = state["final_review"]
    decision = interrupt(f"Do you confirm the changes?: {final_review}")
    return {"human_approved": decision}


async def pr_agent_node(state: PRReviewState) -> dict:
    final_review = state["final_review"]
    judge_scores = state["judge_scores"]
    pr_url = state["pr_url"]

    prompts = get_pr_agent_prompts(final_review=final_review, judge_scores=judge_scores)
    messages = [
        {"role": "system", "content": prompts["system_prompt"]},
        {"role": "user", "content": prompts["user_prompt"]},
    ]

    def parse_pr_result(content: str) -> dict:
        return PRResultSchema(**parse_llm_json(content)).model_dump()

    pr_meta = await call_llm_with_retry(messages, parse_pr_result)

    for reviewed in final_review:
        await asyncio.to_thread(
            apply_patch,
            pr_url=pr_url,
            file_name=reviewed["file_name"],
            suggested_code=reviewed["revised_code"],
        )

    for comment in pr_meta.get("comments", []):
        await asyncio.to_thread(
            create_pr_comment,
            pr_url=pr_url,
            file_name=comment["file_name"],
            line=comment["line"],
            body=comment["body"],
        )

    return {
        "pr_result": {**pr_meta, "patch_status": "patched"},
        "pr_review_steps": ["PR agent: patch applied, PR description and comments posted."],
    }