# ADR-006: Layered Error Handling Strategy

**Status:** Accepted

**Context:** The workflow touches three external systems: the LLM API, the GitHub API, and the local Python AST parser. Each fails for different reasons at different rates. LLM calls fail transiently (rate limits, timeouts). GitHub API calls fail due to auth issues, missing resources, or rate limits. AST parsing fails on malformed diffs or non-Python files. A single undifferentiated error handler cannot respond appropriately to all three.

**Rejected Alternatives:**

- *Single global try/except around the full graph:* Catches everything but loses the failure source. A GitHub 404 and a JSON parse error from the LLM look identical to the caller. The developer cannot act on the error without reading logs.
- *Fail-fast on any error:* Simple to implement but makes the workflow brittle. A single file with a syntax error that trips AST parsing aborts the entire PR review, even if the other files are perfectly valid.

**Decision:** Each failure domain has its own strategy. LLM calls use exponential backoff retry (see ADR-007) with a stricter prompt on parse failures. GitHub API calls are wrapped in try/except blocks that convert `GithubException`, `UnknownObjectException`, and `RateLimitExceededException` into descriptive `RuntimeError` messages that include the HTTP status and GitHub's error message. AST parsing failures are caught per-file — the file is skipped with a `logger.warning` and a default low-severity result is returned, allowing the rest of the PR to continue. Credential validation runs at import time in `config/settings.py`, raising `EnvironmentError` on startup rather than at the first API call.

**Consequences:** Errors surface with enough context to act on: a GitHub 404 tells the developer to check the PR URL and token permissions; an AST skip warning tells them which file could not be parsed. Fail-fast on credentials prevents the workflow from starting in a misconfigured state, which is preferable to failing halfway through. The cost is increased implementation complexity — each integration point must explicitly handle its own error cases rather than relying on a single catch-all.
