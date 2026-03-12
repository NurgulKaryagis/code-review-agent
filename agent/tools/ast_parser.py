import ast
import logging

from agent.tools.utils import extract_source_from_diff

logger = logging.getLogger(__name__)


def analyze_code(code: str, file_name: str) -> dict:
    source = extract_source_from_diff(code) if code.startswith("@@") or "\n@@" in code else code

    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError) as e:
        logger.warning("Skipping AST analysis for %r: %s", file_name, e)
        return {
            "file_name": file_name,
            "function_count": 0,
            "severity": "low",
            "issues": [],
        }

    function_count = 0
    complexity_score = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            function_count += 1
        elif isinstance(node, (ast.If, ast.For, ast.While, ast.Try)):
            complexity_score += 1

    issues = []
    if complexity_score > 10:
        severity = "high"
        issues.append("Complexity is too high")
    elif complexity_score > 5:
        severity = "medium"
        issues.append("Complexity is moderate")
    else:
        severity = "low"

    return {
        "file_name": file_name,
        "function_count": function_count,
        "severity": severity,
        "issues": issues,
    }
