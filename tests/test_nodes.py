import json
import pytest
from unittest.mock import MagicMock, patch, call

from agent.nodes import analysis_node, suggestion_node, judge_node, patch_node


def _llm_response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

ANALYSIS_LLM_PAYLOAD = {
    "file_name": "foo.py",
    "issues": ["too complex"],
    "severity": "high",
    "function_count": 2,
}

SUGGESTION_LLM_PAYLOAD = {
    "suggestion_id": 1,
    "file_name": "foo.py",
    "suggested_code": "def foo(): return 42",
}

PR_URL = "https://github.com/owner/repo/pull/1"


# ---------------------------------------------------------------------------
# analysis_node
# ---------------------------------------------------------------------------

class TestAnalysisNode:
    def _state(self):
        return {"pr_url": PR_URL, "pr_review_steps": []}

    def test_returns_analyzed_codes_and_results(self):
        pr_files = [{"file_name": "foo.py", "code": "def foo(): pass"}]
        ast_result = {"severity": "high", "issues": ["too complex"], "function_count": 2}
        llm_resp = _llm_response(json.dumps(ANALYSIS_LLM_PAYLOAD))

        with patch("agent.nodes.get_pr_files", return_value=pr_files), \
             patch("agent.nodes.analyze_code", return_value=ast_result), \
             patch("agent.nodes.completion", return_value=llm_resp):
            result = analysis_node(self._state())

        assert result["analysis_status"] == "analyzed"
        assert len(result["analyzed_codes"]) == 1
        assert len(result["analysis_results"]) == 1

    def test_analyzed_codes_contain_file_name_and_code(self):
        pr_files = [{"file_name": "foo.py", "code": "def foo(): pass"}]
        ast_result = {"severity": "low", "issues": [], "function_count": 1}
        llm_resp = _llm_response(json.dumps({**ANALYSIS_LLM_PAYLOAD, "severity": "low", "issues": [], "function_count": 1}))

        with patch("agent.nodes.get_pr_files", return_value=pr_files), \
             patch("agent.nodes.analyze_code", return_value=ast_result), \
             patch("agent.nodes.completion", return_value=llm_resp):
            result = analysis_node(self._state())

        assert result["analyzed_codes"][0]["file_name"] == "foo.py"
        assert result["analyzed_codes"][0]["code"] == "def foo(): pass"

    def test_analysis_results_contain_severity_and_issues(self):
        pr_files = [{"file_name": "foo.py", "code": "def foo(): pass"}]
        ast_result = {"severity": "high", "issues": ["too complex"], "function_count": 2}
        llm_resp = _llm_response(json.dumps(ANALYSIS_LLM_PAYLOAD))

        with patch("agent.nodes.get_pr_files", return_value=pr_files), \
             patch("agent.nodes.analyze_code", return_value=ast_result), \
             patch("agent.nodes.completion", return_value=llm_resp):
            result = analysis_node(self._state())

        ar = result["analysis_results"][0]
        assert ar["severity"] == "high"
        assert "too complex" in ar["issues"]

    def test_multiple_files_produce_multiple_results(self):
        pr_files = [
            {"file_name": "a.py", "code": "def a(): pass"},
            {"file_name": "b.py", "code": "def b(): pass"},
        ]
        ast_result = {"severity": "low", "issues": [], "function_count": 1}
        payload_a = {**ANALYSIS_LLM_PAYLOAD, "file_name": "a.py", "severity": "low", "issues": [], "function_count": 1}
        payload_b = {**ANALYSIS_LLM_PAYLOAD, "file_name": "b.py", "severity": "low", "issues": [], "function_count": 1}
        responses = [_llm_response(json.dumps(payload_a)), _llm_response(json.dumps(payload_b))]

        with patch("agent.nodes.get_pr_files", return_value=pr_files), \
             patch("agent.nodes.analyze_code", return_value=ast_result), \
             patch("agent.nodes.completion", side_effect=responses):
            result = analysis_node(self._state())

        assert len(result["analyzed_codes"]) == 2
        assert len(result["analysis_results"]) == 2

    def test_step_message_appended(self):
        pr_files = [{"file_name": "foo.py", "code": ""}]
        ast_result = {"severity": "low", "issues": [], "function_count": 0}
        llm_resp = _llm_response(json.dumps({**ANALYSIS_LLM_PAYLOAD, "severity": "low", "issues": [], "function_count": 0}))

        with patch("agent.nodes.get_pr_files", return_value=pr_files), \
             patch("agent.nodes.analyze_code", return_value=ast_result), \
             patch("agent.nodes.completion", return_value=llm_resp):
            result = analysis_node(self._state())

        assert "Analysis is completed." in result["pr_review_steps"]


# ---------------------------------------------------------------------------
# suggestion_node
# ---------------------------------------------------------------------------

