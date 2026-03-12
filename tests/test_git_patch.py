import pytest
from unittest.mock import MagicMock, patch, call
from github import GithubException, UnknownObjectException, RateLimitExceededException

from agent.tools.git_patch import get_pr_files, apply_patch


def _make_github_mock(files=None, pr_ref="feature-branch", file_sha="abc123"):
    """Return a configured Github instance mock."""
    mock_file = MagicMock()
    mock_file.filename = "foo.py"
    mock_file.patch = "@@ -1 +1 @@\n-old\n+new"

    mock_pr = MagicMock()
    mock_pr.get_files.return_value = files if files is not None else [mock_file]
    mock_pr.head.ref = pr_ref

    mock_contents = MagicMock()
    mock_contents.sha = file_sha

    mock_repo = MagicMock()
    mock_repo.get_pull.return_value = mock_pr
    mock_repo.get_contents.return_value = mock_contents

    mock_g = MagicMock()
    mock_g.get_repo.return_value = mock_repo

    return mock_g, mock_repo, mock_pr, mock_file


# ---------------------------------------------------------------------------
# get_pr_files
# ---------------------------------------------------------------------------

class TestGetPrFiles:
    def test_returns_list_of_file_dicts(self):
        mock_g, mock_repo, mock_pr, mock_file = _make_github_mock()

        with patch("agent.tools.git_patch.Github", return_value=mock_g):
            result = get_pr_files("https://github.com/owner/repo/pull/42")

        assert result == [{"file_name": "foo.py", "code": mock_file.patch}]

    def test_parses_owner_repo_and_pull_number(self):
        mock_g, mock_repo, _, _ = _make_github_mock()

        with patch("agent.tools.git_patch.Github", return_value=mock_g):
            get_pr_files("https://github.com/myorg/myrepo/pull/99")

        mock_g.get_repo.assert_called_once_with("myorg/myrepo")
        mock_repo.get_pull.assert_called_once_with(99)

    def test_invalid_url_raises_value_error(self):
        with patch("agent.tools.git_patch.Github"):
            with pytest.raises(ValueError, match="Invalid GitHub PR URL"):
                get_pr_files("https://not-github.com/bad-url")

    def test_pr_not_found_raises_runtime_error(self):
        mock_g, mock_repo, _, _ = _make_github_mock()
        mock_repo.get_pull.side_effect = UnknownObjectException(404, {}, {})

        with patch("agent.tools.git_patch.Github", return_value=mock_g):
            with pytest.raises(RuntimeError, match="PR not found"):
                get_pr_files("https://github.com/owner/repo/pull/1")

    def test_rate_limit_raises_runtime_error(self):
        mock_g, mock_repo, _, _ = _make_github_mock()
        mock_repo.get_pull.side_effect = RateLimitExceededException(403, {}, {})

        with patch("agent.tools.git_patch.Github", return_value=mock_g):
            with pytest.raises(RuntimeError, match="rate limit"):
                get_pr_files("https://github.com/owner/repo/pull/1")

    def test_github_api_error_raises_runtime_error(self):
        mock_g, mock_repo, _, _ = _make_github_mock()
        mock_repo.get_pull.side_effect = GithubException(500, {"message": "server error"}, {})

        with patch("agent.tools.git_patch.Github", return_value=mock_g):
            with pytest.raises(RuntimeError, match="GitHub API error"):
                get_pr_files("https://github.com/owner/repo/pull/1")


# ---------------------------------------------------------------------------
# apply_patch
# ---------------------------------------------------------------------------

class TestApplyPatch:
    def test_calls_update_file_with_correct_args(self):
        mock_g, mock_repo, _, _ = _make_github_mock(pr_ref="my-branch", file_sha="sha999")

        with patch("agent.tools.git_patch.Github", return_value=mock_g):
            result = apply_patch(
                "https://github.com/owner/repo/pull/7",
                "foo.py",
                "def foo(): return 42",
            )

        mock_repo.get_contents.assert_called_once_with("foo.py", ref="my-branch")
        mock_repo.update_file.assert_called_once_with(
            path="foo.py",
            message="refactor: apply code review suggestions for foo.py",
            content="def foo(): return 42",
            sha="sha999",
            branch="my-branch",
        )
        assert result == {"status": "patched", "file_name": "foo.py"}

    def test_rate_limit_raises_runtime_error(self):
        mock_g, mock_repo, _, _ = _make_github_mock()
        mock_repo.update_file.side_effect = RateLimitExceededException(403, {}, {})

        with patch("agent.tools.git_patch.Github", return_value=mock_g):
            with pytest.raises(RuntimeError, match="rate limit"):
                apply_patch("https://github.com/owner/repo/pull/1", "foo.py", "code")

    def test_file_not_found_raises_runtime_error(self):
        mock_g, mock_repo, _, _ = _make_github_mock()
        mock_repo.get_contents.side_effect = UnknownObjectException(404, {}, {})

        with patch("agent.tools.git_patch.Github", return_value=mock_g):
            with pytest.raises(RuntimeError, match="not found"):
                apply_patch("https://github.com/owner/repo/pull/1", "foo.py", "code")
