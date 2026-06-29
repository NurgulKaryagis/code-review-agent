import asyncio
import json
import logging
import re
from json import JSONDecodeError
from typing import Any, Callable

from litellm import acompletion
from pydantic import ValidationError

from config.settings import MODEL_NAME

logger = logging.getLogger(__name__)


async def call_llm_with_retry(
    messages: list,
    parse_fn: Callable[[str], Any],
    max_retries: int = 3,
    timeout: int = 30,
) -> Any:
    last_exc = None
    strict = False
    for attempt in range(1, max_retries + 1):
        try:
            effective_messages = messages
            if strict:
                effective_messages = [
                    {**messages[0], "content": messages[0]["content"] + "\nIMPORTANT: Respond with valid JSON only, no extra text."},
                    *messages[1:],
                ]
            response = await acompletion(
                model=MODEL_NAME,
                messages=effective_messages,
                timeout=timeout,
            )
            content = response.choices[0].message.content
            return parse_fn(content)
        except (JSONDecodeError, ValidationError) as e:
            last_exc = e
            logger.warning("attempt %d/%d: parse/schema error: %s — retrying with stricter prompt", attempt, max_retries, e)
            strict = True
        except Exception as e:
            last_exc = e
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.warning("attempt %d/%d: LLM error: %s — retrying in %ds", attempt, max_retries, e, wait)
                await asyncio.sleep(wait)
                strict = True
            else:
                logger.error("LLM call failed after %d attempts: %s", max_retries, e)
    raise RuntimeError(f"LLM call failed after {max_retries} attempts") from last_exc


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
