from github import Github, GithubException, UnknownObjectException, RateLimitExceededException
from config.settings import GITHUB_TOKEN

_TIMEOUT = 30


def _parse_pr_url(pr_url: str) -> tuple[str, str, int]:
    try:
        parts = pr_url.split("github.com/")[1].split("/")
        owner = parts[0]
        repo_name = parts[1]
        pull_number = int(parts[3])
        return owner, repo_name, pull_number
    except (IndexError, ValueError) as e:
        raise ValueError(f"Invalid GitHub PR URL format: {pr_url!r}") from e


def get_pr_files(pr_url: str) -> list[dict]:
    g = Github(GITHUB_TOKEN, timeout=_TIMEOUT)
    owner, repo_name, pull_number = _parse_pr_url(pr_url)

    try:
        repo = g.get_repo(f"{owner}/{repo_name}")
        pr = repo.get_pull(pull_number)
        files = pr.get_files()
        return [{"file_name": file.filename, "code": file.patch} for file in files]
    except RateLimitExceededException:
        raise RuntimeError("GitHub API rate limit exceeded. Please wait before retrying.")
    except UnknownObjectException:
        raise RuntimeError(
            f"PR not found: {pr_url}. Check the URL and your GITHUB_TOKEN permissions."
        )
    except GithubException as e:
        raise RuntimeError(
            f"GitHub API error ({e.status}): {e.data.get('message', str(e))}"
        ) from e


def create_pr_comment(pr_url: str, file_name: str, line: int, body: str) -> dict:
    g = Github(GITHUB_TOKEN, timeout=_TIMEOUT)
    owner, repo_name, pull_number = _parse_pr_url(pr_url)

    try:
        repo = g.get_repo(f"{owner}/{repo_name}")
        pr = repo.get_pull(pull_number)
        commit = repo.get_commit(pr.head.sha)
        pr.create_review_comment(
            body=body,
            commit=commit,
            path=file_name,
            line=line,
        )
        return {"status": "commented", "file_name": file_name, "line": line}
    except RateLimitExceededException:
        raise RuntimeError("GitHub API rate limit exceeded. Please wait before retrying.")
    except UnknownObjectException:
        raise RuntimeError(f"PR or file not found: {pr_url}, {file_name!r}.")
    except GithubException as e:
        raise RuntimeError(
            f"GitHub API error ({e.status}): {e.data.get('message', str(e))}"
        ) from e


def apply_patch(pr_url: str, file_name: str, suggested_code: str) -> dict:
    g = Github(GITHUB_TOKEN, timeout=_TIMEOUT)
    owner, repo_name, pull_number = _parse_pr_url(pr_url)

    try:
        repo = g.get_repo(f"{owner}/{repo_name}")
        pr = repo.get_pull(pull_number)
        branch_name = pr.head.ref
        contents = repo.get_contents(file_name, ref=branch_name)
        repo.update_file(
            path=file_name,
            message=f"refactor: apply code review suggestions for {file_name}",
            content=suggested_code,
            sha=contents.sha,
            branch=branch_name,
        )
        return {"status": "patched", "file_name": file_name}
    except RateLimitExceededException:
        raise RuntimeError("GitHub API rate limit exceeded. Please wait before retrying.")
    except UnknownObjectException:
        raise RuntimeError(f"PR or file not found: {pr_url}, {file_name!r}.")
    except GithubException as e:
        raise RuntimeError(
            f"GitHub API error ({e.status}): {e.data.get('message', str(e))}"
        ) from e
