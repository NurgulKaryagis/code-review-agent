## ADR-005: LiteLLM for LLM Abstraction

**Status:** Accepted

**Context:** In this project, multiple LLM calls are made across different nodes. Using a provider-specific library such as OpenAI SDK directly would create tight coupling to a single provider. Switching to a different model or provider would require code changes across multiple nodes.

**Decision:** LiteLLM was chosen.

**Consequences:** LiteLLM provides a unified interface for multiple LLM providers. Switching between models requires only changing the model parameter, without modifying node logic. However, it adds an extra dependency and may introduce a slight overhead compared to using the provider SDK directly.