# ADR-001: LangGraph over LangChain LCEL

**Status:** Accepted

**Context:** In this project, an agentic workflow has been built. The workflow contains HITL and an approval step. Although the flow appears linear, it includes conditional decisions. LangChain LCEL is a good fit for linear workflows but does not support loops and conditional flows natively.

**Decision:** LangGraph was chosen.

**Consequences:** LangGraph natively supports for loops, branching, and conditional flows. It provides full control over state, edges, and interrupts — critical for production-level HITL. However more complex than LCEL and CrewAI, and it has steeper learning curve.