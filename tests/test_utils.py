import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.tools.utils import call_llm_with_retry, parse_llm_json


def _llm_response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


MESSAGES = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Say hello."},
]


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

async def test_returns_parsed_result_on_success():
    response = _llm_response(json.dumps({"key": "value"}))
    with patch("agent.tools.utils.acompletion", new_callable=AsyncMock, return_value=response):
        result = await call_llm_with_retry(MESSAGES, parse_llm_json)

    assert result == {"key": "value"}


async def test_calls_acompletion_once_on_success():
    response = _llm_response(json.dumps({"ok": True}))
    with patch("agent.tools.utils.acompletion", new_callable=AsyncMock, return_value=response) as mock_comp:
        await call_llm_with_retry(MESSAGES, parse_llm_json)

    assert mock_comp.call_count == 1


# ---------------------------------------------------------------------------
# JSON parse failure → stricter prompt retry
# ---------------------------------------------------------------------------

async def test_retries_with_stricter_prompt_on_json_error():
    good = _llm_response(json.dumps({"key": "value"}))
    with patch("agent.tools.utils.acompletion", new_callable=AsyncMock, side_effect=[
        _llm_response("not valid json"),
        good,
    ]) as mock_comp:
        result = await call_llm_with_retry(MESSAGES, parse_llm_json)

    assert result == {"key": "value"}
    assert mock_comp.call_count == 2
    second_system_msg = mock_comp.call_args_list[1][1]["messages"][0]["content"]
    assert "valid JSON only" in second_system_msg


async def test_raises_runtime_error_after_max_json_retries():
    with patch("agent.tools.utils.acompletion", new_callable=AsyncMock, return_value=_llm_response("not json")):
        with pytest.raises(RuntimeError, match="failed after"):
            await call_llm_with_retry(MESSAGES, parse_llm_json)


# ---------------------------------------------------------------------------
# API / network failure → exponential backoff
# ---------------------------------------------------------------------------

async def test_retries_on_api_exception_and_succeeds():
    good = _llm_response(json.dumps({"key": "value"}))
    with patch("agent.tools.utils.acompletion", new_callable=AsyncMock, side_effect=[Exception("timeout"), good]) as mock_comp, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        result = await call_llm_with_retry(MESSAGES, parse_llm_json)

    assert result == {"key": "value"}
    assert mock_comp.call_count == 2


async def test_raises_runtime_error_after_max_api_retries():
    with patch("agent.tools.utils.acompletion", new_callable=AsyncMock, side_effect=Exception("network down")), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(RuntimeError, match="failed after"):
            await call_llm_with_retry(MESSAGES, parse_llm_json)


async def test_sleep_called_with_exponential_backoff():
    good = _llm_response(json.dumps({"key": "value"}))
    with patch("agent.tools.utils.acompletion", new_callable=AsyncMock, side_effect=[
        Exception("err1"),
        Exception("err2"),
        good,
    ]), \
    patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await call_llm_with_retry(MESSAGES, parse_llm_json)

    sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
    assert sleep_calls == [2, 4]


# ---------------------------------------------------------------------------
# parse_llm_json
# ---------------------------------------------------------------------------

def test_parse_llm_json_strips_code_fences():
    content = "```json\n{\"key\": \"value\"}\n```"
    result = parse_llm_json(content)
    assert result == {"key": "value"}


def test_parse_llm_json_handles_plain_json():
    result = parse_llm_json('{"score": 0.9}')
    assert result["score"] == 0.9


def test_parse_llm_json_strips_backtick_only_fences():
    result = parse_llm_json("```\n{\"a\": 1}\n```")
    assert result == {"a": 1}