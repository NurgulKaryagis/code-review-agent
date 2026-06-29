# ADR-003: Separate Analysis and Suggestion Nodes

**Status:** Accepted

**Context:** Code review involves two distinct cognitive tasks: understanding what is wrong with the existing code, and proposing how to fix it. Merging these into a single LLM call produces a prompt that asks the model to reason about problems and generate solutions simultaneously, which degrades output quality and makes failures harder to diagnose.

**Rejected Alternative:** A single monolithic node that fetches PR files, runs AST analysis, calls the LLM once for both analysis and suggestion, and passes the result to the judge. This is simpler to implement but has three problems: (1) a JSON schema error in the suggestion output forces a full retry including the analysis call, doubling cost; (2) LangSmith shows one opaque trace instead of two inspectable steps; (3) the suggestion cannot be regenerated independently if the developer wants a different style without re-running analysis.

**Decision:** The workflow is split into `code_analyst` and `implementation` nodes. `code_analyst` produces `analysis_results` and `repo_context` — a structured description of what is wrong and what patterns the codebase uses. `implementation` reads these fields and proposes `implementation_result` in a focused prompt that does not repeat the analysis work. Each node has its own retry boundary via `call_llm_with_retry`.

**Consequences:** Each node's output is a distinct, inspectable state field. A failure in `implementation` retries only the suggestion LLM call, not the AST analysis. LangSmith traces show the analysis and suggestion steps separately. The cost is one additional LLM call per PR file compared to the monolithic approach.
