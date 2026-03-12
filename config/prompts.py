def get_analysis_prompts(file_name, severity, issues, function_count, code_diff):
    system_prompt = """You are a senior software engineer specialized in code review.
    You analyze code changes and identify issues clearly and concisely.
    Always respond in JSON format."""
    
    user_prompt = f"""Review the following code change and provide analysis.

    File: {file_name}
    Severity: {severity}
    Detected Issues: {issues}

    Code Diff:
    {code_diff}

    Respond in this exact JSON format:
    {{
        "file_name": "{file_name}",
        "issues": ["issue1", "issue2"],
        "severity": "{severity}",
        "function_count": {function_count}
    }}"""
    
    return {"system_prompt": system_prompt,
             "user_prompt" : user_prompt}


def get_suggestion_prompts(file_name, code, issues):
    system_prompt = """You are a senior software engineer specialized in code refactoring.
    You receive code diffs and analysis issues, then produce improved, corrected code.
    Always respond in JSON format."""

    user_prompt = f"""Based on the analysis issues below, provide a refactored version of the code.

    File: {file_name}
    Identified Issues: {issues}

    Original Code:
    {code}

    Respond in this exact JSON format:
    {{
        "suggestion_id": 1,
        "file_name": "{file_name}",
        "suggested_code": "<full refactored code here>"
    }}"""

    return {"system_prompt": system_prompt,
            "user_prompt": user_prompt}
    
    
def get_judge_prompt(original_code: str, suggested_code: str, issues: list) -> dict:
    system_prompt = """You are a senior software engineer evaluating code review suggestions.
    Your job is to assess whether a suggested code change correctly fixes the identified issues.
    Always respond in JSON format."""

    user_prompt = f"""Evaluate the following code change.

    Identified Issues:
    {issues}

    Original Code:
    {original_code}

    Suggested Code:
    {suggested_code}

    Respond in this exact JSON format:
    {{
        "score": 0.0,
        "reasoning": "explanation here"
    }}

    Score must be between 0 and 1:
    0.0 = suggestion does not fix the issues
    1.0 = suggestion perfectly fixes all issues"""

    return {"system_prompt": system_prompt, "user_prompt": user_prompt}