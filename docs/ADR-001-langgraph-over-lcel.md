# ADR-001: LangGraph over LangChain LCEL

**Status:** Accepted

**Context:** The workflow requires HITL at the approval step, conditional routing based on human decision, parallel execution of test and security agents, and persistent state across an HTTP request boundary (webhook → approve). These needs make orchestration a first-class concern, not an afterthought.

**Rejected Alternatives:**

- *LangChain LCEL:* Designed for linear pipelines. Does not natively support cycles, conditional branching, or mid-graph interrupts. Adding HITL would require custom wrappers that recreate what LangGraph already provides.
- *CrewAI:* Provides multi-agent coordination but abstracts away state and edge control. The graph topology (which node runs when, and what state it reads) cannot be inspected or overridden, making debugging and auditing difficult.

**Decision:** LangGraph was chosen. Each processing step is a typed node that reads from and writes to a shared `PRReviewState` TypedDict. Edges are explicit — both linear (`add_edge`) and conditional (`add_conditional_edges`). Parallel execution is expressed as a fan-out/fan-in edge pattern. HITL is implemented with LangGraph's `interrupt()` primitive, which pauses the graph mid-execution, saves state to the checkpointer, and waits for a `Command(resume=...)` call.

**Consequences:** The graph topology is fully auditable: every edge, every state field, and every conditional is declared in `graph.py`. LangSmith tracing shows each node's input and output independently. The cost is a steeper learning curve than LCEL — developers must understand state reducers, checkpointers, and the fan-out/fan-in pattern before contributing to the graph.