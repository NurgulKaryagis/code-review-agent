import json
import logging
import time
from json import JSONDecodeError

from litellm import completion
from config.prompts import get_judge_prompt

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_LLM_TIMEOUT = 30


def judge_code_refactory(original_code: str, suggested_code: str, issues: list) -> dict:
    prompts = get_judge_prompt(original_code, suggested_code, issues)
    messages = [
        {"role": "system", "content": prompts["system_prompt"]},
        {"role": "user", "content": prompts["user_prompt"]},
    ]

    last_exc = None
    strict = False
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            effective_messages = messages
            if strict:
                effective_messages = [
                    {**messages[0], "content": messages[0]["content"] + "\nIMPORTANT: Respond with valid JSON only, no extra text."},
                    messages[1],
                ]
            response = completion(
                model="gpt-4o-mini",
                messages=effective_messages,
                timeout=_LLM_TIMEOUT,
            )
            return json.loads(response.choices[0].message.content)
        except JSONDecodeError as e:
            last_exc = e
            logger.warning(
                "judge attempt %d/%d: invalid JSON response — retrying with stricter prompt",
                attempt, _MAX_RETRIES,
            )
            strict = True
        except Exception as e:
            last_exc = e
            if attempt < _MAX_RETRIES:
                wait = 2 ** attempt
                logger.warning(
                    "judge attempt %d/%d: LLM error: %s — retrying in %ds",
                    attempt, _MAX_RETRIES, e, wait,
                )
                time.sleep(wait)
            else:
                logger.error("judge failed after %d attempts: %s", _MAX_RETRIES, e)

    raise RuntimeError(f"judge_code_refactory failed after {_MAX_RETRIES} attempts") from last_exc
