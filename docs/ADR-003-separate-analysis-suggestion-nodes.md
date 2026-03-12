## ADR-003: Analysis and Suggestion as Separate Nodes

**Status:** Accepted

**Context:** In this project, we need to analyze the code differences and suggest changes based on this analysis. The steps need to be separated to enable clear tracing in LangSmith. Also, unnecessary LLM calls need to be avoided at suggestion step in the case of incorrect or unnecessary analysis.

**Decision:** Separation of analysis and suggestion steps was chosen.

**Consequences:**  Separating analysis and suggestion steps enables detailed tracing  in LangSmith and unncessary LLM calls are prevented. However, implementation complexity is increased by extra step.