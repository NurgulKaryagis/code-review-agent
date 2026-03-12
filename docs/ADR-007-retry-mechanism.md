## ADR-007: Retry Mechanism

**Status:** Accepted

**Context:** In this project, multiple LLM calls are made across analysis, suggestion and judge nodes. LLM calls are not guaranteed to succeed on first attempt due to transient failures such as network timeouts and rate limits. Without retry mechanism, a single failure would cause the entire workflow to fail.

**Decision:** Exponential backoff retry was chosen for LLM calls.

**Consequences:** Retry mechanism prevents transient LLM failures from failing the entire workflow. Max 3 attempts with exponential backoff prevents excessive API usage. However, it adds latency on failure since each retry waits longer than the previous attempt.