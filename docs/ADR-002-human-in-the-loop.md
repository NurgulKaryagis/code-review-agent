# ADR-002: Human-in-the-Loop Before Patch

**Status:** Accepted

**Context:** The agent's final action — applying a code patch to a GitHub branch — is irreversible without a revert commit. An incorrect refactoring silently committed to a feature branch can break CI, block a release, or introduce a regression. Automated quality scoring alone is not sufficient because the judge LLM can also be wrong.

**Rejected Alternatives:**

- *Fully automated patching:* Removes the human check entirely. Acceptable for low-risk stylistic changes but unacceptable for structural refactors that alter logic or public APIs.
- *Post-patch review:* Let the agent apply the patch first, then notify the developer. The patch is already in the branch; reverting requires an additional commit and creates noise in git history.

**Decision:** LangGraph's `interrupt()` primitive is called inside `human_review_node`. When reached, the graph suspends, serialises the entire `PRReviewState` to the `MemorySaver` checkpointer, and returns control to the caller. The `/webhook` endpoint returns the `thread_id` to the client. The developer inspects `final_review` and `judge_scores`, then calls `POST /approve?thread_id=...&approved=true/false`. FastAPI resumes the graph via `graph.ainvoke(Command(resume=approved), config)`. If approved, execution continues to `pr_agent_node`; if rejected, the graph routes to `END` without touching the branch.

**Consequences:** No code is written to GitHub without explicit human approval. The `thread_id` ties the webhook event to the approval, making the flow auditable. The trade-off is added infrastructure: a checkpointer must be configured, the approval endpoint must be secured, and the client must store the `thread_id` between the two HTTP calls.