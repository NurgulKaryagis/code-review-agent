import json
import re


def parse_llm_json(content: str) -> dict:
    """Strip markdown code fences then parse JSON."""
    content = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.IGNORECASE)
    content = re.sub(r"\s*```$", "", content.strip())
    return json.loads(content)


def extract_source_from_diff(diff: str) -> str:
    """Extract parseable Python source from a git diff patch."""
    lines = []
    for line in diff.splitlines():
        if line.startswith("@@") or line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("-"):
            continue
        lines.append(line[1:] if line.startswith("+") else line)
    return "\n".join(lines)
