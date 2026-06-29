# ADR-007: Exponential Backoff Retry with Strict Prompt Escalation

**Status:** Accepted

**Context:** LLM API calls fail for two distinct reasons: transient infrastructure errors (network timeouts, rate limits, provider 5xx) and output format errors (the model returns prose instead of JSON, or JSON that does not match the expected schema). These require different remedies. Infrastructure errors need time before retrying. Output format errors need a more explicit instruction, not more time.

**Rejected Alternatives:**

- *Single attempt, no retry:* A single transient timeout aborts the entire workflow. Given that a PR review may involve 5–10 LLM calls, the probability of at least one transient failure in a session is non-trivial.
- *Fixed interval retry:* Retrying immediately after a rate limit error is likely to hit the same limit again. A fixed 2-second wait does not back off enough under sustained load.
- *Infinite retry:* Prevents the workflow from ever terminating on a persistent failure (wrong API key, model deprecated). The graph would hang indefinitely.

**Decision:** `call_llm_with_retry` in `agent/tools/utils.py` implements up to 3 attempts. On an infrastructure exception, it waits `2^attempt` seconds before the next attempt (2s, then 4s). On a `JSONDecodeError` or Pydantic `ValidationError`, it does not wait — instead, it appends `"IMPORTANT: Respond with valid JSON only, no extra text."` to the system prompt and retries immediately. This strict prompt escalation addresses the most common cause of parse failures (the model wrapping JSON in a markdown code block or adding a preamble) without wasting time on a backoff that serves no purpose for output errors. After 3 failed attempts, a `RuntimeError` is raised and propagates up through the node to the graph, which terminates the run.

**Consequences:** Transient failures are recovered automatically in most cases without developer intervention. The maximum additional latency from retries is bounded at 6 seconds (2 + 4). Persistent failures surface as a `RuntimeError` with a clear message. Because retry logic lives in one place (`utils.py`), changing the retry policy — number of attempts, backoff multiplier, strict prompt text — requires editing a single function.