## ADR-006: Error Handling Strategy

**Status:** Accepted

**Context:** In this project, multiple external calls are made across different nodes including LLM API, GitHub API and AST parsing. Each of these can fail for different reasons such as network timeouts, invalid credentials, rate limits or malformed code diffs. Without a proper error handling strategy, a single failure would cause the entire workflow to fail silently.

**Decision:** A layered error handling strategy was chosen.

**Consequences:** LLM calls are retried with exponential backoff to handle transient failures. GitHub API calls are wrapped with try/except to surface descriptive error messages. Credentials are validated on startup to fail fast before the workflow begins. AST parsing failures are caught and the file is skipped with a warning to avoid blocking the entire workflow. Overall workflow reliability is improved at the cost of slightly increased implementation complexity.