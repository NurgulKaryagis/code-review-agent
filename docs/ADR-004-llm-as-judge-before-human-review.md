## ADR-004: LLM-as-Judge Before Human Review

**Status:** Accepted

**Context:** In this project, we need to evaluate the suggestion of agent but performing this manually may result in missing of underqualified suggestion by developer. However, LLM-as-Judge usage enables developer to be warned before approve stage. 

**Decision:** LLM-as-Judge was chosen.

**Consequences:** LLM-as-Judge is necessary for evaluating a code refactoring suggestion by agent to avoid underqualified or incorrect suggestions. It is leveraged before human review to give insight to developer before approving the code refactoring.It enables developer to decide their decision more informed way. However, it means that the workflow has also one more LLM call which adds latency and increases API cost.