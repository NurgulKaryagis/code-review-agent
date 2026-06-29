import json

from agent.tools.utils import call_llm_with_retry
from config.prompts import get_judge_prompt


async def judge_code_refactory(original_code: str, suggested_code: str, issues: list) -> dict:
    prompts = get_judge_prompt(original_code, suggested_code, issues)
    messages = [
        {"role": "system", "content": prompts["system_prompt"]},
        {"role": "user", "content": prompts["user_prompt"]},
    ]
    return await call_llm_with_retry(messages, json.loads)