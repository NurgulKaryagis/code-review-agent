from unittest.mock import AsyncMock, patch

from eval.judge import judge_code_refactory


async def test_returns_score_and_reasoning():
    score = {"score": 0.8, "reasoning": "looks good"}
    with patch("eval.judge.call_llm_with_retry", new_callable=AsyncMock, return_value=score):
        result = await judge_code_refactory("old code", "new code", ["issue1"])

    assert result["score"] == 0.8
    assert result["reasoning"] == "looks good"


async def test_passes_json_loads_as_parse_fn():
    import json
    score = {"score": 0.7, "reasoning": "ok"}
    captured = {}

    async def capture(messages, parse_fn):
        captured["parse_fn"] = parse_fn
        return score

    with patch("eval.judge.call_llm_with_retry", side_effect=capture):
        await judge_code_refactory("old", "new", [])

    assert captured["parse_fn"] is json.loads


async def test_messages_contain_original_and_suggested_code():
    score = {"score": 0.9, "reasoning": "great"}
    captured = {}

    async def capture(messages, parse_fn):
        captured["messages"] = messages
        return score

    with patch("eval.judge.call_llm_with_retry", side_effect=capture):
        await judge_code_refactory("original_code_here", "suggested_code_here", ["issue"])

    user_content = captured["messages"][1]["content"]
    assert "original_code_here" in user_content
    assert "suggested_code_here" in user_content


async def test_system_message_instructs_json_format():
    score = {"score": 0.5, "reasoning": "ok"}
    captured = {}

    async def capture(messages, parse_fn):
        captured["messages"] = messages
        return score

    with patch("eval.judge.call_llm_with_retry", side_effect=capture):
        await judge_code_refactory("old", "new", [])

    system_content = captured["messages"][0]["content"]
    assert "JSON" in system_content