class TestSuggestionNode:
    def _state(self):
        return {
            "analyzed_codes": [{"file_name": "foo.py", "code": "def foo(): pass"}],
            "analysis_results": [{"file_name": "foo.py", "issues": ["too complex"], "severity": "high", "function_count": 2}],
            "pr_review_steps": [],
        }

    def test_returns_suggested_codes_list(self):
        llm_resp = _llm_response(json.dumps(SUGGESTION_LLM_PAYLOAD))

        with patch("agent.nodes.completion", return_value=llm_resp):
            result = suggestion_node(self._state())

        assert result["suggestion_status"] == "suggested"
        assert len(result["suggested_codes"]) == 1

    def test_suggested_code_fields_are_correct(self):
        llm_resp = _llm_response(json.dumps(SUGGESTION_LLM_PAYLOAD))

        with patch("agent.nodes.completion", return_value=llm_resp):
            result = suggestion_node(self._state())

        sc = result["suggested_codes"][0]
        assert sc["file_name"] == "foo.py"
        assert sc["suggested_code"] == "def foo(): return 42"
        assert sc["suggestion_id"] == 1

    def test_suggestion_id_increments_per_file(self):
        state = {
            "analyzed_codes": [
                {"file_name": "a.py", "code": "def a(): pass"},
                {"file_name": "b.py", "code": "def b(): pass"},
            ],
            "analysis_results": [
                {"file_name": "a.py", "issues": [], "severity": "low", "function_count": 1},
                {"file_name": "b.py", "issues": [], "severity": "low", "function_count": 1},
            ],
            "pr_review_steps": [],
        }
        responses = [
            _llm_response(json.dumps({**SUGGESTION_LLM_PAYLOAD, "file_name": "a.py"})),
            _llm_response(json.dumps({**SUGGESTION_LLM_PAYLOAD, "file_name": "b.py"})),
        ]

        with patch("agent.nodes.completion", side_effect=responses):
            result = suggestion_node(state)

        assert result["suggested_codes"][0]["suggestion_id"] == 1
        assert result["suggested_codes"][1]["suggestion_id"] == 2

    def test_step_message_appended(self):
        llm_resp = _llm_response(json.dumps(SUGGESTION_LLM_PAYLOAD))

        with patch("agent.nodes.completion", return_value=llm_resp):
            result = suggestion_node(self._state())

        assert "Suggestions completed." in result["pr_review_steps"]


# ---------------------------------------------------------------------------
# judge_node
# ---------------------------------------------------------------------------

class TestJudgeNode:
    def _state(self, score=0.9):
        return {
            "suggested_codes": [{"file_name": "foo.py", "suggested_code": "def foo(): return 42", "suggestion_id": 1}],
            "analyzed_codes": [{"file_name": "foo.py", "code": "def foo(): pass"}],
            "analysis_results": [{"file_name": "foo.py", "issues": ["too complex"], "severity": "high", "function_count": 2}],
            "pr_review_steps": [],
        }

    def test_returns_judge_scores(self):
        score_payload = {"score": 0.9, "reasoning": "great fix"}
        with patch("agent.nodes.judge_code_refactory", return_value=score_payload):
            result = judge_node(self._state())

        assert len(result["judge_scores"]) == 1
        assert result["judge_scores"][0]["score"] == 0.9

    def test_judge_status_passed_when_score_above_threshold(self):
        with patch("agent.nodes.judge_code_refactory", return_value={"score": 0.8, "reasoning": "good"}):
            result = judge_node(self._state())

        assert result["judge_status"] == "passed"

    def test_judge_status_warning_when_score_below_threshold(self):
        with patch("agent.nodes.judge_code_refactory", return_value={"score": 0.3, "reasoning": "poor"}):
            result = judge_node(self._state())

        assert result["judge_status"] == "warning"

    def test_calls_judge_with_correct_args(self):
        with patch("agent.nodes.judge_code_refactory", return_value={"score": 0.9, "reasoning": "ok"}) as mock_judge:
            judge_node(self._state())

        mock_judge.assert_called_once_with(
            original_code="def foo(): pass",
            suggested_code="def foo(): return 42",
            issues=["too complex"],
        )


# ---------------------------------------------------------------------------
# patch_node
# ---------------------------------------------------------------------------

class TestPatchNode:
    def _state(self):
        return {
            "pr_url": PR_URL,
            "suggested_codes": [
                {"file_name": "foo.py", "suggested_code": "def foo(): return 42", "suggestion_id": 1}
            ],
            "pr_review_steps": [],
        }

    def test_calls_apply_patch_with_correct_args(self):
        with patch("agent.nodes.apply_patch", return_value={"status": "patched", "file_name": "foo.py"}) as mock_apply:
            patch_node(self._state())

        mock_apply.assert_called_once_with(
            pr_url=PR_URL,
            file_name="foo.py",
            suggested_code="def foo(): return 42",
        )

    def test_returns_patch_status(self):
        with patch("agent.nodes.apply_patch", return_value={"status": "patched", "file_name": "foo.py"}):
            result = patch_node(self._state())

        assert result["patch_status"] == "patched"

    def test_step_message_appended(self):
        with patch("agent.nodes.apply_patch", return_value={"status": "patched", "file_name": "foo.py"}):
            result = patch_node(self._state())

        assert "Codes are patched." in result["pr_review_steps"]

    def test_applies_patch_for_each_file(self):
        state = {
            "pr_url": PR_URL,
            "suggested_codes": [
                {"file_name": "a.py", "suggested_code": "def a(): pass", "suggestion_id": 1},
                {"file_name": "b.py", "suggested_code": "def b(): pass", "suggestion_id": 2},
            ],
            "pr_review_steps": [],
        }
        with patch("agent.nodes.apply_patch", return_value={"status": "patched", "file_name": "a.py"}) as mock_apply:
            patch_node(state)

        assert mock_apply.call_count == 2
        mock_apply.assert_any_call(pr_url=PR_URL, file_name="a.py", suggested_code="def a(): pass")
        mock_apply.assert_any_call(pr_url=PR_URL, file_name="b.py", suggested_code="def b(): pass")
