## ADR-002: Human-in-the-Loop Before Patch

**Status:** Accepted

**Context:** In this project, HITL ( Human-in-the-loop ) need to be leveraged to enhance safety and reliability of the agentic workflow. Without HITL, incorrect or unnecassary code patches are commited automatically to the branches, which reduce developer trust.  

**Decision:** HITL was chosen. 

**Consequences:** Human-in-the-loop is necessary for code refactoring tool to prevent critical code alteration. It enhances accuracy, safety and reliability in agentic workflows. However, It increases complexity of implementation. It requires separate endpoint for approve and thread management with checkpointer.