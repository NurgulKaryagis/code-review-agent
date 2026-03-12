import json
import pytest
from unittest.mock import MagicMock, patch

from eval.judge import judge_code_refactory


def _llm_response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_returns_score_and_reasoning():
    payload = {"score": 0.8, "reasoning": "looks good"}
    with patch("eval.judge.completion", return_value=_llm_response(json.dumps(payload))):
        result = judge_code_refactory("old code", "new code", ["issue1"])

    assert result["score"] == 0.8
    assert result["reasoning"] == "looks good"


# ---------------------------------------------------------------------------
# JSON parse failure → retry with stricter prompt
# ---------------------------------------------------------------------------

def test_retries_with_stricter_prompt_on_json_error():
    good_payload = {"score": 0.5, "reasoning": "ok after retry"}
    responses = [_llm_response("not valid json"), _llm_response(json.dumps(good_payload))]

    with patch("eval.judge.completion", side_effect=responses) as mock_comp:
        result = judge_code_refactory("old", "new", [])

    assert result["score"] == 0.5
    assert mock_comp.call_count == 2
    # Second call must carry the stricter system prompt
    second_system_msg = mock_comp.call_args_list[1][1]["messages"][0]["content"]
    assert "valid JSON only" in second_system_msg


def test_raises_runtime_error_after_max_json_retries():
    bad = _llm_response("still not json")
    with patch("eval.judge.completion", return_value=bad):
        with pytest.raises(RuntimeError, match="failed after"):
            judge_code_refactory("old", "new", [])


# ---------------------------------------------------------------------------
# API / network failure → exponential backoff retry
# ---------------------------------------------------------------------------

def test_retries_on_api_exception_and_succeeds():
    good_payload = {"score": 0.9, "reasoning": "great"}
    responses = [Exception("timeout"), _llm_response(json.dumps(good_payload))]

    with patch("eval.judge.completion", side_effect=responses) as mock_comp, \
         patch("eval.judge.time.sleep"):
        result = judge_code_refactory("old", "new", [])

    assert result["score"] == 0.9
    assert mock_comp.call_count == 2


def test_raises_runtime_error_after_max_api_retries():
    with patch("eval.judge.completion", side_effect=Exception("network down")), \
         patch("eval.judge.time.sleep"):
        with pytest.raises(RuntimeError, match="failed after"):
            judge_code_refactory("old", "new", [])


def test_sleep_called_with_exponential_backoff():
    with patch("eval.judge.completion", side_effect=Exception("err")), \
         patch("eval.judge.time.sleep") as mock_sleep:
        with pytest.raises(RuntimeError):
            judge_code_refactory("old", "new", [])

    # backoff: 2^1=2 on attempt 1, 2^2=4 on attempt 2; attempt 3 does not sleep
    sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
    assert sleep_calls == [2, 4]
