import logging
import re

logger = logging.getLogger(__name__)

_INJECTION_PATTERNS = [
    r"ignore\s+(previous|above|all)\s+instructions",
    r"disregard\s+(previous|above|all)\s+instructions",
    r"forget\s+(previous|above|all)\s+instructions",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+(a|an)\s+\w+",
    r"new\s+persona",
    r"system\s*:\s*you",
    r"<\s*system\s*>",
    r"\[system\]",
    r"###\s*instruction",
    r"your\s+new\s+task\s+is",
    r"override\s+(your\s+)?(previous\s+)?instructions",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


def detect_prompt_injection(text: str) -> list[str]:
    """Return a list of matched injection patterns found in text; empty if clean."""
    if not text:
        return []
    matches = []
    for pattern in _COMPILED:
        match = pattern.search(text)
        if match:
            matches.append(match.group(0))
    if matches:
        logger.warning("Prompt injection patterns detected: %s", matches)
    return matches


def validate_llm_output(ast_result: dict, llm_result: dict) -> list[str]:
    """Compare AST findings against LLM output and return a list of conflicts."""
    conflicts = []

    ast_fn_count = ast_result.get("function_count", 0)
    llm_fn_count = llm_result.get("function_count")
    if llm_fn_count is not None and ast_fn_count != llm_fn_count:
        conflicts.append(
            f"function_count mismatch: AST={ast_fn_count}, LLM={llm_fn_count}"
        )

    ast_severity = ast_result.get("severity", "").lower()
    llm_severity = llm_result.get("severity", "").lower()
    severity_rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    if ast_severity and llm_severity:
        ast_rank = severity_rank.get(ast_severity, -1)
        llm_rank = severity_rank.get(llm_severity, -1)
        if abs(ast_rank - llm_rank) >= 2:
            conflicts.append(
                f"severity conflict: AST={ast_severity}, LLM={llm_severity}"
            )

    ast_issues = set(ast_result.get("issues", []))
    llm_issues = set(llm_result.get("issues", []))
    if ast_issues and not ast_issues.intersection(llm_issues):
        conflicts.append(
            f"AST issues not reflected in LLM output: {ast_issues}"
        )

    if conflicts:
        logger.warning("AST vs LLM output conflicts: %s", conflicts)
    return conflicts