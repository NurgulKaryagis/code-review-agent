# ADR-005: LiteLLM for LLM Provider Abstraction

**Status:** Accepted

**Context:** Every node in the graph makes LLM calls. Binding directly to the OpenAI Python SDK would mean that switching models — for cost reasons, capability reasons, or provider outages — requires touching every node that calls `openai.ChatCompletion`. The same risk applies to the judge node in `eval/judge.py`. The call site is spread across the codebase, not centralised.

**Rejected Alternatives:**

- *OpenAI SDK directly:* Tight coupling to a single provider. A model change or provider switch requires modifying every call site. Switching to Anthropic or a self-hosted model is a refactor, not a config change.
- *LangChain LLM wrappers:* Provide provider abstraction but add a heavy dependency with its own abstractions (chains, runnables) that conflict with the explicit node-and-edge design chosen in ADR-001. They also make it harder to control retry logic at the call level.

**Decision:** LiteLLM is used for all LLM calls via its `acompletion` interface (async). The model is read from the `MODEL_NAME` environment variable in `config/settings.py`, defaulting to `gpt-4o-mini`. Changing the model for the entire system requires only updating `MODEL_NAME` in `.env` — no code changes. The call site is further centralised in `agent/tools/utils.py` via `call_llm_with_retry`, so provider-specific behaviour (timeout, retry headers) is adjusted in one place.

**Consequences:** Switching between OpenAI, Anthropic, Mistral, or a local Ollama instance requires only a `MODEL_NAME` change. The abstraction adds a thin middleware layer that may obscure provider-specific error messages — LiteLLM normalises them into a common exception hierarchy, which can make debugging provider-specific issues slightly harder.
